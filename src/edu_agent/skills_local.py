# -*- coding: utf-8 -*-
"""经验→技能（2026-09-19）：让 agent 能把"跑通的做法/踩过的坑"写成自己的 SKILL.md。

为什么要这个：在此之前 agent 的"学习"只能表现为记忆里多一条**关于用户的事实**，
它不会积累**关于自己该怎么干活的程序性知识**（Hermes 那种"技能"）。本模块补上这条回路：

  写入：① 用户明说「存成技能：xxx」→ 把这一轮的回答存成技能
        ② 提供 /api/skill/save 接口（前端"存为技能"按钮）
  读回：每次回答前把技能清单（id + 一句话描述）注入提示词 → 下一次回答真的按技能走

存储：<data_dir>/skills/<id>/SKILL.md（UTF-8，带 YAML front-matter），
      data/ 不入库（与 memory.db / 会话库一致）；EDU_SKILLS_DIR 可整体迁移。
      旧版本不覆盖丢失：改写时先备份到同目录 SKILL.md.bak-<时间戳>；
      删除时整目录移到 skills/_archive/<id>-<时间戳>/（不物理删，便于找回）。
"""
from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

from edu_agent.config import load_settings

# 单技能限制（防止把整篇教材塞进技能）
NAME_MAX = 60
DESC_MAX = 300
BODY_MAX = 20000
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,47}$")

# 显式指令：「存成技能：xxx」/「把这个存成技能 xxx」/「记成技能：xxx」/「存为技能：xxx」
_SAVE_RE = re.compile(
    r"(?:存成|存为|记成|保存成|做成)\s*技能\s*[:：]?\s*(.{0,60})", re.S)
# 删除指令：「删掉技能 xxx」
_DEL_RE = re.compile(r"(?:删掉|删除|去掉)\s*技能\s*[:：]?\s*([a-z0-9][a-z0-9_-]{1,47})", re.I)


def skills_dir() -> Path:
    """技能根目录（优先 EDU_SKILLS_DIR，其次 <data_dir>/skills）。"""
    import os

    env = (os.getenv("EDU_SKILLS_DIR") or "").strip()
    if env:
        return Path(env)
    return Path(load_settings().data_dir) / "skills"


def _slug(text: str, fallback: str = "") -> str:
    """把任意名字变成合法 id（保 ASCII）。

    · 纯 ASCII 名字 → 用可读的 slug（mono-steps 这种）
    · **含中文等非 ASCII 的名字 → 一律走哈希**（不能只取 ASCII 片段：`ad-hoc-中文技能名A` 与
      `...B` 会被截成同一个 `ad-hoc` → 两个不同技能撞 id）；同一名字永远同一个 id，
      所以再存一次是"更新 + 留旧版备份"，不会堆重复。
    """
    raw = " ".join(str(text or "").split())
    if raw and re.fullmatch(r"[A-Za-z0-9 _.-]+", raw):
        s = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()[:48]
        if ID_RE.match(s):
            return s
    seed = raw or " ".join(str(fallback or "").split()) or "skill"
    return "skill-" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]


def _front_matter(name: str, description: str, tags: list[str] | None = None,
                  source: str = "self") -> str:
    tags = tags or []
    now = time.strftime("%Y-%m-%d %H:%M")
    lines = [f"name: {name}", f"description: {description}"]
    if tags:
        lines.append("tags: " + ", ".join(tags))
    lines += [f"source: {source}", f"updated: {now}"]
    return "---\n" + "\n".join(lines) + "\n---\n\n"


def save_skill(skill_id: str, name: str, description: str, body: str,
               tags: list[str] | None = None) -> dict:
    """写入/更新一个技能。返回 {"ok", "id", "path", "backup"?}。"""
    sid = _slug(skill_id, fallback=_slug(name))
    nm = " ".join(str(name or "").split())[:NAME_MAX] or sid
    desc = " ".join(str(description or "").split())[:DESC_MAX] or (nm + "（无描述）")
    txt = str(body or "").strip()
    if not txt:
        return {"ok": False, "error": "技能正文为空"}
    txt = txt[:BODY_MAX]

    d = skills_dir() / sid
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    backup = None
    if p.exists():                      # 改写前留旧版，别覆盖丢内容
        backup = d / ("SKILL.md.bak-" + time.strftime("%Y%m%d-%H%M%S"))
        try:
            p.replace(backup)
        except OSError:
            backup = None
    p.write_text(_front_matter(nm, desc, tags) + txt + ("\n" if not txt.endswith("\n") else ""),
                 encoding="utf-8")
    out = {"ok": True, "id": sid, "name": nm, "path": str(p),
           "bytes": p.stat().st_size}
    if backup:
        out["backup"] = str(backup)
    return out


