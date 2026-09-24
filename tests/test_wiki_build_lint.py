# -*- coding: utf-8 -*-
"""wiki_build / wiki_lint 离线单测：**零网络、零模型调用、零 Chroma**。

覆盖三块：
  1. 抠 JSON 与"模型乱来"的形状归一化（实测踩过：返回字符串数组）
  2. 公式双通道核对、索引摘要清洗（中文 + LaTeX 的坑）
  3. 自检闸门的 6 条 ERROR 规则 + pending.md 白名单语义（"待学概念"不算断链）

临时目录一律放仓库 data/ 下（该用户禁写 C 盘），用完即删。
"""
import json
import shutil
import sys
import unittest
from pathlib import Path

# 不能靠别的测试文件先插入 src/ 才碰巧能 import（单跑本文件时必须自己挂）
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from edu_agent import wiki_build as wb      # noqa: E402
from edu_agent import wiki_lint as wl       # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def mkdir(name: str) -> Path:
    d = REPO / "data" / f"_test_wiki_{name}"
    shutil.rmtree(d, ignore_errors=True)
    (d / "concepts").mkdir(parents=True, exist_ok=True)
    return d


GOOD = """---
title: 奇函数
slug: 奇函数
created: 2026-09-22
updated: 2026-09-22
type: concept
tags: [函数, 奇偶性]
book: 必修第一册
sources: [raw/必修第一册/3.2.2.md]
pages: [89]
confidence: medium
contradictions: []
---

# 奇函数

## 定义
一般地，设函数 f(x) 的定义域为 I，若 f(-x)=-f(x)，则叫奇函数。^[p89]

## 判定/使用步骤（归纳，非原文）
1. 先看定义域是否关于原点对称。

## 关联概念
- 相关：[[偶函数]]、[[奇偶性与图象对称性]]
"""

GOOD2 = GOOD.replace("奇函数", "偶函数").replace("f(-x)=-f(x)", "f(-x)=f(x)").replace("[[偶函数]]", "[[奇函数]]")
GOOD3 = GOOD.replace("奇函数", "奇偶性与图象对称性").replace("[[奇函数]]", "[[奇函数]]")


class TestJsonAndShape(unittest.TestCase):
    """模型输出形状漂移是实测踩到的头号问题，必须有兜底。"""

    def test_parse_plain_object(self):
        self.assertEqual(wb.parse_json('{"a": 1}'), {"a": 1})

    def test_parse_with_fence_and_prose(self):
        txt = '好的，结果如下：\n```json\n{"a": [1, 2]}\n```\n以上。'
        self.assertEqual(wb.parse_json(txt), {"a": [1, 2]})

    def test_parse_nested_braces_in_string(self):
        txt = 'x {"a": "含 } 和 { 的字符串", "b": 2} y'
        self.assertEqual(wb.parse_json(txt)["b"], 2)

    def test_parse_garbage_returns_none(self):
        self.assertIsNone(wb.parse_json("完全没有 JSON"))
        self.assertIsNone(wb.parse_json(""))

    def test_norm_vision_passthrough_dict(self):
        d = wb._norm_vision({"section_no": "3.2.2", "figures": [{"num": "3.2-7"}]})
        self.assertEqual(d["section_no"], "3.2.2")
        self.assertEqual(len(d["figures"]), 1)
        self.assertIsNone(d["examples"])

    def test_norm_vision_list_of_strings_becomes_definitions(self):
        """实测第 1 页就返回了这种形状：[ "一般地，…偶函数(even function)." ]"""
        d = wb._norm_vision(["一般地，设函数 f(x)…叫做偶函数。", "另一句"])
        self.assertEqual(d["_parse"], "list-normalized")
        self.assertEqual(len(d["definitions"]), 2)
        self.assertEqual(d["formulas"], [])

    def test_norm_vision_list_of_dicts_merged(self):
        d = wb._norm_vision([{"formulas": [{"latex": "f(-x)=f(x)"}]}, {"figures": [{"num": "3.2-7"}]}])
        self.assertEqual(len(d["formulas"]), 1)
        self.assertEqual(len(d["figures"]), 1)

    def test_norm_vision_garbage(self):
        d = wb._norm_vision("这不是 JSON")
        self.assertEqual(d["_parse"], "failed")

    def test_lst_handles_none_scalar_list(self):
        self.assertEqual(wb.lst({}, "k"), [])
        self.assertEqual(wb.lst({"k": None}, "k"), [])
        self.assertEqual(wb.lst({"k": "one"}, "k"), ["one"])
        self.assertEqual(wb.lst({"k": [1, 2]}, "k"), [1, 2])


