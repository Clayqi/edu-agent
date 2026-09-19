# -*- coding: utf-8 -*-
"""edu-math MCP server：课本教练的计算验证工具（本地 stdio，sympy 内核）。

路线 B「能力挂载」的第一块：一个真正独立的 MCP server 进程，
对教育agent 主进程暴露 5 个白名单数学工具：
  derivative          求导
  monotonic_intervals 单调区间（解 f'(x)>0 / <0）
  solve_equation      解方程/不等式（=、>、<、>=、<=）
  evaluate            代入求值
  simplify            化简

输入兼容高中写法：x^2-4x+3（^ 幂、省略乘号）都会被解析。
工具只返回文本；解析失败返回 ERR: ... 字符串，不抛异常（client 侧另有兜底）。

启动（stdio，由 client 拉起，也可手动测）：
  .venv\\Scripts\\python.exe mcp_servers/math_server.py
"""
from __future__ import annotations

import re

import sympy as sp
from mcp.server.fastmcp import FastMCP
from sympy.core.relational import Equality, Relational
from sympy.parsing.sympy_parser import (
    convert_equals_signs,
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

mcp = FastMCP("edu-math")

# 教学友好解析：^ -> **、省略乘号(4x -> 4*x)、= -> Eq
# sympy 1.14 起 = 号转换函数名为 convert_equals_signs（旧 convert_equality_inequalities 已移除）
_TRANS = standard_transformations + (
    convert_xor,
    implicit_multiplication_application,
    convert_equals_signs,
)


def _parse(expr: str, var: str = "x"):
    """解析用户表达式，返回 (expr, Symbol)。失败抛异常由调用方捕获。"""
    v = sp.Symbol(var)
    return parse_expr(expr, transformations=_TRANS, local_dict={var: v}), v


def _safe(fn):
    """把异常转成 'ERR: ...' 字符串，保证工具永远可返回。
    functools.wraps 必须保留：FastMCP 靠 inspect.signature 生成参数 schema，
    没有它包装器会暴露成 (*a, **kw) 两个必填字段。"""
    import functools

    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return str(fn(*a, **kw))
        except Exception as e:
            return "ERR: %s" % e
    return wrapper


def _fmt_set(sol) -> str:
    """把 sympy 解集格式化成教学可读串：(-∞, 1) ∪ (3, +∞)、{1, 3}、无解。"""
    if sol is sp.S.EmptySet:
        return "无解"
    if sol is sp.S.Reals:
        return "全体实数"
    if isinstance(sol, sp.Interval):
        l, r = sol.left, sol.right
        ls = "-∞" if l is sp.S.NegativeInfinity else str(l)
        rs = "+∞" if r is sp.S.Infinity else str(r)
        a = "(" if sol.left_open else "["
        b = ")" if sol.right_open else "]"
        return "%s%s, %s%s" % (a, ls, rs, b)
    if isinstance(sol, sp.Union):
        return " ∪ ".join(_fmt_set(a) for a in sol.args)
    if isinstance(sol, sp.FiniteSet):
        return "{" + ", ".join(str(v) for v in sol.args) + "}"
    return str(sol)


@mcp.tool()
@_safe
def derivative(expr: str, var: str = "x") -> str:
    """对函数表达式求导。例：derivative('x^2-4x+3') -> 2*x - 4"""
    f, x = _parse(expr, var)
    return sp.diff(f, x)


@mcp.tool()
@_safe
def monotonic_intervals(expr: str, var: str = "x") -> str:
    """求函数单调区间：解 f'(x)>0（增）与 f'(x)<0（减）。例：monotonic_intervals('x^2-4x+3')"""
    f, x = _parse(expr, var)
    d = sp.diff(f, x)
    inc = sp.solve_univariate_inequality(d > 0, x, relational=False)
    dec = sp.solve_univariate_inequality(d < 0, x, relational=False)
    return "增区间: %s; 减区间: %s" % (_fmt_set(inc), _fmt_set(dec))


@mcp.tool()
@_safe
def solve_equation(expr: str, var: str = "x") -> str:
    """解方程或不等式（支持 = > < >= <=）。例：solve_equation('x^2-4x+3>0') 或 solve_equation('x^2-4x+3=0')"""
    e, x = _parse(expr, var)
    if isinstance(e, Relational):
        if isinstance(e, Equality):
            return "解集: %s" % _fmt_set(sp.solveset(e, x, domain=sp.S.Reals))
        return "解集: %s" % _fmt_set(
            sp.solve_univariate_inequality(e, x, relational=False))
    # 裸表达式按 =0 处理
    return "解集: %s" % _fmt_set(sp.solveset(sp.Eq(e, 0), x, domain=sp.S.Reals))


@mcp.tool()
@_safe
def evaluate(expr: str, var: str = "x", value: str = "0") -> str:
    """代入求值。例：evaluate('x^2-4x+3', 'x', '2') -> -1"""
    f, x = _parse(expr, var)
    return f.subs(x, sp.sympify(value))


@mcp.tool()
@_safe
def simplify(expr: str) -> str:
    """化简表达式。例：simplify('(x+1)^2-(x-1)^2') -> 4*x"""
    e, _ = _parse(expr)
    return sp.simplify(e)


if __name__ == "__main__":
    # stdio transport 是默认；显式写明便于阅读
    mcp.run(transport="stdio")