def _parse(txt: str) -> dict:
    """读 front-matter（name/description/tags/source）。"""
    info: dict = {}
    if not txt.startswith("---"):
        return info
    end = txt.find("\n---", 3)
    if end < 0:
        return info
    for line in txt[3:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    return info


def list_skills() -> list[dict]:
    """列出全部自建技能（新→旧）。"""
    root = skills_dir()
    if not root.exists():
        return []
    out = []
    for d in sorted(root.iterdir()):
        p = d / "SKILL.md"
        if not d.is_dir() or not p.exists():
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = _parse(txt)
        body = txt.split("\n---", 1)[-1].strip()
        out.append({"id": d.name, "name": fm.get("name") or d.name,
                    "description": fm.get("description") or "",
                    "tags": [t.strip() for t in (fm.get("tags") or "").split(",") if t.strip()],
                    "source": fm.get("source") or "self",
                    "path": str(p), "bytes": len(txt.encode("utf-8")),
                    "body_chars": len(body),
                    "updated": p.stat().st_mtime})
    return sorted(out, key=lambda x: x["updated"], reverse=True)


def read_skill(skill_id: str) -> str:
    p = skills_dir() / _slug(skill_id) / "SKILL.md"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def delete_skill(skill_id: str) -> dict:
    """归档删除（移到 _archive/，不物理删）。"""
    d = skills_dir() / _slug(skill_id)
    if not d.exists():
        return {"ok": False, "error": "技能不存在"}
    arch = skills_dir() / "_archive"
    arch.mkdir(parents=True, exist_ok=True)
    dest = arch / (d.name + "-" + time.strftime("%Y%m%d-%H%M%S"))
    try:
        d.replace(dest)
    except OSError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "archived_to": str(dest)}


def skill_intent(text: str) -> str | None:
    """识别「存成技能：xxx」的意图，返回用户给的名字（可能为空串）。"""
    m = _SAVE_RE.search(str(text or ""))
    return (m.group(1) or "").strip() if m else None


def delete_intent(text: str) -> str | None:
    m = _DEL_RE.search(str(text or ""))
    return m.group(1) if m else None


def save_from_answer(user_text: str, answer: str, name_hint: str = "") -> dict | None:
    """把这一轮回答存成技能（用户说了「存成技能」时调用）。

    技能名优先用用户给的名字，其次用问题的前 24 字；正文 = 这一轮的回答原文。
    """
    hint = " ".join(str(name_hint or "").split())
    q = " ".join(str(user_text or "").split())
    if not hint:
        hint = q[:24]
    if not hint:
        return None
    desc = (q[:DESC_MAX] if q else hint)
    body = ("# " + hint + "\n\n"
            "> 来源：由用户在对话中要求保存（2026-09-19 经验→技能回路）。\n"
            "> 触发场景：" + (q[:120] if q else "（未记录）") + "\n\n"
            + str(answer or "").strip())
    return save_skill(_slug(hint, fallback=_slug(q)), hint, desc, body)


def prompt_block(limit: int = 8) -> str:
    """注入提示词的技能清单（只给 id + 描述，正文按需读，避免撑爆上下文）。"""
    rows = list_skills()[:limit]
    if not rows:
        return ""
    items = "；".join(f"{r['id']}（{r['description'][:60]}）" for r in rows)
    return ("【我自己积累的技能】" + items +
            "。若当前问题和某个技能相关，就按该技能的做法执行；"
            "用户说「存成技能：名字」时，把这一轮的有效做法整理成可复用步骤写进技能。")