class TestFormulaCrossCheck(unittest.TestCase):
    def test_norm_math_maps_pua_and_fullwidth(self):
        self.assertEqual(wb.norm_math("犳（狓）＝狓２＋１"), "f(x)=x2+1")

    def test_conflict_when_digits_absent(self):
        # 真·冲突：公式里有个数字，文字层里**根本没出现过**（不是粘连问题）
        c = wb.cross_check([{"latex": "g(x)=x^{9}+1"}], "例如 f(x)=x2+1 都是偶函数")
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["level"], "conflict")

    def test_absent_digit_plus_present_digit_still_conflict(self):
        c = wb.cross_check([{"latex": "g(x)=\\frac{2}{x^2+7}"}], "犵（狓）＝２狓２＋１１都是偶函数")
        self.assertEqual(c[0]["level"], "conflict")

    def test_look_when_digits_present_but_not_contiguous(self):
        c = wb.cross_check([{"latex": "g(x)=\\frac{2}{x^2+1}"}], "犵（狓）＝２狓２＋１１都是偶函数")
        self.assertEqual(c[0]["level"], "look")

    def test_no_conflict_when_matching(self):
        self.assertEqual(wb.cross_check([{"latex": "f(-x)=f(x)"}], "f(-x)=f(x)"), [])

    def test_empty_inputs(self):
        self.assertEqual(wb.cross_check([], "任意文本"), [])
        self.assertEqual(wb.cross_check([{"latex": None}], "文本"), [])


class TestSummaryAndWriting(unittest.TestCase):
    def setUp(self):
        self.dir = mkdir("write")
        self._wiki, self._raw = wb.WIKI, wb.RAW
        wb.WIKI, wb.RAW = self.dir, self.dir / "raw"

    def tearDown(self):
        wb.WIKI, wb.RAW = self._wiki, self._raw
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_summary_prefers_plain_text_section(self):
        body = GOOD.split("---\n\n", 1)[1]
        s = wb._summary_of(body)
        self.assertIn("定义域", s)
        self.assertNotIn("\\", s)          # 不应残留 LaTeX 片段

    def test_write_page_writes_frontmatter_and_body(self):
        class W:
            section = "3.2.2"
        W.touched = []
        p = wb.write_page(W, {"slug": "奇函数", "title": "奇函数", "tags": ["函数", "奇偶性"],
                              "confidence": "medium", "pages": [89, 90], "body": "# 奇函数\n\n正文 ^[p89]\n"})
        txt = p.read_text(encoding="utf-8")
        self.assertTrue(txt.startswith("---\n"))
        self.assertIn("slug: 奇函数", txt)
        self.assertIn("pages: [89, 90]", txt)
        self.assertNotIn("---\n---", txt)
        self.assertEqual(W.touched[0][0], "new")

    def test_write_page_twice_marks_update(self):
        class W:
            section = "3.2.2"
        W.touched = []
        page = {"slug": "偶函数", "title": "偶函数", "tags": ["函数"], "confidence": "low",
                "pages": [88], "body": "# 偶函数\n\n^[p88]\n"}
        wb.write_page(W, page)
        wb.write_page(W, page)
        self.assertEqual([a for a, _ in W.touched], ["new", "update"])

    def test_rebuild_index_and_pending(self):
        class W:
            section = "3.2.2"
        W.touched = []
        (self.dir / "index.md").write_text(
            "# Wiki Index\n\n> 说明\n> Last updated: 2026-01-01 | Total pages: 0\n\n"
            "## 概念（Concept）\n\n（空）\n\n## 待审核（Review）\n\n> 说明\n\n（空）\n", encoding="utf-8")
        wb.write_page(W, {"slug": "奇函数", "title": "奇函数", "tags": ["函数"], "confidence": "medium",
                          "pages": [89], "body": "# 奇函数\n\n## 定义\nf(-x)=-f(x)。^[p89]\n\n- 相关：[[偶函数]]、[[还没学的概念]]\n"})
        pend = wb.update_pending()
        wb.rebuild_index(conflicts=[{"page": 88, "vision": "g(x)=2/(x^2+11)", "text": "2x2+11", "item": "举例公式"}],
                         pending=pend)
        idx = (self.dir / "index.md").read_text(encoding="utf-8")
        self.assertIn("- [[奇函数]]", idx)
        self.assertIn("Total pages: 1", idx)
        self.assertIn("公式待核（p88）", idx)
        self.assertIn("待学概念", idx)
        self.assertIn("还没学的概念", pend)


