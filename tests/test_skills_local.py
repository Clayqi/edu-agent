# -*- coding: utf-8 -*-
"""经验→技能（自写 SKILL.md）单元测试。用 EDU_SKILLS_DIR 指到临时目录，不碰真实 data/skills。"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class SkillCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="skilltest-")
        self._old = os.environ.get("EDU_SKILLS_DIR")
        os.environ["EDU_SKILLS_DIR"] = self.dir
        import importlib

        from edu_agent import skills_local
        importlib.reload(skills_local)          # 重新读 env
        self.sk = skills_local

    def tearDown(self):
        if self._old is None:
            os.environ.pop("EDU_SKILLS_DIR", None)
        else:
            os.environ["EDU_SKILLS_DIR"] = self._old
        shutil.rmtree(self.dir, ignore_errors=True)


class TestSaveListRead(SkillCase):
    def test_save_and_list(self):
        r = self.sk.save_skill("mono-steps", "单调性三步法", "判断单调性的固定流程", "1. 取 x1<x2\n2. 作差\n3. 判号")
        self.assertTrue(r["ok"])
        self.assertTrue(Path(r["path"]).exists())
        rows = self.sk.list_skills()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "单调性三步法")
        self.assertGreater(rows[0]["body_chars"], 5)

    def test_read_back_keeps_body(self):
        self.sk.save_skill("s1", "技能一", "描述一", "正文内容在这里")
        self.assertIn("正文内容在这里", self.sk.read_skill("s1"))

    def test_overwrite_backs_up_old(self):
        self.sk.save_skill("s1", "技能一", "描述一", "第一版")
        r = self.sk.save_skill("s1", "技能一", "描述一", "第二版")
        self.assertIn("backup", r)
        self.assertTrue(Path(r["backup"]).exists())
        self.assertIn("第二版", self.sk.read_skill("s1"))
        self.assertIn("第一版", Path(r["backup"]).read_text(encoding="utf-8"))
        self.assertEqual(len(self.sk.list_skills()), 1)     # 不是两条

    def test_empty_body_rejected(self):
        self.assertFalse(self.sk.save_skill("s2", "空技能", "描述", "   ")["ok"])

    def test_chinese_name_gets_fallback_id(self):
        r = self.sk.save_skill("单调性三步法", "单调性三步法", "描述", "正文")
        self.assertTrue(r["ok"])
        self.assertTrue(r["id"].startswith("skill-"))       # 合法 id（哈希兜底）

    def test_chinese_name_id_is_stable(self):
        """同名同 id：再存一次是更新 + 留旧版备份，不会堆出重复技能。"""
        r1 = self.sk.save_skill("单调性三步法", "单调性三步法", "描述", "第一版")
        r2 = self.sk.save_skill("单调性三步法", "单调性三步法", "描述", "第二版")
        self.assertEqual(r1["id"], r2["id"])
        self.assertEqual(len(self.sk.list_skills()), 1)
        self.assertIn("backup", r2)
        self.assertIn("第二版", self.sk.read_skill(r1["id"]))

    def test_mixed_ascii_chinese_names_do_not_collide(self):
        """含中文的名字不能只截 ASCII 片段（否则两个不同技能会撞同一个 id）。"""
        a = self.sk.save_skill("ad-hoc-中文技能名A", "ad-hoc-中文技能名A", "d", "正文A")
        b = self.sk.save_skill("ad-hoc-中文技能名B", "ad-hoc-中文技能名B", "d", "正文B")
        self.assertNotEqual(a["id"], b["id"])
        self.assertEqual(len(self.sk.list_skills()), 2)

    def test_pure_ascii_name_stays_readable(self):
        r = self.sk.save_skill("mono-steps", "单调性三步法", "d", "正文")
        self.assertEqual(r["id"], "mono-steps")          # 纯 ASCII 仍给可读 id

    def test_caps_enforced(self):
        r = self.sk.save_skill("big", "x" * 200, "y" * 900, "z" * 40000)
        self.assertTrue(r["ok"])
        row = self.sk.list_skills()[0]
        self.assertLessEqual(len(row["name"]), self.sk.NAME_MAX)


class TestDeleteAndIntents(SkillCase):
    def test_delete_archives(self):
        self.sk.save_skill("s3", "技能三", "描述", "正文")
        r = self.sk.delete_skill("s3")
        self.assertTrue(r["ok"])
        self.assertEqual(len(self.sk.list_skills()), 0)
        self.assertTrue(Path(r["archived_to"]).exists())     # 归档而非物理删

    def test_delete_missing(self):
        self.assertFalse(self.sk.delete_skill("nope")["ok"])

    def test_skill_intent(self):
        self.assertEqual(self.sk.skill_intent("把这套做法存成技能：单调性三步法"), "单调性三步法")
        self.assertEqual(self.sk.skill_intent("存成技能："), "")
        self.assertIsNone(self.sk.skill_intent("函数的单调性怎么判断？"))

    def test_delete_intent(self):
        self.assertEqual(self.sk.delete_intent("删掉技能 mono-steps"), "mono-steps")
        self.assertIsNone(self.sk.delete_intent("删除这条记忆"))

    def test_save_from_answer(self):
        r = self.sk.save_from_answer("这道题怎么讲更好？存成技能：例题讲法", "先给情境再给定义", "例题讲法")
        self.assertTrue(r["ok"])
        txt = self.sk.read_skill(r["id"])
        self.assertIn("先给情境再给定义", txt)
        self.assertIn("经验→技能回路", txt)

    def test_prompt_block_empty_when_none(self):
        self.assertEqual(self.sk.prompt_block(), "")

    def test_prompt_block_lists_skills(self):
        self.sk.save_skill("s4", "技能四", "一句话描述", "正文")
        blk = self.sk.prompt_block()
        self.assertIn("我自己积累的技能", blk)
        self.assertIn("s4", blk)


if __name__ == "__main__":
    unittest.main()
