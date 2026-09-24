# -*- coding: utf-8 -*-
"""长期记忆治理（2026-09-19）：去重合并 / 使用计数 / 衰减裁剪 / 冲突确认。

纯 SQLite，不碰网络；用临时库，绝不写真实 data/memory.db。
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from edu_agent import memory

P = "t"


class MemoryCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="memtest-")
        self._old = memory.DB
        memory.DB = Path(self.dir) / "memory.db"

    def tearDown(self):
        memory.DB = self._old
        shutil.rmtree(self.dir, ignore_errors=True)


class TestSchemaAndFacts(MemoryCase):
    def test_add_and_exact_dedupe(self):
        a = memory.add_fact(P, "我用的是人教A版必修一")
        b = memory.add_fact(P, "我用的是人教A版必修一")
        self.assertEqual(a, b)                      # 精确重复 → 同一条
        self.assertEqual(len(memory.list_facts(P)), 1)

    def test_new_columns_present(self):
        memory.add_fact(P, "喜欢用表格讲例题")
        f = memory.list_facts(P)[0]
        for k in ("used", "last_used", "pinned"):
            self.assertIn(k, f)
        self.assertEqual(f["used"], 0)
        self.assertFalse(f["pinned"])

    def test_mark_used_counts(self):
        fid = memory.add_fact(P, "喜欢用表格讲例题")
        memory.mark_used(P, [fid])
        memory.mark_used(P, [fid])
        self.assertEqual(memory.list_facts(P)[0]["used"], 2)

    def test_empty_is_rejected(self):
        self.assertIsNone(memory.add_fact(P, "   "))


class TestMergeDuplicates(MemoryCase):
    def test_near_dup_merged(self):
        memory.add_fact(P, "我用人教A版必修一，班级是重点班")
        memory.add_fact(P, "我用的是人教A版必修一，班级是重点班！")   # 只差标点/空格
        r = memory.merge_duplicates(P)
        self.assertEqual(r["removed"], 1)
        self.assertEqual(len(memory.list_facts(P)), 1)

    def test_pinned_survives_merge(self):
        keep = memory.add_fact(P, "我带的是高二(3)班", pinned=True)
        memory.add_fact(P, "我带的是高二3班")
        memory.merge_duplicates(P)
        rows = memory.list_facts(P)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], keep)
        self.assertTrue(rows[0]["pinned"])

    def test_unrelated_not_merged(self):
        memory.add_fact(P, "我用的是人教A版必修一")
        memory.add_fact(P, "喜欢用表格讲例题")
        self.assertEqual(memory.merge_duplicates(P)["removed"], 0)


class TestPrune(MemoryCase):
    def test_expire_old_unused(self):
        memory.add_fact(P, "陈旧偏好：喜欢用红笔批改")
        r = memory.prune(P, cap=30, ttl_days=0)      # ttl=0 → 全部算过期
        self.assertEqual(r["expired"], 1)
        self.assertEqual(memory.stats(P)["facts"], 0)

    def test_cap_keeps_used_one(self):
        hot = memory.add_fact(P, "热的一条")
        memory.mark_used(P, [hot])
        for i in range(4):
            memory.add_fact(P, "冷的一条 %d" % i)
        r = memory.prune(P, cap=2, ttl_days=3650)
        self.assertGreaterEqual(r["trimmed"], 1)
        self.assertLessEqual(memory.stats(P)["facts"], 2)
        self.assertIn(hot, [f["id"] for f in memory.list_facts(P)])

    def test_pinned_never_expires(self):
        memory.add_fact(P, "钉住的", pinned=True)
        memory.prune(P, cap=1, ttl_days=0)
        self.assertEqual(len(memory.list_facts(P)), 1)


class TestConflicts(MemoryCase):
    def test_add_and_list(self):
        cid = memory.add_conflict(P, "带的是重点班", "带的是普通班")
        self.assertIsNotNone(cid)
        self.assertEqual(memory.add_conflict(P, "带的是重点班", "带的是普通班"), cid)  # 不重复登记
        self.assertEqual(len(memory.list_conflicts(P)), 1)
        self.assertEqual(memory.stats(P)["conflicts_pending"], 1)

    def test_same_text_ignored(self):
        self.assertIsNone(memory.add_conflict(P, "一样的话", "一样的话"))

    def test_resolve_keep_new_drops_old(self):
        memory.add_fact(P, "带的是重点班")
        memory.add_fact(P, "带的是普通班")
        cid = memory.add_conflict(P, "带的是重点班", "带的是普通班")
        r = memory.resolve_conflict(P, cid, "new")
        self.assertTrue(r["ok"])
        texts = [f["text"] for f in memory.list_facts(P)]
        self.assertIn("带的是普通班", texts)
        self.assertNotIn("带的是重点班", texts)
        self.assertEqual(len(memory.list_conflicts(P)), 0)

    def test_resolve_keep_old_drops_new(self):
        memory.add_fact(P, "带的是重点班")
        memory.add_fact(P, "带的是普通班")
        cid = memory.add_conflict(P, "带的是重点班", "带的是普通班")
        memory.resolve_conflict(P, cid, "old")
        texts = [f["text"] for f in memory.list_facts(P)]
        self.assertIn("带的是重点班", texts)
        self.assertNotIn("带的是普通班", texts)

    def test_prefix_asks_user(self):
        memory.add_conflict(P, "带的是重点班", "带的是普通班")
        self.assertIn("需要用户确认", memory.profile_memory_prefix(P))

    def test_resolve_unknown_id(self):
        self.assertFalse(memory.resolve_conflict(P, 9999, "new")["ok"])


class TestSwitchAndPin(MemoryCase):
    def test_disabled_means_no_prefix(self):
        memory.add_fact(P, "一条事实")
        self.assertTrue(memory.profile_memory_prefix(P))
        memory.set_memory_enabled(P, False)
        self.assertEqual(memory.profile_memory_prefix(P), "")
        memory.set_memory_enabled(P, True)
        self.assertTrue(memory.profile_memory_prefix(P))

    def test_prefix_marks_used(self):
        memory.add_fact(P, "一条事实")
        memory.profile_memory_prefix(P)
        self.assertEqual(memory.list_facts(P)[0]["used"], 1)

    def test_pin_toggle(self):
        fid = memory.add_fact(P, "一条事实")
        self.assertTrue(memory.set_pinned(P, fid, True))
        self.assertTrue(memory.list_facts(P)[0]["pinned"])
        memory.set_pinned(P, fid, False)
        self.assertFalse(memory.list_facts(P)[0]["pinned"])


if __name__ == "__main__":
    unittest.main()
