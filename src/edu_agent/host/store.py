"""host 层 · 统一会话持久化（SQLite）。

第一阶段对照 DSH 的收口点：会话状态不再活在 web 服务进程的模块级全局
dict（web_server.SESSIONS）+ JSON 全量覆写里，而是落到 SQLite（WAL），
按 session_id 键控存取；进程重启、多线程并发都不丢数据、不互相覆盖。

数据位置：默认 data/edu_sessions.db（可用 EDU_DATA_DIR 整体迁移数据根）。
旧版 data/web_sessions.json 首次启动自动迁移（成功后原文件改名为
web_sessions.json.migrated-<时间戳>，不删除，便于回滚核对）。

对外形状与旧 JSON 完全一致：
  {id, title, messages:[{role,content}...], last_html}
所以 web 网关可以无痛切换，前端零改动。
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id        TEXT PRIMARY KEY,
  title     TEXT NOT NULL,
  messages  TEXT NOT NULL DEFAULT '[]',
  last_html TEXT NOT NULL DEFAULT '',
  created   REAL NOT NULL,
  updated   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created);
"""

_MSG_CAP = 40          # 与旧版 _save() 的 messages[-40:] 对齐
_LIST_CAP = 30         # 与旧版只保留最近 30 个会话对齐


class SessionStore:
    """线程安全的会话存取。方法签名按旧 web_server 的用法设计。"""

    def __init__(self, path: Path | None = None,
                 migrate_legacy: Path | None = None):
        self.path = Path(path) if path is not None else Path("data/edu_sessions.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        # 注意：须用 RLock——构造函数持锁期间 _migrate_legacy 还会经 _exec/_query 二次加锁
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            if migrate_legacy is not None:
                self._migrate_legacy(Path(migrate_legacy))

    # ---------- 基础 ----------

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _exec(self, sql: str, params: tuple = ()):
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def _query(self, sql: str, params: tuple = ()):
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    @staticmethod
    def _dump(msgs: list) -> str:
        # 与旧版一致：只保留最近 _MSG_CAP 条（尾部截断，不是头部）
        return json.dumps(msgs[-_MSG_CAP:], ensure_ascii=False)

    @staticmethod
    def _load(raw: str) -> list:
        try:
            msgs = json.loads(raw or "[]")
            return msgs if isinstance(msgs, list) else []
        except Exception:
            return []

    # ---------- 会话 CRUD ----------

    def new(self, title: str = "新会话") -> str:
        sid = uuid.uuid4().hex[:12]
        now = time.time()
        self._exec(
            "INSERT INTO sessions(id,title,messages,last_html,created,updated) VALUES(?,?,?,?,?,?)",
            (sid, title, "[]", "", now, now),
        )
        return sid

    def list_sessions(self) -> list[dict]:
        """最近 _LIST_CAP 条、旧→新排序（与旧 JSON 只留最近 30 个会话一致）。"""
        rows = self._query(
            "SELECT id,title FROM sessions ORDER BY created DESC, rowid DESC LIMIT ?",
            (_LIST_CAP,),
        )
        return [{"id": r["id"], "title": r["title"]} for r in reversed(rows)]

    def current_id(self) -> str | None:
        """默认选中的会话 = 保留集合里最早创建的一个（沿用旧网关语义）。"""
        listing = self.list_sessions()
        return listing[0]["id"] if listing else None

    def get(self, sid: str) -> dict | None:
        rows = self._query(
            "SELECT id,title,messages,last_html FROM sessions WHERE id=?", (sid,))
        if not rows:
            return None
        r = rows[0]
        return {"id": r["id"], "title": r["title"],
                "messages": self._load(r["messages"]), "last_html": r["last_html"]}

    def rename(self, sid: str, title: str) -> None:
        self._exec("UPDATE sessions SET title=?, updated=? WHERE id=?",
                   (title[:18], time.time(), sid))

    def delete(self, sid: str) -> None:
        self._exec("DELETE FROM sessions WHERE id=?", (sid,))

    def append(self, sid: str, role: str, content: str, meta: dict | None = None) -> None:
        """追加一条消息（超长截断到 _MSG_CAP 条，与旧版落盘行为一致）。

        meta（可选，2026-09-10 新增）：随消息一起持久化的附加信息，目前用于**引用 citations**
        ——此前只存正文，刷新/重开会话后正文里的引用 pill 就消失了（George 2026-09-10 报的 bug）。
        形状：{"mode": "A|S|B", "citations": [...], "pages": [...]}
        老消息没有 meta 键，前端按「无引用」处理，向后兼容。
        """
        sess = self.get(sid)
        if sess is None:
            return
        msg: dict = {"role": role, "content": content}
        if meta:
            msg["meta"] = meta
        msgs = sess["messages"] + [msg]
        self._exec(
            "UPDATE sessions SET messages=?, updated=? WHERE id=?",
            (self._dump(msgs), time.time(), sid),
        )

    def set_title_if_new(self, sid: str, title: str) -> None:
        """会话仍是默认标题时用首条消息改题（旧 web_server 逻辑）。"""
        rows = self._query("SELECT title FROM sessions WHERE id=?", (sid,))
        if rows and rows[0]["title"] == "新会话":
            self.rename(sid, title)

    def set_last_html(self, sid: str, name: str) -> None:
        self._exec("UPDATE sessions SET last_html=?, updated=? WHERE id=?",
                   (name, time.time(), sid))

    # ---------- 旧 JSON 迁移 ----------

    def _migrate_legacy(self, legacy: Path) -> None:
        """web_sessions.json → SQLite；迁移成功把旧文件改名留档。"""
        if not legacy.exists():
            return
        rows = self._query("SELECT COUNT(*) AS n FROM sessions")
        if rows[0]["n"] > 0:
            return
        try:
            raw = json.loads(legacy.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(raw, dict):
            return
        now = time.time()
        n = 0
        for sid, v in list(raw.items())[-_LIST_CAP:]:
            if not isinstance(v, dict) or not isinstance(v.get("messages"), list):
                continue
            msgs = [m for m in v["messages"]
                    if isinstance(m, dict) and "role" in m and "content" in m]
            self._exec(
                "INSERT OR REPLACE INTO sessions(id,title,messages,last_html,created,updated)"
                " VALUES(?,?,?,?,?,?)",
                (str(sid), str(v.get("title") or "新会话")[:18], self._dump(msgs),
                 str(v.get("last_html") or ""), now, now),
            )
            n += 1
        if n:
            try:
                legacy.rename(legacy.with_name(legacy.name + ".migrated-" + uuid.uuid4().hex[:8]))
            except OSError:
                pass
