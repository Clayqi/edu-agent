# -*- coding: utf-8 -*-
"""跨会话检索（FTS5+trigram）单元测试。用 EDU_SESSIONS_DB 指到临时库，不碰真实会话库。"""
import importlib
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class SearchCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="searchtest-")
        self.db = str(Path(self.dir) / "sessions.db")
        self._old = os.environ.get("EDU_SESSIONS_DB")
        os.environ["EDU_SESSIONS_DB"] = self.db

        from edu_agent import session_search
        from edu_agent.host.store import SessionStore

        importlib.reload(session_search)
        self.ss = session_search
        self.store = SessionStore(path=Path(self.db))
        # 两个会话：一个讲单调性，一个讲集合
        self.a = self.store.new("什么是增函数？")
        self.store.append(self.a, "user", "什么是增函数？")
        self.store.append(self.a, "assistant", "在区间上自变量增大函数值也增大，就是增函数，判定要看单调性定义。")
        self.b = self.store.new("集合怎么表示")
        self.store.append(self.b, "user", "集合怎么表示？")
        self.store.append(self.b, "assistant", "列举法和描述法都可以表示集合。")
        self.store.close()

    def tearDown(self):
        try:
            self.store.close()
        except Exception:
            pass
        if self._old is None:
            os.environ.pop("EDU_SESSIONS_DB", None)
        else:
            os.environ["EDU_SESSIONS_DB"] = self._old
        shutil.rmtree(self.dir, ignore_errors=True)


class TestSearch(SearchCase):
    def test_refresh_then_incremental(self):
        r1 = self.ss.refresh()
        self.assertEqual(r1["indexed"], 2)
        r2 = self.ss.refresh()                     # 没变化 → 全部跳过
        self.assertEqual(r2["indexed"], 0)
        self.assertEqual(r2["skipped"], 2)

    def test_chinese_search_hits(self):
        self.ss.refresh()
        hits = self.ss.search("单调性", limit=5)
        self.assertTrue(hits)
        self.assertIn("单调性", " ".join(h["snippet"] for h in hits))

    def test_short_query_fallback(self):
        self.ss.refresh()
        hits = self.ss.search("集合", limit=5)     # 2 字：trigram 命不中，走子串扫描
        self.assertTrue(hits)
        self.assertTrue(all("集合" in h["snippet"] or "集合" in h["text"] for h in hits))

    def test_exclude_sid(self):
        self.ss.refresh()
        hits = self.ss.search("集合", limit=5, exclude_sid=self.b)
        self.assertTrue(all(h["sid"] != self.b for h in hits))

    def test_no_hit(self):
        self.ss.refresh()
        self.assertEqual(self.ss.search("量子纠缠与火箭推力", limit=3), [])

    def test_too_short_query_ignored(self):
        self.assertEqual(self.ss.search("一", limit=3), [])

    def test_past_prefix_wording(self):
        self.ss.refresh()
        p = self.ss.past_prefix("增函数怎么判断？")
        self.assertIn("过去的对话里提到过", p)
        self.assertIn("什么是增函数？", p)          # 带上会话标题，便于溯源

    def test_past_prefix_empty_when_no_hit(self):
        self.ss.refresh()
        self.assertEqual(self.ss.past_prefix("量子纠缠与火箭推力"), "")

    def test_force_reindex(self):
        self.ss.refresh()
        self.assertEqual(self.ss.refresh(force=True)["indexed"], 2)

    def test_natural_language_query_hits(self):
        """整句中文提问（无空格、非子串）也要能命中 —— 靠 3-gram OR + 打分。"""
        self.ss.refresh()
        hits = self.ss.search("增函数怎么判断？", limit=3)
        self.assertTrue(hits)
        self.assertTrue(any("增函数" in h["snippet"] for h in hits))

    def test_ngrams_and_candidates(self):
        self.assertGreaterEqual(len(self.ss._ngrams("增函数怎么判断")), 4)
        self.assertEqual(self.ss._ngrams("增", n=3), ["增"])
        self.assertIn("增函数", self.ss._candidates("增函数"))

    def test_english_query_also_works(self):
        self.ss.refresh()
        self.assertEqual(self.ss.search("zzz-not-exist", limit=3), [])


if __name__ == "__main__":
    unittest.main()