class TestLintGate(unittest.TestCase):
    """闸门必须会红——只会说"通过"的自检等于没有。"""

    def setUp(self):
        self.dir = mkdir("lint")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _write(self, name, text):
        (self.dir / "concepts" / name).write_text(text, encoding="utf-8")

    def test_clean_wiki_passes(self):
        self._write("奇函数.md", GOOD)
        self._write("偶函数.md", GOOD2)
        self._write("奇偶性与图象对称性.md", GOOD3.replace("[[偶函数]]", "[[奇函数]]"))
        r = wl.lint(self.dir)
        self.assertTrue(r["ok"], r["errors"])

    def test_missing_frontmatter_is_error(self):
        self._write("坏页.md", "# 没有 frontmatter\n")
        r = wl.lint(self.dir)
        self.assertFalse(r["ok"])
        self.assertTrue(any("缺 frontmatter" in e for e in r["errors"]))

    def test_bad_tag_short_links_and_no_provenance_are_errors(self):
        self._write("半坏.md", "---\ntitle: 半坏\nslug: 半坏\ncreated: 2026-09-22\nupdated: 2026-09-22\n"
                              "type: concept\ntags: [不存在的标签]\nbook: 必修第一册\nsources: [x]\n"
                              "pages: [1]\nconfidence: high\ncontradictions: []\n---\n\n# 半坏\n\n什么也没有。\n"
                              "\n## 判定（归纳，非原文）\n- 一条\n")
        r = wl.lint(self.dir)
        joined = " | ".join(r["errors"])
        self.assertIn("标签不在 SCHEMA 标签表内", joined)
        self.assertIn("出链只有 0 条", joined)
        self.assertIn("没有段级溯源", joined)
        self.assertIn("confidence=high 但含", joined)

    def test_pending_whitelist_turns_broken_link_into_warn(self):
        page = GOOD.replace("[[偶函数]]", "[[函数]]").replace("[[奇偶性与图象对称性]]", "[[定义域]]")
        self._write("奇函数.md", page)
        r1 = wl.lint(self.dir)
        self.assertFalse(r1["ok"], "没有 pending.md 时，引用未学概念应报 ERROR")
        (self.dir / "pending.md").write_text("# 待学\n- [[函数]]\n- [[定义域]]\n", encoding="utf-8")
        r2 = wl.lint(self.dir)
        self.assertTrue(r2["ok"], r2["errors"])
        self.assertTrue(any("待学概念" in w for w in r2["warns"]))

    def test_real_broken_link_still_error_with_pending_present(self):
        (self.dir / "pending.md").write_text("- [[函数]]\n", encoding="utf-8")
        self._write("奇函数.md", GOOD.replace("[[偶函数]]", "[[真断链]]"))
        r = wl.lint(self.dir)
        self.assertTrue(any("真断链" in e for e in r["errors"]), r["errors"])


