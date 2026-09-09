"""host.store.SessionStore 单元测试（纯本地 sqlite，零网络）。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from edu_agent.host.store import SessionStore


class SessionStoreTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self._tmp.name) / "sessions.db"
        self._s = None

    def tearDown(self):
        if self._s is not None:
            try:
                self._s.close()
            except Exception:
                pass
            self._s = None
        self._tmp.cleanup()

    def _open(self, migrate_legacy: Path | None = None):
        s = SessionStore(path=self.db, migrate_legacy=migrate_legacy)
        self._s = s
        return s

    def test_new_list_get_roundtrip(self):
        s = self._open()
        sid = s.new()
        self.assertEqual(s.get(sid)["title"], "新会话")
        self.assertEqual(s.get(sid)["messages"], [])
        listing = s.list_sessions()
        self.assertEqual([x["id"] for x in listing], [sid])

    def test_append_orders_and_caps_messages(self):
        s = self._open()
        sid = s.new()
        for i in range(50):
            s.append(sid, "user" if i % 2 == 0 else "assistant", f"msg{i}")
        msgs = s.get(sid)["messages"]
        # 与旧版 messages[-40:] 落盘行为对齐（保留最近 40 条）
        self.assertEqual(len(msgs), 40)
        self.assertEqual(msgs[0]["content"], "msg10")
        self.assertEqual(msgs[-1]["content"], "msg49")

    def test_persists_across_instances(self):
        s1 = self._open()
        sid = s1.new(title="持久化")
        s1.append(sid, "user", "函数的单调性怎么判断？")
        s1.set_last_html(sid, "plan.html")
        s1.close()
        self._s = None
        s2 = self._open()
        rec = s2.get(sid)
        self.assertEqual(rec["title"], "持久化")
        self.assertEqual(rec["messages"][0]["content"], "函数的单调性怎么判断？")
        self.assertEqual(rec["last_html"], "plan.html")

    def test_title_set_if_new_and_rename(self):
        s = self._open()
        sid = s.new()
        s.set_title_if_new(sid, "单调性问题")
        self.assertEqual(s.get(sid)["title"], "单调性问题")
        s.set_title_if_new(sid, "不该再改")   # 已命名不再覆盖
        self.assertEqual(s.get(sid)["title"], "单调性问题")
        s.rename(sid, "改名后")
        self.assertEqual(s.get(sid)["title"], "改名后")

    def test_delete_and_current(self):
        s = self._open()
        a = s.new()
        b = s.new()
        self.assertEqual(s.current_id(), a)   # 最旧优先（沿用旧网关语义）
        s.delete(a)
        self.assertEqual(s.current_id(), b)
        self.assertIsNone(s.get(a))

    def test_list_cap_keeps_most_recent(self):
        s = self._open()
        sids = [s.new() for _ in range(40)]
        listing = s.list_sessions()
        listed = [x["id"] for x in listing]
        # 保留最近 30 条（sids[10:]），且按 旧→新 顺序
        self.assertEqual(listed, sids[10:])

    def test_migrate_runs_at_open(self):
        """迁移在构造时执行：旧 JSON 内容进库，源文件改名留档。"""
        legacy = Path(self._tmp.name) / "web_sessions.json"
        legacy.write_text(json.dumps({
            "sid1": {"title": "老会话", "messages": [{"role": "user", "content": "旧问题"}],
                     "last_html": "old.html"},
            "broken": {"title": "坏记录", "messages": "not-a-list"},
        }, ensure_ascii=False), encoding="utf-8")
        s = self._open(migrate_legacy=legacy)
        rec = s.get("sid1")
        self.assertEqual(rec["title"], "老会话")
        self.assertEqual(rec["messages"][0]["content"], "旧问题")
        self.assertEqual(rec["last_html"], "old.html")
        self.assertIsNone(s.get("broken"))          # 坏记录跳过
        self.assertFalse(legacy.exists())           # 迁移成功则改名留档
        names = [p.name for p in Path(self._tmp.name).iterdir()
                 if p.name.startswith("web_sessions.json.migrated-")]
        self.assertEqual(len(names), 1)

    def test_unknown_session_safe(self):
        s = self._open()
        self.assertIsNone(s.get("nope"))
        s.append("nope", "user", "x")   # 不报错、不产生记录
        self.assertIsNone(s.get("nope"))


if __name__ == "__main__":
    unittest.main()
