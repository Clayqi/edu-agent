# -*- coding: utf-8 -*-
"""查询预处理（编号/术语/结构问法）单元测试。纯规则，无 IO。"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from edu_agent.preprocess import (  # noqa: E402
    classify_question,
    cn_to_int,
    int_to_cn_chapter,
    kind_filter_for,
    normalize_terms,
    parse_refs,
    preprocess,
)


class TestCnToInt(unittest.TestCase):
    def test_single(self):
        self.assertEqual(cn_to_int("五"), 5)
        self.assertEqual(cn_to_int("一"), 1)

    def test_ten_and_teens(self):
        self.assertEqual(cn_to_int("十"), 10)
        self.assertEqual(cn_to_int("十三"), 13)

    def test_twenties(self):
        self.assertEqual(cn_to_int("二十"), 20)
        self.assertEqual(cn_to_int("二十五"), 25)

    def test_invalid(self):
        self.assertIsNone(cn_to_int("ABC"))
        self.assertIsNone(cn_to_int(""))


class TestChapter(unittest.TestCase):
    def test_int_to_cn(self):
        self.assertEqual(int_to_cn_chapter(3), "第三章")
        self.assertEqual(int_to_cn_chapter(11), "第十一章")

    def test_parse_arabic_chapter(self):
        ref = parse_refs("第四章 指数函数和对数函数的关系")
        self.assertEqual(ref.chapter, "第四章")

    def test_parse_chinese_chapter(self):
        ref = parse_refs("第三章函数的概念怎么理解")
        self.assertEqual(ref.chapter, "第三章")

    def test_no_chapter(self):
        ref = parse_refs("什么是函数的单调性？")
        self.assertIsNone(ref.chapter)


class TestSectionAndPage(unittest.TestCase):
    def test_section_2part(self):
        ref = parse_refs("3.2 函数的单调性怎么判断")
        self.assertEqual(ref.section, "3.2")

    def test_section_3part(self):
        ref = parse_refs("课本 3.2.1 节例题怎么做")
        self.assertEqual(ref.section, "3.2.1")

    def test_page_en(self):
        ref = parse_refs("p45 的练习怎么做")
        self.assertEqual(ref.page, 45)

    def test_page_cn(self):
        ref = parse_refs("第 102 页的例 3")
        self.assertEqual(ref.page, 102)

    def test_item_li(self):
        ref = parse_refs("4.2 例 2 怎么做")
        self.assertEqual(ref.item, "例 2")

    def test_item_diN_ti(self):
        ref = parse_refs("第三章 第 5 题怎么做")
        self.assertEqual(ref.item, "第 5 题")


class TestNormalizeTerms(unittest.TestCase):
    def test_dandiao(self):
        out = normalize_terms("函数单调怎么判断")
        self.assertIn("单调性", out)

    def test_aliases(self):
        out = normalize_terms("均值不等式是什么")
        self.assertIn("基本不等式", out)

    def test_no_change_when_plain(self):
        out = normalize_terms("集合的交集怎么算")
        self.assertEqual(out, "集合的交集怎么算")


class TestClassify(unittest.TestCase):
    def test_problem(self):
        self.assertEqual(classify_question("3.2 例 2 怎么做"), "problem")
        self.assertEqual(classify_question("已知 f(x)=x^2 求 f(1)"), "problem")

    def test_concept(self):
        self.assertEqual(classify_question("什么是奇函数？"), "concept")
        self.assertEqual(classify_question("函数的单调性怎么判断"), "concept")

    def test_general(self):
        self.assertEqual(classify_question("课本里讲了什么"), "general")

    def test_kind_filter(self):
        self.assertIn("section", kind_filter_for("problem"))
        self.assertIn("section", kind_filter_for("concept"))
        self.assertIsNone(kind_filter_for("general"))


class TestPreprocess(unittest.TestCase):
    def test_structural_question_kept(self):
        p = preprocess("3.2 例 2 怎么做？")
        self.assertEqual(p.ref.section, "3.2")
        self.assertEqual(p.ref.item, "例 2")
        self.assertEqual(p.qtype, "problem")
        self.assertTrue(p.hints, "应生成坐标提示")

    def test_plain_question_query_kept(self):
        p = preprocess("函数的单调性怎么判断？")
        self.assertEqual(p.query, "函数的单调性怎么判断？")

    def test_hint_content(self):
        p = preprocess("第三章 第 5 题")
        joined = " ".join(p.hints)
        self.assertIn("第三章", joined)
        self.assertIn("第 5 题", joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
