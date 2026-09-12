# -*- coding: utf-8 -*-
"""教案/PPT 联动（一期）：意图判定 / 选项事件 / 模板生成结果转换。

全离线：LLM 与检索都不调用，只测纯逻辑与结构化转换。
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_PROJ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJ / "src"))
os.environ.setdefault("EDU_DATA_DIR", tempfile.mkdtemp(prefix="edu_test_data_"))

from edu_agent import planner, prompts, routing   # noqa: E402
from edu_agent import template_rich as tr         # noqa: E402
from edu_agent import web_server as ws            # noqa: E402


class _Hit:
    """假检索命中（retrieve 的返回元素只需要 metadata / text）。"""

    def __init__(self, text="", **md):
        self.text = text
        self.metadata = md


class TestIntent(unittest.TestCase):
    def test_plan_words_route_to_b(self):
        for q in ("帮我备一节 3.3 幂函数的课", "我要做 ppt", "生成幻灯片", "写个演示文稿", "要做课件"):
            self.assertEqual(routing.decide(q), "B", q)

    def test_plain_question_stays_a(self):
        for q in ("什么是函数的单调性", "求 f(x)=x^2 的导数", "这道题怎么解"):
            self.assertEqual(routing.decide(q), "A", q)

    def test_involves_by_intent(self):
        ok, why = routing.involves_plan_topic("帮我写个教案")
        self.assertTrue(ok)
        self.assertEqual(why, "intent")
        for q in ("要 ppt", "做个幻灯片", "教学设计怎么写", "演示文稿"):
            self.assertTrue(routing.involves_plan_topic(q)[0], q)

    def test_involves_by_retrieval(self):
        """老师上传过教案/课件 PDF 时，命中片段里会带这些词。"""
        hits = [_Hit("本课教学目标如下…", source="人教版教案.pdf", heading="教学目标", page=1)]
        ok, why = routing.involves_plan_topic("这节课怎么安排", hits)
        self.assertTrue(ok)
        self.assertEqual(why, "retrieval")

    def test_not_involved(self):
        hits = [_Hit("函数的单调性定义：区间上取 x1<x2…", source="必修一.pdf",
                     heading="函数的基本性质", page=76)]
        for q in ("什么是函数的单调性", "单调性怎么判断"):
            self.assertEqual(routing.involves_plan_topic(q, hits), (False, ""), q)

    def test_empty_hits_and_plain_text(self):
        self.assertEqual(routing.involves_plan_topic("", None), (False, ""))
        self.assertFalse(routing.involves_plan_topic("求导", [])[0])


class TestPrompts(unittest.TestCase):
    def test_template_guard_filled(self):
        txt = prompts.PLAN_TEMPLATE_GUARD.format(skeleton="1. 教学目标\n2. 教学过程")
        self.assertIn("1. 教学目标", txt)
        self.assertIn("不得增删板块", txt)
        self.assertIn("本板块教材依据不足", txt)      # 本次补的那条规则

    def test_answer_prompt_forbids_plan(self):
        self.assertIn("不越界写教案", prompts.SYSTEM_PROMPT)
        self.assertIn("生成教案模板", prompts.SYSTEM_PROMPT)

    def test_template_json_contract(self):
        self.assertIn("table_head", prompts.TEMPLATE_JSON)
        self.assertIn("expect", prompts.TEMPLATE_JSON)


class TestTemplateObjToRich(unittest.TestCase):
    OBJ = {
        "title": "新授课通用模板",
        "blocks": [
            {"title": "教学目标", "level": 1, "hint": "写 2~3 条可检测的目标", "expect": "text"},
            {"title": "教学过程", "level": 1, "hint": "按环节填写", "expect": "table",
             "table_head": ["教学环节", "教师活动", "学生活动", "时间"]},
            {"title": "", "hint": "空标题应被丢弃"},
        ],
    }

    def test_blocks_and_hint(self):
        rich = planner.template_obj_to_rich(self.OBJ)
        titles = [b["title"] for b in rich["blocks"]]
        self.assertEqual(titles, ["教学目标", "教学过程"])
        p = rich["blocks"][0]["elements"][0]
        self.assertEqual(p["type"], "para")
        self.assertIn("可检测的目标", p["text"], "填写提示应落到段落里")

    def test_table_header_from_head(self):
        rich = planner.template_obj_to_rich(self.OBJ)
        tbl = rich["blocks"][1]["elements"][0]
        self.assertEqual(tbl["type"], "table")
        self.assertEqual([c["text"] for c in tbl["cells"][0]],
                         ["教学环节", "教师活动", "学生活动", "时间"])
        self.assertTrue(all(c["b"] for c in tbl["cells"][0]), "表头应加粗")

    def test_is_valid_rich_template(self):
        rich = planner.template_obj_to_rich(self.OBJ, fallback_name="回退名")
        self.assertEqual(rich["spec_version"], tr.SPEC_VERSION)
        self.assertTrue(rich["template_id"])
        st = tr.stats(rich)
        self.assertEqual(st["blocks"], 2)
        self.assertEqual(st["tables"], 1)

    def test_markdown_skeleton(self):
        rich = planner.template_obj_to_rich(self.OBJ)
        md = planner.template_to_markdown(rich)
        self.assertIn("1. 教学目标", md)
        self.assertIn("【表格板块】教学过程", md)


class TestOptionsEvent(unittest.TestCase):
    class _Req:
        template_id = "default"
        session_id = ""

    def test_plan_mode_always_gets_options(self):
        ev = ws._plan_options_event(self._Req(), "帮我生成教案", "B", None)
        self.assertIsNotNone(ev)
        self.assertEqual(ev["t"], "options")
        self.assertEqual([o["id"] for o in ev["options"]],
                         ["gen_template", "use_template", "fill_center"])
        self.assertEqual(ev["reason"], "plan_mode")
        use = [o for o in ev["options"] if o["id"] == "use_template"][0]
        self.assertIn("templates", use)
        self.assertIn("current", use)

    def test_coach_with_signal_gets_options(self):
        last = {"t": "done", "plan_options": {"suggest": True, "reason": "retrieval"}}
        ev = ws._plan_options_event(self._Req(), "这节课怎么安排", "A", last)
        self.assertIsNotNone(ev)
        self.assertEqual(ev["reason"], "retrieval")

    def test_fill_option_only_when_there_is_a_plan(self):
        """③「填入教案中心」只在会话里真有教案正文时出现（没东西可填就别给按钮）。"""
        last = {"t": "done", "plan_options": {"suggest": True, "reason": "intent"}}
        with mock.patch.object(ws, "_last_plan_markdown", return_value=""):
            ev = ws._plan_options_event(self._Req(), "写个教案", "A", last)
            self.assertEqual([o["id"] for o in ev["options"]], ["gen_template", "use_template"])
        with mock.patch.object(ws, "_last_plan_markdown", return_value="# 幂函数\n**教学目标**\n- 理解"):
            ev2 = ws._plan_options_event(self._Req(), "写个教案", "A", last)
            self.assertIn("fill_center", [o["id"] for o in ev2["options"]])

    def test_coach_without_signal_no_options(self):
        self.assertIsNone(ws._plan_options_event(self._Req(), "什么是单调性", "A", {"t": "done"}))
        self.assertIsNone(ws._plan_options_event(self._Req(), "什么是单调性", "A", None))

    def test_stream_passthrough_and_append(self):
        def gen():
            yield {"t": "d", "text": "正"}
            yield {"t": "done", "text": "正文", "plan_options": {"suggest": True, "reason": "intent"}}
        evs = list(ws._with_plan_options(gen(), self._Req(), "讲讲教案", "A"))
        self.assertEqual([e["t"] for e in evs], ["d", "done", "options"])

    def test_stream_without_options(self):
        def gen():
            yield {"t": "done", "text": "正文"}
        evs = list(ws._with_plan_options(gen(), self._Req(), "什么是单调性", "A"))
        self.assertEqual([e["t"] for e in evs], ["done"])


if __name__ == "__main__":
    unittest.main()
