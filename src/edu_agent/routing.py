"""routing.py —— 意图路由的单一事实来源（第一阶段收口）。

背景（收口前的问题）：supervisor.py、graph.py、web_server.py / api.py 各自维护
一份"教案类/答疑类"关键词表，已出现互相漂移（如 supervisor 独有的"上课/导学"、
graph 独有的"课件/教案模板"）。同一个句子在 S 路径和 auto 路径可能路由到不同 Agent。

收口后：只在本文件维护一份 PLAN_HINTS / QA_HINTS 与 decide()，所有消费方
（supervisor 派单、web 网关 auto、graph Router）一律调用本文件，不再自带词表。
行为约定（与旧规则一致）：
  - 显式 mode 优先（"A"/"B" 或 "coach"/"plan"）；
  - 无显式 mode 时：命中任一教案类词 → B（教案 Agent）；否则 → A（课本教练）。
"""
from __future__ import annotations

# 教案意图词（命中任一即 B）。刻意小而准；可在此集中增删。
PLAN_HINTS = (
    "教案", "备课", "教学设计", "怎么讲", "怎么教", "如何教", "如何讲",
    "教学目标", "板书设计", "教学环节", "课件", "课堂设计", "教案模板",
    "上课", "导学",
    # 2026-09-12 补：PPT/演示类说法此前不在词表里，"要课件" 能命中 B、"要 ppt" 却不能
    "ppt", "幻灯片", "演示文稿", "slides", "课件制作", "说课",
    # 2026-09-12 补：口语说法（"帮我备一节 3.3 幂函数的课"）此前漏判为 A
    "备一节", "备一课", "备这节课",
)

# 「教案 / PPT 主题」判定词（比 PLAN_HINTS 更宽，用于决定是否给用户两个选项）
TOPIC_HINTS = (
    "教案", "备课", "教学设计", "课堂设计", "课件", "ppt", "幻灯片",
    "演示文稿", "slides", "说课", "讲稿", "导学案", "教案模板",
)

# 答疑意图词（A 侧信号；decide 默认即 A，此表供分类/统计与未来策略使用）
QA_HINTS = (
    "是什么", "为什么", "怎么解", "怎么判断", "区别", "证明",
    "求", "等于", "练习", "题", "帮我算", "讲解",
)

# 规范化代号：任意形态 → "A" | "B"
_CODE_MAP = {
    "A": "A", "coach": "A", "答疑": "A",
    "B": "B", "plan": "B", "教案": "B",
}


def want_plan(text: str) -> bool:
    """文本是否含教案类意图词。"""
    t = text or ""
    return any(h in t for h in PLAN_HINTS)


def involves_plan_topic(text: str, hits=None) -> tuple[bool, str]:
    """本次是否「涉及教案/PPT」——决定要不要给用户那两个选项。

    两类信号（任一命中即可，对应计划书 §4.2）：
      intent    —— 问题/指令里出现 教案|备课|课件|ppt|幻灯片|演示文稿… ；
      retrieval —— 检索命中的片段（来源名/标题/正文开头）里出现这些词，
                   典型场景：老师上传过教案/课件 PDF 后按 `corpus=pdf:` 检索。

    返回 (是否涉及, 命中原因)。
    """
    t = (text or "").lower()
    for h in TOPIC_HINTS:
        if h in t:
            return True, "intent"
    for h in (hits or []):
        try:
            md = getattr(h, "metadata", None) or {}
            blob = " ".join(str(x) for x in (
                md.get("source", ""), md.get("heading", ""), md.get("book", ""),
                md.get("section", ""), getattr(h, "text", "")[:120],
            )).lower()
        except Exception:
            continue
        if any(k in blob for k in TOPIC_HINTS):
            return True, "retrieval"
    return False, ""


def decide(text: str, mode: str | None = None) -> str:
    """统一派单决策：返回 "A"（课本教练）或 "B"（教案 Agent）。

    mode 接受 A/B、coach/plan、auto/空（=None）。显式 A/B 优先于关键词。
    """
    m = _CODE_MAP.get((mode or "").strip())
    if m:
        return m
    return "B" if want_plan(text) else "A"


def label(mode: str) -> str:
    """把内部代号转成对外标签（旧 web 文案兼容）。"""
    return "coach" if decide("", mode=mode) == "A" else "plan"
