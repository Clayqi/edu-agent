# -*- coding: utf-8 -*-
"""会话教案 -> 教案中心模板：解析 / 匹配 / 填充 的离线测试。

（与「升级模板不得删原件」的回归用例分开：那条在 tests/test_template_rich.py，
属于接口层修复，和本模块的解析/匹配/填充逻辑无关。）
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_PROJ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJ / "src"))

# web_server 在 import 时会建 SessionStore，先把数据根指到临时目录，避免污染本机
os.environ.setdefault("EDU_DATA_DIR", tempfile.mkdtemp(prefix="edu_test_data_"))

from edu_agent import plan_sync as ps       # noqa: E402
from edu_agent import template_rich as tr   # noqa: E402
from edu_agent import template_spec as ts   # noqa: E402
from edu_agent import web_server as ws      # noqa: E402
SAMPLE_MD = """**【Agent B · 教案 Agent】**# 函数的单调性（新授课）

**教学目标**
- 理解函数单调性的定义，能判断区间上的增减性。[1]
- 会用定义证明简单函数的单调性。[2]

**教学重难点**
- 重点：单调性的定义与判定。
- 难点：作差法比较 f(x1) 与 f(x2)。

**教学过程**
### 情境导入（约 5 分钟）
用气温曲线图引入"随自变量增大函数值如何变化"。
### 概念建构（约 15 分钟）
给出定义：区间上取 x1<x2，比较 f(x1)-f(x2) 与 0。
### 例题精讲（约 15 分钟）
例1 f(x)=kx+b 的单调性；例2 用定义证明 f(x)=x^2 在 [0,+∞) 递增。
### 课堂小结（约 5 分钟）
总结判定步骤：取值 -> 作差 -> 变形 -> 定号 -> 结论。

**板书设计**
左侧定义，右侧例题。

