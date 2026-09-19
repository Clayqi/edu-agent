"""routing 单一来源 + supervisor/graph 接线测试（零网络、纯规则）。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from edu_agent import routing


class RoutingDecideTest(unittest.TestCase):

    def test_plain_question_goes_A(self):
        self.assertEqual(routing.decide("函数的单调性怎么判断？"), "A")

    def test_plan_intent_goes_B(self):
        for q in ("写一份函数的单调性的教案", "帮我备课：对数函数",
                  "教学目标怎么写？", "板书设计怎么做", "怎么讲指数函数",
                  "帮我安排上课环节（新课导入怎么设计）"):
            self.assertEqual(routing.decide(q), "B", q)

    def test_supervisor_only_words_merged(self):
        # 收口前 supervisor 独有 / graph 独有的词，现在单表统一命中 B
        for q in ("这节课怎么上课？", "帮我设计课件", "我要导学案"):
            self.assertTrue(routing.want_plan(q), q)

    def test_explicit_mode_wins_over_keywords(self):
        self.assertEqual(routing.decide("随便什么内容", mode="B"), "B")
        self.assertEqual(routing.decide("写一份教案", mode="A"), "A")
        self.assertEqual(routing.decide("x", mode="coach"), "A")
        self.assertEqual(routing.decide("x", mode="plan"), "B")

    def test_auto_mode_equals_default(self):
        self.assertEqual(routing.decide("什么是奇函数？", mode="auto"), "A")
        self.assertEqual(routing.decide("教案怎么写", mode="auto"), "B")


class WiringTest(unittest.TestCase):
    """supervisor / graph 不再自维护词表，均委托 routing。"""

    def test_supervisor_decide_delegates(self):
        from edu_agent import supervisor

        for q in ("什么是奇函数？", "备一节指数函数的课", "帮我做教学设计"):
            self.assertEqual(supervisor.decide(q), routing.decide(q), q)

    def test_graph_plan_hints_is_single_source(self):
        from edu_agent import graph

        self.assertIs(graph.PLAN_HINTS, routing.PLAN_HINTS)
        self.assertIs(graph.want_plan, routing.want_plan)


if __name__ == "__main__":
    unittest.main()
