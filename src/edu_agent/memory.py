"""Agent A · 长期记忆（SQLite 持久化，跨会话）。

- secs: 学生问过的教材 章/节 及次数（从每次回答的 citations 自动累积）
- kv:   自由键值笔记（后续可接"知识点掌握度/偏好"等）
位置：data/memory.db。profile 区分不同学生（UI 默认 default）。
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "data" / "memory.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS secs (
  profile TEXT NOT NULL, chapter TEXT NOT NULL, section TEXT NOT NULL,
  hits INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL,
  PRIMARY KEY (profile, chapter, section)
);
CREATE TABLE IF NOT EXISTS kv (
  profile TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
  updated REAL NOT NULL, PRIMARY KEY (profile, key)
);
"""


def _conn() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB))
    c.executescript(_SCHEMA)
    return c


def record_sections(profile: str, citations: list) -> None:
    """记录一次回答涉及的 章/节（防跨章引用也计入）。"""
    if not citations:
        return
    seen = set()
    with _conn() as c:
        for cit in citations:
            ch = (cit.get("chapter") or "").strip()
            sec = (cit.get("section") or "").strip()
            if not ch:
                continue
            key = (ch, sec if sec else cit.get("heading") or "整节")
            if key in seen:
                continue
            seen.add(key)
            now = time.time()
            c.execute(
                "INSERT INTO secs(profile,chapter,section,hits,updated) VALUES(?,?,?,1,?) "
                "ON CONFLICT(profile,chapter,section) DO UPDATE SET hits=hits+1, updated=excluded.updated",
                (profile, key[0], key[1], now),
            )


def visited_sections(profile: str, limit: int = 8) -> str:
    """最近/最常问的节 -> 一段可注入前情的文本（无记录返回空）。"""
    with _conn() as c:
        rows = c.execute(
            "SELECT chapter, section, hits FROM secs WHERE profile=? ORDER BY updated DESC, hits DESC LIMIT ?",
            (profile, limit),
        ).fetchall()
    if not rows:
        return ""
    parts = [f"{ch} {sec}(问过{hits}次)" for ch, sec, hits in rows]
    return "该学生此前问过：" + "、".join(parts) + "。"


def set_note(profile: str, key: str, value: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO kv(profile,key,value,updated) VALUES(?,?,?,?) "
            "ON CONFLICT(profile,key) DO UPDATE SET value=excluded.value, updated=excluded.updated",
            (profile, key, value, time.time()),
        )


def get_notes(profile: str) -> dict:
    with _conn() as c:
        rows = c.execute("SELECT key, value FROM kv WHERE profile=?", (profile,)).fetchall()
    return dict(rows)


def profile_memory_prefix(profile: str) -> str:
    """组装长期记忆上下文前缀（供提示词注入，无记忆返回空串）。"""
    sec = visited_sections(profile)
    notes = get_notes(profile)
    out = []
    if sec:
        out.append(sec)
    for k, v in notes.items():
        out.append(f"{k}: {v}")
    return "；".join(out)
