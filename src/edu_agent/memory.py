"""Agent A · 长期记忆（SQLite 持久化，跨会话）。

- secs:  学生问过的教材 章/节 及次数（从每次回答的 citations 自动累积）
- kv:    自由键值笔记（如 memory_enabled 开关、"记住"类短句）
- facts: 长期事实（老师偏好/班级学情/常用教材版本…），来自「记住：xxx」或自动抽取，
         按 profile 隔离，可逐条删除 —— 对齐 DeepSeek 网页版的「记忆」：跨会话、用户可见可删
位置：data/memory.db。profile 区分不同学生/老师（UI 默认 default）。

2026-09-12 扩展（对齐 DeepSeek 记忆功能）：
  · add_fact / list_facts / delete_fact / clear_facts  —— 结构化条目，不再只能塞 kv
  · memory_enabled / set_memory_enabled                —— 总开关（关掉后不注入、不自动抽取）
  · profile_memory_prefix 现在把 facts 一并注入（原来是 secs + kv）
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "data" / "memory.db"

# 单条记忆最长字符数（防把整篇教材塞进记忆）
FACT_MAX = 200
ENABLED_KEY = "memory_enabled"

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
CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile TEXT NOT NULL, text TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'preference',
  source TEXT NOT NULL DEFAULT 'auto',
  created REAL NOT NULL, updated REAL NOT NULL,
  used INTEGER NOT NULL DEFAULT 0,        -- 被注入过几次（2026-09-19 治理用）
  last_used REAL,                         -- 上次被注入的时间
  pinned INTEGER NOT NULL DEFAULT 0,      -- 钉住：不参与衰减/裁剪（用户手动保住的）
  UNIQUE(profile, text)
);
CREATE TABLE IF NOT EXISTS conflicts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile TEXT NOT NULL,
  old_text TEXT NOT NULL,
  new_text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',  -- pending | kept_new | kept_old
  created REAL NOT NULL,
  resolved REAL
);
"""

# 老库升级：给 facts 补列（SQLite 没有 ADD COLUMN IF NOT EXISTS，重复执行报错即忽略）
_MIGRATIONS = (
    "ALTER TABLE facts ADD COLUMN used INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE facts ADD COLUMN last_used REAL",
    "ALTER TABLE facts ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0",
)


def _conn() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB))
    c.executescript(_SCHEMA)
    for sql in _MIGRATIONS:
        try:
            c.execute(sql)
        except sqlite3.OperationalError:
            pass
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


def add_fact(profile: str, text: str, kind: str = "preference",
             source: str = "auto", pinned: bool = False) -> int | None:
    """加一条长期记忆；重复/空串返回 None（去重靠 (profile,text) 唯一约束）。

    pinned=True 表示用户手动钉住：不参与衰减/裁剪（见 prune）。
    """
    t = " ".join(str(text or "").split()).strip()
    if not t:
        return None
    t = t[:FACT_MAX]
    now = time.time()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO facts(profile,text,kind,source,created,updated,pinned) "
            "VALUES(?,?,?,?,?,?,?) "
            "ON CONFLICT(profile,text) DO UPDATE SET updated=excluded.updated, "
            "kind=excluded.kind, pinned=MAX(facts.pinned, excluded.pinned)",
            (profile, t, kind or "preference", source or "auto", now, now, 1 if pinned else 0),
        )
        if cur.lastrowid:
            return int(cur.lastrowid)
        row = c.execute("SELECT id FROM facts WHERE profile=? AND text=?", (profile, t)).fetchone()
        return int(row[0]) if row else None


def list_facts(profile: str, limit: int = 100) -> list[dict]:
    """列出长期记忆（新→旧）。"""
    with _conn() as c:
        rows = c.execute(
            "SELECT id, text, kind, source, created, updated, used, last_used, pinned "
            "FROM facts WHERE profile=? ORDER BY updated DESC, id DESC LIMIT ?",
            (profile, limit),
        ).fetchall()
    return [{"id": int(r[0]), "text": r[1], "kind": r[2], "source": r[3],
             "created": r[4], "updated": r[5], "used": int(r[6] or 0),
             "last_used": r[7], "pinned": bool(r[8])} for r in rows]