class TestCliSafety(unittest.TestCase):
    """不需要跑模型就能验的两件事：默认路径正确、缺 key 时会明确报错而不是静默发请求。"""

    def test_default_paths_point_into_repo(self):
        self.assertTrue(str(wb.WIKI).endswith("content\\wiki") or str(wb.WIKI).endswith("content/wiki"))
        self.assertIn("wiki_raw", str(wb.RAW))
        self.assertIn("wiki", str(wl.WIKI))

    def test_chat_without_key_raises_clear_error(self):
        old = wb.API_KEY
        wb.API_KEY = ""
        try:
            with self.assertRaises(RuntimeError):
                wb.chat([{"role": "user", "content": "hi"}])
        finally:
            wb.API_KEY = old

    def test_parse_pages_range(self):
        self.assertEqual(wb.parse_pages("88-91"), [88, 89, 90, 91])
        self.assertEqual(wb.parse_pages("88,90"), [88, 90])
        self.assertEqual(wb.parse_pages("88-89,91"), [88, 89, 91])


class TestWikiInject(unittest.TestCase):
    """问答侧注入块：命中要带 [[页面名]]+页码、有长度上限、**任何异常都必须返回空串**。"""

    def setUp(self):
        from edu_agent import wiki_index as wi
        self.wi = wi
        self._search = wi.search

    def tearDown(self):
        self.wi.search = self._search

    def test_block_contains_wikilink_and_pages(self):
        self.wi.search = lambda q, k=2: [{
            "text": "奇函数 · 定义\n定义正文 f(-x)=-f(x)。",
            "meta": {"title": "奇函数", "section": "定义", "pages": "89"}, "score": 0.9}]
        blk = self.wi.prompt_block("怎么判断奇偶性", k=2)
        self.assertIn("[[奇函数]]", blk)
        self.assertIn("p89", blk)
        self.assertIn("f(-x)=-f(x)", blk)

    def test_block_empty_when_no_hits(self):
        self.wi.search = lambda q, k=2: []
        self.assertEqual(self.wi.prompt_block("随便问"), "")

    def test_block_swallows_exception(self):
        """Ollama/Chroma 挂了必须静默（主链路不能因边角能力 500）。"""

        def boom(q, k=2):
            raise RuntimeError("ollama 挂了")

        self.wi.search = boom
        self.assertEqual(self.wi.prompt_block("随便问"), "")

    def test_block_respects_max_chars(self):
        self.wi.search = lambda q, k=2: [{"text": "标题\n" + "长" * 5000,
                                          "meta": {"title": "T", "section": "S", "pages": "1"}}]
        blk = self.wi.prompt_block("x", k=1, max_chars=300)
        self.assertLessEqual(len(blk), 300 + len(self.wi.WIKI_HEADER) + 4)

    def test_chunks_of_page_splits_by_section(self):
        d = mkdir("chunks")
        try:
            p = d / "concepts" / "奇函数.md"
            p.write_text(GOOD, encoding="utf-8")
            cs = self.wi.chunks_of(p)
            self.assertGreaterEqual(len(cs), 3)
            self.assertTrue(all(c["meta"]["slug"] == "奇函数" for c in cs))
            self.assertTrue(all(c["id"].startswith("奇函数--") for c in cs))
            self.assertTrue(all(len(c["meta"]["sha1"]) == 40 for c in cs))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TestVectorSync(unittest.TestCase):
    """写页后自动同步向量库：要么同步成功，要么静默失败——**不能把落盘也带崩**。"""

    def test_sync_vectors_calls_index_sync(self):
        from edu_agent import wiki_index as wi
        old = wi.sync
        calls = []
        try:
            wi.sync = lambda quiet=False: (calls.append(quiet) or
                                           {"chunks_total": 3, "added": 1, "removed": 0, "collection_count": 3})
            r = wb.sync_vectors(verbose=False)
        finally:
            wi.sync = old
        self.assertEqual(calls, [True])                  # 内部必须 quiet=True
        self.assertEqual(r["added"], 1)

    def test_sync_vectors_swallows_exception(self):
        from edu_agent import wiki_index as wi
        old = wi.sync
        try:
            def boom(quiet=False):
                raise RuntimeError("chroma 挂了")
            wi.sync = boom
            self.assertIsNone(wb.sync_vectors(verbose=False))   # 不抛
        finally:
            wi.sync = old


if __name__ == "__main__":
    unittest.main()
