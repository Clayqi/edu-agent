# -*- coding: utf-8 -*-
"""graph.py 编排层测试：路由逻辑 / 图级路由 / 节点隔离与 P1 学情拼接。

全 mock（节点桩），零网络/零向量库/零 LLM。
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import edu_agent.graph as g


class TestRouteLogic(unittest.TestCase):
    """纯逻辑：意图词与条件边路由（不碰节点）。"""

    def test_plan_keywords(self):
        for t in ["帮我写一份教案", "备课：函数的单调性", "怎么做教学设计",
                  "为3.2.1生成教案", "教学目标怎么写"]:
            self.assertTrue(g._want_plan(t), t)

    def test_coach_plain_question(self):
        for t in ["什么是集合？", "3.2 例2怎么做", "函数的单调性怎么判断？",
                  "奇函数和偶函数有什么区别"]:
            self.assertFalse(g._want_plan(t), t)

    def test_route_explicit_mode(self):
        self.assertEqual(g._route({"text": "什么是集合？", "mode": "plan"}), "plan")
        self.assertEqual(g._route({"text": "帮我备课", "mode": "coach"}), "coach")

    def test_route_by_keyword_and_default(self):
        self.assertEqual(g._route({"text": "帮我写教案"}), "plan")
        self.assertEqual(g._route({"text": "什么是集合？"}), "coach")
        self.assertEqual(g._route({}), "coach")


class TestGraphRouting(unittest.TestCase):
    """图级：桩替换节点后验证 invoke 走到正确分支。"""

    def setUp(self):
        self._orig_coach, self._orig_plan = g._coach_node, g._plan_node
        self.calls = []

        def coach(state):
            self.calls.append(("coach", dict(state)))
            return {"output_md": "A答", "error": "", "mode": "coach"}

        def plan(state):
            self.calls.append(("plan", dict(state)))
            return {"output_md": "B教案", "error": "", "mode": "plan"}

        g._coach_node, g._plan_node = coach, plan
        g._graph = None  # 强制用桩重建编译图

    def tearDown(self):
        g._coach_node, g._plan_node = self._orig_coach, self._orig_plan
        g._graph = None

    def test_auto_route_to_coach(self):
        out = g.ask("什么是函数的单调性？")
        self.assertEqual(out["mode"], "coach")
        self.assertEqual(self.calls[0][0], "coach")

    def test_auto_route_to_plan(self):
        out = g.ask("帮我生成一份教案")
        self.assertEqual(out["mode"], "plan")
        self.assertEqual(self.calls[0][0], "plan")

    def test_ask_coach_forces_a(self):
        out = g.ask_coach("3.2.1 例2")
        self.assertEqual(out["mode"], "coach")

    def test_ask_plan_carries_fields(self):
        out = g.ask_plan("函数的单调性", goal="重点班45分钟",
                         template_id="t1", coach_summary="学生问了单调性，A 答了定义")
        self.assertEqual(out["mode"], "plan")
        state = self.calls[0][1]
        self.assertEqual(state["knowledge_point"], "函数的单调性")
        self.assertEqual(state["goal"], "重点班45分钟")
        self.assertEqual(state["template_id"], "t1")
        # 学情摘要作为独立字段原样到达 plan 节点（拼接逻辑见 TestPlanNodeSummary）
        self.assertEqual(state["coach_summary"], "学生问了单调性，A 答了定义")


class TestPlanNodeSummary(unittest.TestCase):
    """_plan_node 的 P1 学情拼接：coach_summary 自动并入 goal，无则原样。"""

    def setUp(self):
        import edu_agent.planner as planner_mod
        self._planner = planner_mod
        self._orig_make_plan = planner_mod.make_plan
        self._orig_to_md = planner_mod.to_markdown
        self.received = {}

        def fake_make_plan(kp, goal="", template=None):
            self.received = {"kp": kp, "goal": goal, "template": template}
            return SimpleNamespace(title=f"《{kp}》教案", objectives=[], key_points=[],
                                   flow_steps=[], mistakes=[], citations=[])

        planner_mod.make_plan = fake_make_plan
        planner_mod.to_markdown = lambda rec: f"# {rec.title}\n教案正文"

    def tearDown(self):
        self._planner.make_plan = self._orig_make_plan
        self._planner.to_markdown = self._orig_to_md

    def test_summary_merged_into_goal(self):
        out = g._plan_node({
            "knowledge_point": "函数的单调性",
            "goal": "重点班",
            "coach_summary": "学生刚问单调性怎么判断，A 答按定义作差",
        })
        self.assertEqual(out["error"], "")
        self.assertIn("学生前情", self.received["goal"])
        self.assertIn("重点班", self.received["goal"])
        self.assertIn("学生刚问单调性怎么判断", self.received["goal"])

    def test_no_summary_goal_untouched(self):
        out = g._plan_node({"knowledge_point": "函数的单调性", "goal": "普通班"})
        self.assertEqual(self.received["goal"], "普通班")
        self.assertEqual(out["mode"], "plan")

    def test_plan_node_error_isolation(self):
        self._planner.make_plan = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        out = g._plan_node({"knowledge_point": "x"})
        self.assertIn("不可用或出错", out["output_md"])
        self.assertIn("boom", out["error"])


class TestGraphBuilds(unittest.TestCase):
    def test_compile_without_invoke(self):
        gr = g._get_graph()
        self.assertIsNotNone(gr)
        # 编译图再次获取走缓存
        self.assertIs(g._get_graph(), gr)


if __name__ == "__main__":
    unittest.main()