def delete_fact(profile: str, fact_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM facts WHERE profile=? AND id=?", (profile, int(fact_id)))
    return cur.rowcount > 0


def clear_facts(profile: str) -> int:
    with _conn() as c:
        cur = c.execute("DELETE FROM facts WHERE profile=?", (profile,))
    return cur.rowcount


def memory_enabled(profile: str) -> bool:
    """记忆总开关（默认开）。关掉后：不注入、不自动抽取；已存条目保留。"""
    v = get_notes(profile).get(ENABLED_KEY)
    return v is None or str(v) != "0"


def set_memory_enabled(profile: str, on: bool) -> None:
    set_note(profile, ENABLED_KEY, "1" if on else "0")


def facts_prefix(profile: str, limit: int = 12) -> str:
    """把长期记忆条目拼成一句可注入的文本（无记忆返回空串）。

    顺带记一次「被用上了」（used/last_used）——治理时按这个判冷热（见 prune）。
    """
    rows = list_facts(profile, limit=limit)
    if not rows:
        return ""
    mark_used(profile, [r["id"] for r in rows])
    return "关于这位老师/学生，你已经知道：" + "；".join(r["text"] for r in rows) + "。"


def profile_memory_prefix(profile: str) -> str:
    """组装长期记忆上下文前缀（供提示词注入，无记忆返回空串）。

    关掉记忆开关 → 直接返回空串（不注入旧内容，等于"这次对话不带记忆"）。
    顺序：待确认冲突（要问用户）→ 长期事实 → 问过的章节 → 其它键值笔记。
    """
    if not memory_enabled(profile):
        return ""
    parts = []
    conf = conflicts_prefix(profile)
    if conf:
        parts.append(conf)
    facts = facts_prefix(profile)
    if facts:
        parts.append(facts)
    sec = visited_sections(profile)
    if sec:
        parts.append(sec)
    notes = {k: v for k, v in get_notes(profile).items() if k != ENABLED_KEY}
    for k, v in notes.items():
        parts.append(f"{k}: {v}")
    return "；".join(parts)


# ---------- 治理（2026-09-19）：使用计数 / 近重复合并 / 衰减裁剪 / 冲突确认 ----------

def mark_used(profile: str, ids: list[int]) -> None:
    """标记这些条目刚被注入使用（used+1、last_used=now）。"""
    if not ids:
        return
    now = time.time()
    with _conn() as c:
        c.executemany(
            "UPDATE facts SET used=used+1, last_used=? WHERE profile=? AND id=?",
            [(now, profile, int(i)) for i in ids],
        )


def set_pinned(profile: str, fact_id: int, on: bool) -> bool:
    """钉住/取消钉住（钉住的不参与裁剪与衰减）。"""
    with _conn() as c:
        cur = c.execute("UPDATE facts SET pinned=?, updated=? WHERE profile=? AND id=?",
                        (1 if on else 0, time.time(), profile, int(fact_id)))
    return cur.rowcount > 0


def _norm(text: str) -> str:
    """归一化：去空白与常见标点、全角半角无关的简化（用于近重复判断）。"""
    s = str(text or "").lower()
    return "".join(ch for ch in s if ch.strip() and ch not in "，。、；：,.;:!？?！\"'“”‘’（）()[]【】{}~-—_")


def _bigrams(s: str) -> set:
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _similar(a: str, b: str) -> float:
    """字符二元组 Jaccard 相似度（中文短句够用，不引第三方库）。"""
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ga, gb = _bigrams(na), _bigrams(nb)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / float(len(ga | gb))


def merge_duplicates(profile: str, threshold: float = 0.75) -> dict:
    """合并近重复条目（治理①）：保留「被钉住 > 用过 > 更新」的那条，删除其余。

    返回 {"removed": n, "kept": [text, ...]}，供 UI 显示"整理掉了什么"。
    """
    rows = list_facts(profile, limit=500)
    kept: list[dict] = []
    removed: list[str] = []
    for r in rows:
        dup = None
        for k in kept:
            if _similar(r["text"], k["text"]) >= threshold:
                dup = k
                break
        if dup is None:
            kept.append(r)
            continue
        # 谁是"更值得留"的：钉住 > used 多 > 更新更近
        score_r = (1 if r["pinned"] else 0, r["used"], r["updated"])
        score_k = (1 if dup["pinned"] else 0, dup["used"], dup["updated"])
        if score_r > score_k:
            kept[kept.index(dup)] = r
            loser = dup
        else:
            loser = r
        delete_fact(profile, loser["id"])
        removed.append(loser["text"])
    return {"removed": len(removed), "removed_texts": removed[:10],
            "kept": len(kept)}


def prune(profile: str, cap: int = 30, ttl_days: float = 180.0) -> dict:
    """治理②：先合并近重复，再按冷热裁剪。

    规则（钉住的永不删）：
      · 未钉住且「最后使用/更新时间」早于 ttl_days 的 → 过期删除（一直没用上的陈旧事实）
      · 未钉住且超过 cap 条的 → 按 (used, updated) 从冷到热删到 cap 条
    返回 {"merged": n, "expired": n, "trimmed": n, "facts": 剩余条数}
    """
    merged = merge_duplicates(profile)
    now = time.time()
    cutoff = now - float(ttl_days) * 86400.0
    expired = trimmed = 0
    rows = list_facts(profile, limit=500)
    pool = [r for r in rows if not r["pinned"]]
    for r in pool:
        last = max(float(r["last_used"] or 0), float(r["updated"] or 0))
        if last < cutoff:
            if delete_fact(profile, r["id"]):
                expired += 1
    pool = [r for r in list_facts(profile, limit=500) if not r["pinned"]]
    if cap > 0 and len(pool) > cap:
        cold = sorted(pool, key=lambda r: (r["used"], r["updated"]))[: len(pool) - cap]
        for r in cold:
            if delete_fact(profile, r["id"]):
                trimmed += 1
    return {"merged": merged["removed"], "expired": expired, "trimmed": trimmed,
            "facts": len(list_facts(profile, limit=500))}


# ---------- 冲突确认（2026-09-19）：新旧说法打架时，让 agent 问用户一句 ----------

def add_conflict(profile: str, old_text: str, new_text: str) -> int | None:
    """记一条待确认冲突（同一对文本只留一条 pending）。"""
    o = " ".join(str(old_text or "").split()).strip()[:FACT_MAX]
    n = " ".join(str(new_text or "").split()).strip()[:FACT_MAX]
    if not o or not n or o == n:
        return None
    with _conn() as c:
        row = c.execute(
            "SELECT id FROM conflicts WHERE profile=? AND old_text=? AND new_text=? AND status='pending'",
            (profile, o, n)).fetchone()
        if row:
            return int(row[0])
        cur = c.execute(
            "INSERT INTO conflicts(profile,old_text,new_text,status,created) VALUES(?,?,?,?,?)",
            (profile, o, n, "pending", time.time()))
        return int(cur.lastrowid) if cur.lastrowid else None


def list_conflicts(profile: str, status: str = "pending", limit: int = 20) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, old_text, new_text, status, created FROM conflicts "
            "WHERE profile=? AND status=? ORDER BY created DESC LIMIT ?",
            (profile, status, limit)).fetchall()
    return [{"id": int(r[0]), "old_text": r[1], "new_text": r[2],
             "status": r[3], "created": r[4]} for r in rows]