**作业布置**
- 课本 P79 练习 1、2。
"""


def _template() -> dict:
    """一份带表格板块的富模板（模拟老师自带的模板）。"""
    return tr.normalize({
        "template_id": "tpl", "name": "我的教案模板",
        "blocks": [
            {"title": "一、教学目标", "elements": [
                {"type": "para", "text": "（在此填写目标）",
                 "runs": [{"text": "（在此填写目标）", "font": "宋体", "size": 12}]}]},
            {"title": "二、教学重点与难点", "elements": [{"type": "para", "text": "（待填）"}]},
            {"title": "三、教学过程", "elements": [
                {"type": "table", "header": True, "cells": [
                    [{"text": "教学环节"}, {"text": "教师活动"}, {"text": "学生活动"}, {"text": "时间"}],
                    [{"text": "（示例行）"}, {"text": ""}, {"text": ""}, {"text": ""}]]}]},
            {"title": "四、板书设计", "elements": [{"type": "para", "text": "（待填）"}]},
            {"title": "五、作业布置", "elements": [{"type": "para", "text": "（待填）"}]},
            {"title": "六、教学反思", "elements": [{"type": "para", "text": "（课后补）"}]},
        ]})


class TestParse(unittest.TestCase):
    def test_title_and_tag_stripped(self):
        p = ps.parse_plan_markdown(SAMPLE_MD)
        self.assertEqual(p["title"], "函数的单调性（新授课）")
        self.assertNotIn("Agent B", p["title"])

    def test_bold_lines_become_sections(self):
        p = ps.parse_plan_markdown(SAMPLE_MD)
        titles = [s.title for s in p["sections"]]
        for t in ("教学目标", "教学重难点", "教学过程", "板书设计", "作业布置"):
            self.assertIn(t, titles)

    def test_bullets_and_subs(self):
        p = ps.parse_plan_markdown(SAMPLE_MD)
        sec = {s.title: s for s in p["sections"]}
        self.assertEqual(len([i for i in sec["教学目标"].items if i.kind == "bullet"]), 2)
        subs = [i for i in sec["教学过程"].items if i.kind == "sub"]
        self.assertEqual(len(subs), 4)
        self.assertEqual(subs[0].title, "情境导入（约 5 分钟）")
        self.assertIn("气温曲线", subs[0].text)

    def test_markdown_table(self):
        md = "# 课题\n\n**教学目标**\n\n| 素养 | 描述 |\n| --- | --- |\n| 数学抽象 | 抽象出概念 |\n"
        p = ps.parse_plan_markdown(md)
        tbl = [i for i in p["sections"][0].items if i.kind == "table"][0]
        self.assertEqual(len(tbl.rows), 2)          # 分隔行被剔除
        self.assertEqual(tbl.rows[0], ["素养", "描述"])


class TestMatch(unittest.TestCase):
    def test_norm_and_score(self):
        self.assertEqual(ps.norm_title("四、教学目标（对标核心素养）"), "教学目标")
        self.assertEqual(ps.title_score("四、教学目标（对标核心素养）", "教学目标"), 1.0)
        self.assertGreaterEqual(ps.title_score("二、课标依据与教材分析", "教材依据"), 0.4)
        self.assertGreaterEqual(ps.title_score("九、作业设计（分层设计）", "作业布置"), 0.8)
        self.assertLess(ps.title_score("板书设计", "教学反思"), 0.34)

    def test_greedy_one_to_one(self):
        blocks = [{"title": "教学目标"}, {"title": "教学过程"}]
        secs = [ps.Section(title="教学过程"), ps.Section(title="教学目标")]
        pairs, miss_b, miss_s = ps.match_sections(blocks, secs)
        self.assertEqual([(b, s) for b, s, _ in pairs], [(0, 1), (1, 0)])
        self.assertEqual(miss_b, [])
        self.assertEqual(miss_s, [])


class TestFill(unittest.TestCase):
    def setUp(self):
        self.tpl = _template()

    def test_blocks_keep_title_and_order(self):
        res = ps.sync(SAMPLE_MD, self.tpl)
        self.assertTrue(res["ok"], res.get("error"))
        t = res["template"]
        self.assertEqual([b["title"] for b in t["blocks"]][:6], [b["title"] for b in self.tpl["blocks"]][:6],
                         "模板板块标题与顺序必须原样保留")

    def test_table_block_filled_row_per_sub(self):
        res = ps.sync(SAMPLE_MD, self.tpl)
        blk = [b for b in res["template"]["blocks"] if b["title"] == "三、教学过程"][0]
        cells = blk["elements"][0]["cells"]
        head = [c["text"] for c in cells[0][:4]]
        self.assertEqual(head, ["教学环节", "教师活动", "学生活动", "时间"], "真表头应保留")
        self.assertEqual(len(cells), 1 + 4, "表头 + 4 个环节行；模板示例行应被替换")
        self.assertTrue(cells[1][0]["text"].startswith("情境导入"), cells[1][0]["text"])
        self.assertIn("气温曲线", cells[1][1]["text"])

    def test_paragraph_block_filled(self):
        res = ps.sync(SAMPLE_MD, self.tpl)
        blk = [b for b in res["template"]["blocks"] if b["title"] == "一、教学目标"][0]
        texts = [e["text"] for e in blk["elements"] if e["type"] == "para"]
        self.assertEqual(len(texts), 2)
        self.assertIn("单调性", texts[0])
        self.assertTrue(texts[0].startswith("·"), "要点应带 · 前缀")
        # 套用模板段落格式
        self.assertEqual(blk["elements"][0]["runs"][0]["font"], "宋体")
        self.assertEqual(blk["elements"][0]["runs"][0]["size"], 12)

    def test_unmatched_sections_appended(self):
        md = SAMPLE_MD + "\n**易错点辨析**\n- 定义域漏限制。\n"
        res = ps.sync(md, self.tpl)
        titles = [b["title"] for b in res["template"]["blocks"]]
        self.assertIn("易错点辨析", titles)
        self.assertIn("易错点辨析", res["report"]["appended"])

    def test_unmatched_blocks_untouched(self):
        res = ps.sync(SAMPLE_MD, self.tpl)
        blk = [b for b in res["template"]["blocks"] if b["title"] == "六、教学反思"][0]
        self.assertEqual(blk["elements"][0]["text"], "（课后补）")
        self.assertIn("六、教学反思", res["report"]["unmatched_blocks"])

    def test_no_plan_content(self):
        self.assertFalse(ps.sync("这里没有板块结构", self.tpl)["ok"])

    def test_plan_title_recorded(self):
        res = ps.sync(SAMPLE_MD, self.tpl)
        self.assertEqual(res["template"]["plan_title"], "函数的单调性（新授课）")


def _gen_template() -> dict:
    """模拟 ①「生成教案模板」的产物：板块 + （填写提示） + 只有表头的空表格。"""
    return tr.normalize({
        "template_id": "gen", "name": "AI 生成模板",
        "blocks": [
            {"title": "教学目标", "elements": [{"type": "para", "text": "（填写提示）写可检测的目标"}]},
            {"title": "教学过程", "elements": [
                {"type": "table", "header": True, "cells": [
                    [{"text": "环节"}, {"text": "教师活动"}],
                    [{"text": ""}, {"text": ""}]]}]},
        ]})


class TestBlankBlocks(unittest.TestCase):
    """教案中心黄条提示：哪些板块还空着。"""

    def test_generated_template_all_blank(self):
        self.assertEqual(ps.blank_blocks(_gen_template()), ["教学目标", "教学过程"])

    def test_filled_block_is_not_blank(self):
        res = ps.sync(SAMPLE_MD, _gen_template())
        blank = ps.blank_blocks(res["template"])
        self.assertNotIn("教学目标", blank, "已填入目标的板块不该算空")
        self.assertNotIn("教学过程", blank, "表格填了环节行就不算空")

    def test_table_header_alone_is_blank(self):
        t = tr.normalize({"template_id": "x", "name": "x", "blocks": [
            {"title": "板书设计", "elements": [
                {"type": "table", "header": True, "cells": [[{"text": "左"}, {"text": "右"}]]}]}]})
        self.assertEqual(ps.blank_blocks(t), ["板书设计"], "只有表头不算有内容")

    def test_empty_section_is_blank(self):
        t = tr.normalize({"template_id": "x", "name": "x",
                          "blocks": [{"title": "教学反思", "elements": []}]})
        self.assertEqual(ps.blank_blocks(t), ["教学反思"])


class TestFromTemplateEndpoint(unittest.TestCase):
    """选项③：把已有教案正文按板块填进模板（不再花模型调用）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._old = (tr.TEMPLATES_DIR, tr.ORIG_DIR, ts.TEMPLATES_DIR)
        tr.TEMPLATES_DIR = ts.TEMPLATES_DIR = Path(self._tmp.name)
        tr.ORIG_DIR = Path(self._tmp.name) / "orig"
        tr.save_rich(_template())

    def tearDown(self):
        tr.TEMPLATES_DIR, tr.ORIG_DIR, ts.TEMPLATES_DIR = self._old

    def test_fill_by_markdown(self):
        res = ws.api_plan_from_template(
            ws.PlanFromTemplateReq(markdown=SAMPLE_MD, template_id="tpl"))
        self.assertTrue(res["ok"], res.get("error"))
        self.assertEqual(res["template_id"], "tpl")
        matched = [m["block"] for m in res["report"]["matched"]]
        self.assertIn("一、教学目标", matched)
        self.assertIn("三、教学过程", matched)
        self.assertIn("blank_blocks", res)
        self.assertNotIn("一、教学目标", res["blank_blocks"], "填过的板块不该报空")

    def test_missing_content_is_reported(self):
        with mock.patch.object(ws, "_last_plan_markdown", return_value=""):
            with mock.patch.object(ws._store, "current_id", return_value=""):
                with mock.patch.object(ws._store, "list_sessions", return_value=[]):
                    res = ws.api_plan_from_template(
                        ws.PlanFromTemplateReq(markdown="  ", template_id="tpl"))
        self.assertFalse(res["ok"])
        self.assertIn("教案内容", res["error"])

    def test_unknown_template_is_reported(self):
        res = ws.api_plan_from_template(
            ws.PlanFromTemplateReq(markdown=SAMPLE_MD, template_id="不存在的模板"))
        self.assertFalse(res["ok"])
        self.assertIn("没有模板", res["error"])

    def test_skeleton_template_can_be_filled(self):
        """内置 default 这种「只有板块名、没有原件」的骨架模板也要能填（原先直接报错）。"""
        res = ws.api_plan_from_template(
            ws.PlanFromTemplateReq(markdown=SAMPLE_MD, template_id="default"))
        self.assertTrue(res["ok"], res.get("error"))
        self.assertEqual(res["template_source"], "skeleton")
        self.assertEqual(res["stats"]["blocks"], 7, "内置 default 的 7 个板块应都在")
        matched = [m["block"] for m in res["report"]["matched"]]
        self.assertIn("教学目标", matched)
        self.assertIn("作业布置", matched)

    def test_save_flag_writes_template(self):
        res = ws.api_plan_from_template(
            ws.PlanFromTemplateReq(markdown=SAMPLE_MD, template_id="tpl", save=True))
        self.assertTrue(res["ok"], res.get("error"))
        saved = tr.load_rich("tpl")
        self.assertEqual(saved["plan_title"], "函数的单调性（新授课）")


