# -*- coding: utf-8 -*-
"""跨会话检索（2026-09-19）：让"旧对话"能回流到新对话里。

在此之前，这个 agent 跨会话只记得两类东西：关于用户的事实（memory.facts）和
"问过哪些章节"的次数（memory.secs）——**具体聊过什么不会回流**。本模块把会话库
（host.store 的 sessions.messages）用 SQLite **FTS5 + trigram 分词**索引起来，
回答前按当前问题检索几条最相关的历史片段注入提示词。

为什么必须 trigram：FTS5 默认 unicode61 会把整串中文当成一个 token，搜「单调性」命中不了
「函数的单调性判定」（实测 t3 返回 0 条）；trigram（三字符滑窗）能正确命中，实测可用。
查询短于 3 个字符时 trigram 无法命中（这是 FTS5 trigram 的硬性要求），此时退回
Python 子串扫描（会话量上限 30 个，全扫也就千把条消息，够快）。

索引与同步：FTS 表建在**同一个会话库**里（msg_fts / msg_fts_sync），
refresh() 只重建"自上次同步后有更新"的会话；任何异常都静默（检索失败绝不影响回答）。
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path

from edu_agent.config import load_settings

_SNIPPET_PAD = 40          # 片段左右各留多少字符
_PREFIX_MAX = 600          # 注入提示词的总长度上限
_FTS_MIN = 3               # trigram 能命中的最短查询长度

_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS msg_fts USING fts5(
  sid UNINDEXED, role UNINDEXED, text, tokenize='trigram'
);
CREATE TABLE IF NOT EXISTS msg_fts_sync (sid TEXT PRIMARY KEY, updated REAL NOT NULL);
"""

_fts_ok: bool | None = None


def _db_path() -> Path:
    return Path(load_settings().sessions_db)


def _conn() -> sqlite3.Connection:
    p = _db_path()
    c = sqlite3.connect(str(p), timeout=10)
    c.execute("PRAGMA busy_timeout=5000")
    c.executescript(_SCHEMA)
    return c


def fts_available() -> bool:
    """探测本机 SQLite 是否支持 FTS5+trigram（不支持就全程走子串扫描）。"""
    global _fts_ok
    if _fts_ok is None:
        c = None
        try:
            c = _conn()
            c.execute("INSERT INTO msg_fts(sid, role, text) VALUES('__probe__','user','探测trigram分词')")
            c.execute("DELETE FROM msg_fts WHERE sid='__probe__'")
            c.commit()
            _fts_ok = True
        except Exception:
            _fts_ok = False
        finally:
            if c is not None:
                try:
                    c.close()      # 探测完立刻关连接：不关会一直握住 db 句柄（Windows 上删文件/迁移会失败）
                except Exception:
                    pass
    return bool(_fts_ok)


def _load_messages(raw: str) -> list:
    try:
        msgs = json.loads(raw or "[]")
        return msgs if isinstance(msgs, list) else []
    except Exception:
        return []


def refresh(force: bool = False, max_sessions: int = 30) -> dict:
    """把（有更新的）会话重建进 FTS 索引。返回 {"indexed": n, "skipped": n, "fts": bool}。"""
    indexed = skipped = 0
    try:
        c = _conn()
        rows = c.execute("SELECT id, messages, updated FROM sessions "
                         "ORDER BY created DESC, rowid DESC LIMIT ?", (max_sessions,)).fetchall()
        synced = dict(c.execute("SELECT sid, updated FROM msg_fts_sync").fetchall())
        use_fts = fts_available()
        for sid, raw, updated in rows:
            if not force and abs(float(synced.get(sid, -1)) - float(updated or 0)) < 1e-9:
                skipped += 1
                continue
            msgs = _load_messages(raw)
            if use_fts:
                c.execute("DELETE FROM msg_fts WHERE sid=?", (sid,))
                for m in msgs:
                    if not isinstance(m, dict):
                        continue
                    txt = str(m.get("content") or "").strip()
                    if txt:
                        c.execute("INSERT INTO msg_fts(sid, role, text) VALUES(?,?,?)",
                                  (str(sid), str(m.get("role") or ""), txt))
            c.execute("INSERT INTO msg_fts_sync(sid, updated) VALUES(?,?) "
                      "ON CONFLICT(sid) DO UPDATE SET updated=excluded.updated",
                      (str(sid), float(updated or 0)))
            indexed += 1
        c.commit()
        c.close()
    except Exception:
        return {"indexed": indexed, "skipped": skipped, "fts": bool(_fts_ok)}
    return {"indexed": indexed, "skipped": skipped, "fts": bool(_fts_ok)}


def _snippet(text: str, q: str) -> str:
    """取匹配点附近的片段（找不到就取开头）。"""
    t = re.sub(r"\s+", " ", str(text or ""))
    i = t.find(q)
    if i < 0:
        return t[:_SNIPPET_PAD * 2]
    a = max(0, i - _SNIPPET_PAD)
    b = min(len(t), i + len(q) + _SNIPPET_PAD)
    return ("…" if a else "") + t[a:b] + ("…" if b < len(t) else "")