def resolve_conflict(profile: str, conflict_id: int, keep: str = "new") -> dict:
    """用户裁决：keep='new' 用新说法（删掉旧条），keep='old' 保留旧说（删掉新条）。"""
    keep = "old" if str(keep).lower() in ("old", "1", "旧", "keep_old") else "new"
    with _conn() as c:
        row = c.execute("SELECT old_text, new_text FROM conflicts WHERE profile=? AND id=?",
                        (profile, int(conflict_id))).fetchone()
        if not row:
            return {"ok": False, "error": "找不到该冲突"}
        old_text, new_text = row[0], row[1]
        drop = old_text if keep == "new" else new_text
        c.execute("DELETE FROM facts WHERE profile=? AND text=?", (profile, drop))
        c.execute("UPDATE conflicts SET status=?, resolved=? WHERE profile=? AND id=?",
                  ("kept_" + keep, time.time(), profile, int(conflict_id)))
    return {"ok": True, "kept": keep, "dropped": drop}


def conflicts_prefix(profile: str) -> str:
    """把待确认冲突拼成给模型的一句指令（让它先问用户，别自己猜）。"""
    rows = list_conflicts(profile)
    if not rows:
        return ""
    items = "；".join("此前记的是『%s』，这次说的是『%s』" % (r["old_text"], r["new_text"])
                     for r in rows[:3])
    return ("【需要用户确认】记忆里有两处说法冲突：" + items +
            "。请在回答的最开头用一句话问清以哪个为准，不要自行假定。")


def stats(profile: str) -> dict:
    """记忆面板用的统计（条数 / 钉住 / 用过 / 待确认冲突）。"""
    rows = list_facts(profile, limit=500)
    kinds: dict = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    return {"facts": len(rows),
            "pinned": sum(1 for r in rows if r["pinned"]),
            "used_any": sum(1 for r in rows if r["used"]),
            "conflicts_pending": len(list_conflicts(profile)),
            "kinds": kinds,
            "enabled": memory_enabled(profile)}