class TestRichFromSkeleton(unittest.TestCase):
    """骨架模板（v1）-> 可填充的富模板。"""

    def test_builtin_default(self):
        spec = ts.default_template()
        rich = ps.rich_from_skeleton(spec)
        titles = [b["title"] for b in rich["blocks"]]
        self.assertEqual(titles, ["教材与学情分析", "教学目标", "教学重难点",
                                  "教学过程", "板书设计", "作业布置", "教学反思"])
        self.assertEqual(ps.blank_blocks(rich), titles, "刚搭出来时全都空着")
        self.assertEqual(tr.normalize(rich)["blocks"][0]["kind"], "section")

    def test_table_header_restored_from_note(self):
        from edu_agent.template_spec import Block, TemplateSpec

        spec = TemplateSpec(template_id="sk", name="骨架", blocks=[
            Block(order=1, type="heading", title="教学目标"),
            Block(order=2, type="table", title="表格(4列)",
                  note="表头: 教学环节 / 教师活动 / 学生活动 / 设计意图; 6 行内容"),
        ])
        rich = ps.rich_from_skeleton(spec)
        tbl = rich["blocks"][1]["elements"][0]
        self.assertEqual(tbl["type"], "table")
        self.assertTrue(tbl["header"])
        self.assertEqual([c["text"] for c in tbl["cells"][0]],
                         ["教学环节", "教师活动", "学生活动", "设计意图"])

    def test_preamble_skipped(self):
        from edu_agent.template_spec import Block, TemplateSpec

        spec = TemplateSpec(template_id="sk", name="骨架", blocks=[
            Block(order=1, type="preamble", title="（模板开头）", note="随便写点"),
            Block(order=2, type="heading", title="教学目标"),
        ])
        self.assertEqual([b["title"] for b in ps.rich_from_skeleton(spec)["blocks"]], ["教学目标"])


if __name__ == "__main__":
    unittest.main()