def _norm_query(text: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", " ", str(text or "")).strip()


def _candidates(text: str, max_len: int = 12, cap: int = 4) -> list[str]:
    """短句/带空格子句 → 可直接检索的候选词。"""
    s = _norm_query(text)
    cands: list[str] = []
    if s and len(s) <= max_len:
        cands.append(s)
    for p in s.split():
        if len(p) >= 2:
            cands.append(p if len(p) <= max_len else p[:6])
    out: list[str] = []
    for c in cands:
        if c and c not in out:
            out.append(c)
    return out[:cap]


def _ngrams(text: str, n: int = 3, cap: int = 24) -> list[str]:
    """中文没有词边界：整句「增函数怎么判断」在 trigram 里不是子串，必须切成 n-gram 去 OR 检索。"""
    s = _norm_query(text).replace(" ", "")
    if len(s) < n:
        return [s] if s else []
    grams: list[str] = []
    for i in range(len(s) - n + 1):
        g = s[i:i + n]
        if g not in grams:
            grams.append(g)
    return grams[:cap]


def _like_scan(c: sqlite3.Connection, needles: list[str], limit_rows: int = 60) -> list[tuple[str, str, str]]:
    """子串扫描兜底（短词或 FTS 不可用时）。"""
    hits: list[tuple[str, str, str]] = []
    for sid, raw in c.execute("SELECT id, messages FROM sessions "
                              "ORDER BY created DESC, rowid DESC LIMIT 30"):
        for m in _load_messages(raw):
            txt = str(m.get("content") or "")
            if any(n in txt for n in needles):
                hits.append((sid, str(m.get("role") or ""), txt))
                break
        if len(hits) >= limit_rows:
            break
    return hits


def search(q: str, limit: int = 3, exclude_sid: str | None = None) -> list[dict]:
    """检索历史对话片段 → [{sid, role, snippet}]。

    流程：① 整句短（≤4 字）→ 直接子串/FTS；② 长句 → 切 3-gram，用 "OR" 拼成一次 FTS 查询，
    再按「命中的 gram 数」排序取前 limit 条（中文提问通常只有几个词能对上，靠这个打分）。
    """
    q = " ".join(str(q or "").split())
    if len(q) < 2:
        return []
    grams = _ngrams(q)
    cands = _candidates(q) or [q]
    rows: list[tuple[str, str, str]] = []
    try:
        c = _conn()
        if fts_available() and len(grams) >= 1:
            expr = " OR ".join('"' + g.replace('"', '""') + '"' for g in (grams or cands))
            try:
                rows = [(sid, role, text) for sid, role, text in c.execute(
                    "SELECT sid, role, text FROM msg_fts WHERE msg_fts MATCH ? LIMIT 60", (expr,))]
            except sqlite3.OperationalError:
                rows = []
        if not rows:
            rows = _like_scan(c, grams if len(grams) >= 1 and len(q) >= 3 else cands)
        c.close()
    except Exception:
        return []
    ranked: list[tuple[int, str, str, str]] = []
    for sid, role, text in rows:
        if exclude_sid and sid == exclude_sid:
            continue
        score = sum(1 for g in (grams or cands) if g in text)
        if score <= 0:
            continue
        ranked.append((score, sid, role, text))
    ranked.sort(key=lambda r: -r[0])
    out: list[dict] = []
    used: set = set()
    for score, sid, role, text in ranked:
        key = (sid, role, text[:60])
        if key in used:
            continue
        used.add(key)
        hit_gram = next((g for g in (grams or cands) if g in text), cands[0])
        out.append({"sid": sid, "role": role, "snippet": _snippet(text, hit_gram),
                    "text": text[:_PREFIX_MAX], "score": score})
        if len(out) >= limit:
            break
    return out


def _titles() -> dict:
    try:
        c = _conn()
        d = {r[0]: r[1] for r in c.execute("SELECT id, title FROM sessions")}
        c.close()
        return d
    except Exception:
        return {}


def past_prefix(user_text: str, exclude_sid: str | None = None, limit: int = 2) -> str:
    """把最相关的历史对话片段拼成可注入文本（无命中返回空串）。"""
    rows = search(user_text, limit=limit, exclude_sid=exclude_sid)
    if not rows:
        return ""
    titles = _titles()
    items = []
    for r in rows:
        who = "我问过" if r["role"] == "user" else "我之前答过"
        ttl = titles.get(r["sid"], "")
        items.append("在《%s》里%s：%s" % (ttl, who, r["snippet"]))
    s = "【过去的对话里提到过】" + "；".join(items) + "。（可作参考；与教材原文冲突时以教材为准）"
    return s[:_PREFIX_MAX]
