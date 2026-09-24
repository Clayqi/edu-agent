# -*- coding: utf-8 -*-
"""记忆自动抽取（对齐 DeepSeek 网页版的「记忆」）—— 2026-09-12。

两条来源：
1. **显式**：用户说「记住：xxx」/「记一下 xxx」→ 直接落库，不花模型调用（快、准、可预期）
2. **自动**：一轮问答结束后，用一次低温小调用判断「这轮里有没有值得跨会话记住的事实」

克制原则（重要，别把记忆用成流水账）：
- 只记**跨会话仍然成立、且下次能改变行为**的事实：教材版本、班级学情、课时安排、惯用模板、
  称呼与称谓、明确说出的偏好/禁忌；「这道题怎么做」这类一次性问题一律不记。
- 每轮最多 max_new 条、单条 ≤ memory.FACT_MAX 字；任何失败都静默（记忆绝不拖垮/拖慢主流程）。
- 记忆总开关关掉时：不抽取、不注入（见 memory.memory_enabled）。

调用方：web_server 的 Agent A 流式回答结束后（后台线程，不阻塞回答）。
"""
from __future__ import annotations

import json
import re
import threading

from edu_agent import memory

_LOG = None
_EXTRACT_SYSTEM = (
    "你负责维护用户的长期记忆（像 DeepSeek 网页版的记忆功能）。"
    "只抽取**跨会话仍然成立、且下次能改变你行为**的事实，例如：教材版本/出版社、班级与学情、"
    "课时长度、惯用教案模板、称呼、明确的偏好或禁忌。"
    "不要记：一次性提问内容、题目解法、泛泛的寒暄、你自己说过的话。"
    "最多 {max_new} 条，每条不超过 {max_len} 个字。\n"
    "同时检查「用户这轮说的」与「已记住的」是否**互相矛盾**（同一件事两种说法，"
    "如班级/学段/教材版本/称呼变了）——矛盾的放进 conflicts，不要放进 add。\n"
    "只输出一个 JSON 对象，不要解释、不要代码块标记："
    '{{"add": ["用的是人教版必修一"], "conflicts": [{{"old": "带的是重点班", "new": "带的是普通班"}}]}}'
)

# 显式指令：记住：xxx / 记一下：xxx / 记下来 xxx / 帮我记住 xxx
_EXPLICIT = re.compile(
    r"(?:^|[，。;；\s])(?:请|帮我|麻烦)?(?:记住|记一下|记下来|记录一下|记下)\s*[:：]?\s*(.{2,200})",
    re.S,
)


def explicit_fact(text: str) -> str | None:
    """从用户这句话里取出「记住：xxx」的内容（没有则 None）。"""
    m = _EXPLICIT.search(str(text or ""))
    if not m:
        return None
    fact = " ".join(m.group(1).split()).strip(" 　.。;；,，")
    return fact[: memory.FACT_MAX] or None


def _parse_json_list(raw: str) -> list[str]:
    """从模型输出里抠出 JSON 数组（容忍代码块/前后废话）。"""
    s = str(raw or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    m = re.search(r"\[.*\]", s, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out = []
    for it in data:
        if isinstance(it, str) and it.strip():
            out.append(" ".join(it.split())[: memory.FACT_MAX])
    return out


def _clean(s: str) -> str:
    return " ".join(str(s or "").split()).strip()[: memory.FACT_MAX]


def _parse_extract(raw: str) -> tuple[list[str], list[dict]]:
    """解析抽取结果 → (新增事实, 冲突对)。

    新格式：{"add": [...], "conflicts": [{"old": "...", "new": "..."}]}
    兼容老格式：模型只给了一个 JSON 数组（当作 add，无冲突）。
    """
    s = str(raw or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    m = re.search(r"\{.*\}", s, re.S)
    if m:
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            adds = [_clean(x) for x in (data.get("add") or []) if isinstance(x, str)]
            confs = []
            for c in (data.get("conflicts") or []):
                if isinstance(c, dict) and c.get("old") and c.get("new"):
                    confs.append({"old": _clean(c["old"]), "new": _clean(c["new"])})
            return [a for a in adds if a], [c for c in confs if c["old"] and c["new"]]
    return _parse_json_list(s), []


def extract_and_store(user_text: str, answer_text: str = "", profile: str = "default",
                      max_new: int = 4) -> list[str]:
    """跑一次抽取并落库，返回本次新增/更新的条目。任何异常都静默返回 []。"""
    if not memory.memory_enabled(profile):
        return []
    user_text = str(user_text or "").strip()
    if len(user_text) < 6:                       # 太短的话没什么可记
        return []

    # ① 显式指令优先（不花模型）
    stored: list[str] = []
    fact = explicit_fact(user_text)
    if fact:
        if memory.add_fact(profile, fact, kind="preference", source="user"):
            stored.append(fact)

    # ② 自动抽取（有模型 key 时才做）
    try:
        from edu_agent.config import get_chat_llm, load_settings

        if not load_settings().key_ready:
            return stored
        llm = get_chat_llm(temperature=0.0, timeout=40)
        msg = [
            {"role": "system",
             "content": _EXTRACT_SYSTEM.format(max_new=max_new, max_len=memory.FACT_MAX)},
            {"role": "user",
             "content": ("【用户这轮说的】\n" + user_text[:800]
                         + "\n\n【助手回答（节选）】\n" + str(answer_text or "")[:600]
                         + "\n\n已记住的（别重复）：" + "；".join(
                             f["text"] for f in memory.list_facts(profile, limit=20))[:400])},
        ]
        raw = llm.invoke(msg).content or ""
        adds, confs = _parse_extract(raw)
        for f in adds[:max_new]:
            if f not in stored and memory.add_fact(profile, f, kind="preference", source="auto"):
                stored.append(f)
        # 矛盾的说法不进 add，登记成待确认冲突（下次回答开头 agent 会问用户一句）
        for c in confs[:max_new]:
            memory.add_conflict(profile, c["old"], c["new"])
    except Exception:  # noqa: BLE001  记忆抽取失败绝不影响主流程
        pass
    return stored


def extract_async(user_text: str, answer_text: str = "", profile: str = "default") -> None:
    """后台线程抽取（web_server 回答结束后调用，不阻塞用户）。"""
    threading.Thread(target=extract_and_store, args=(user_text, answer_text, profile),
                     name="edu-memory-extract", daemon=True).start()
