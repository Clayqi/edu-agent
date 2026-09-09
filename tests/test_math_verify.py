# -*- coding: utf-8 -*-
"""math_verify.py + mcp_servers/math_server.py 测试（路线 B「能力挂载」）。

- math_verify：检测/抽取/附加逻辑（mock MCP 调用，零子进程）
- math_server：5 工具数学正确性直测（sympy 本地计算，零网络）
- mcp_tools：白名单拦截（不触发 stdio）
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_PROJ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJ / "src"))
sys.path.insert(0, str(_PROJ / "mcp_servers"))

from edu_agent import math_verify as mv
from edu_agent import mcp_tools


class TestNormalize(unittest.TestCase):
    def test_fullwidth_and_superscript(self):
        self.assertEqual(mv.normalize_expr("x²-4x+3"), "x^2-4x+3")
        self.assertEqual(mv.normalize_expr("（x＋1）²"), "(x+1)^2")
        self.assertEqual(mv.normalize_expr("x  ^  2"), "x^2")


class TestDetectTool(unittest.TestCase):
    def test_intents(self):
        self.assertEqual(mv.detect_tool("求 f(x)=x^2 的导数"), "derivative")
        self.assertEqual(mv.detect_tool("f(x)=x^2 的单调区间"), "monotonic_intervals")
        self.assertEqual(mv.detect_tool("解不等式 x^2-4x+3>0"), "solve_equation")
        self.assertEqual(mv.detect_tool("化简 (x+1)^2"), "simplify")

    def test_no_intent(self):
        for q in ["集合是什么", "对数的运算规则有哪些", "什么是充分条件"]:
            self.assertIsNone(mv.detect_tool(q), q)


class TestExtractExpr(unittest.TestCase):
    def test_extract_forms(self):
        cases = [
            ("求 f(x)=x^2-4x+3 的导数", "derivative", "x^2-4x+3"),
            ("f(x)=x²-4x+3 的单调区间是什么", "monotonic_intervals", "x^2-4x+3"),
            ("求 y=2x+1 的单调性", "monotonic_intervals", "2x+1"),
            ("解不等式 x^2-4x+3>0", "solve_equation", "x^2-4x+3>0"),
            ("解方程 x^2=4", "solve_equation", "x^2=4"),
            ("化简 (x+1)^2-(x-1)^2", "simplify", "(x+1)^2-(x-1)^2"),
            ("求导 x^3", "derivative", "x^3"),
        ]
        for q, tool, want in cases:
            self.assertEqual(mv.extract_expr(q, tool), want, q)

    def test_garbage_rejected(self):
        # 无字母（纯数字/废话）抽不出可信表达式
        self.assertIsNone(mv.extract_expr("什么是函数的单调性", "monotonic_intervals"))
        self.assertIsNone(mv.extract_expr("化简 12345", "simplify"))


class TestAttachVerify(unittest.TestCase):
    def test_attach_success(self):
        with patch("edu_agent.math_verify.calc_text", return_value="导数：2*x - 4") as m:
            out = mv.attach_verify("求 f(x)=x^2-4x+3 的导数", "教材答案…")
            m.assert_called_once_with("derivative", "x^2-4x+3")
        self.assertIn("机器验证", out)
        self.assertIn("2*x - 4", out)

    def test_calc_failure_returns_original(self):
        with patch("edu_agent.math_verify.calc_text", return_value=None):
            out = mv.attach_verify("求 f(x)=x^2 的导数", "原答案")
        self.assertEqual(out, "原答案")

    def test_no_intent_returns_original(self):
        self.assertEqual(mv.attach_verify("集合是什么", "原答案"), "原答案")

    def test_no_expr_returns_original(self):
        self.assertEqual(mv.attach_verify("什么是函数的单调性", "原答案"), "原答案")

    def test_idempotent(self):
        with patch("edu_agent.math_verify.calc_text") as m:
            out = mv.attach_verify("求导 x^3", "已有 **机器验证** 字样")
            m.assert_not_called()
        self.assertEqual(out, "已有 **机器验证** 字样")

    def test_empty_inputs(self):
        self.assertEqual(mv.attach_verify("", "答案"), "答案")
        self.assertEqual(mv.attach_verify("求导 x^3", ""), "")


class TestMcpToolsWhitelist(unittest.TestCase):
    def test_allowed_names(self):
        self.assertIn("derivative", mcp_tools.ALLOWED)
        self.assertIn("monotonic_intervals", mcp_tools.ALLOWED)

    def test_unknown_tool_blocked_without_io(self):
        # 白名单外的名字在触碰任何 IO/子进程前直接返回 None
        self.assertIsNone(mcp_tools.mcp_call("rm_rf_evil", expr="x"))


class TestMathServer(unittest.TestCase):
    """math_server 5 工具直测（sympy 本地，零网络）。"""

    @classmethod
    def setUpClass(cls):
        import math_server
        cls.ms = math_server

    def test_derivative(self):
        self.assertEqual(self.ms.derivative(expr="x^2-4x+3"), "2*x - 4")
        self.assertEqual(self.ms.derivative(expr="sin(x)"), "cos(x)")

    def test_monotonic(self):
        out = self.ms.monotonic_intervals(expr="x^2-4x+3")
        self.assertIn("(2, +∞)", out)
        self.assertIn("(-∞, 2)", out)

    def test_solve_inequality(self):
        out = self.ms.solve_equation(expr="x^2-4x+3>0")
        self.assertIn("(-∞, 1)", out)
        self.assertIn("(3, +∞)", out)

    def test_solve_equality(self):
        out = self.ms.solve_equation(expr="x^2-4x+3=0")
        self.assertEqual(out, "解集: {1, 3}")

    def test_solve_no_solution(self):
        self.assertEqual(self.ms.solve_equation(expr="x^2<0"), "解集: 无解")

    def test_evaluate_and_simplify(self):
        self.assertEqual(self.ms.evaluate(expr="x^2-4x+3", var="x", value="2"), "-1")
        self.assertEqual(self.ms.simplify(expr="(x+1)^2-(x-1)^2"), "4*x")

    def test_bad_input_returns_err(self):
        self.assertTrue(self.ms.derivative(expr="###").startswith("ERR"))


if __name__ == "__main__":
    unittest.main()
