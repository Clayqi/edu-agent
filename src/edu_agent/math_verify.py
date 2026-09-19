# -*- coding: utf-8 -*-
"""机器验证挂载：检测「可计算」的数学问题 -> 抽表达式 -> 调 edu-math MCP -> 附加验证行。

路线 B「能力挂载」的编排层，挂在 generate.ask / ask_stream 的出口：
- 只在问题命中计算意图 且 能抽出可信表达式时才启动 MCP（每次 ~2-3s，低频可接受）
- 永不抛异常、永不阻塞主链路：任何失败都原样返回 answer_md
- 幂等：answer 里已有验证标记则跳过（防 ask/ask_stream 双路径重复附加）

用法：
    from edu_agent import math_verify
    answer_md = math_verify.attach_verify(question, answer_md)
"""
from __future__ import annotations

import re

_VERIFY_MARK = "机器验证"

# 工具意图 -> (关键词正则, 展示用标签)
_INTENTS: list[tuple[str, re.Pattern, str]] = [
    ("monotonic_intervals", re.compile(r"单调"), "单调区间"),
    ("derivative", re.compile(r"求导|导数|导函数|的导\b"), "导数"),
    ("solve_equation", re.compile(r"解方程|解不等式|解集|求.+的解"), "解集"),
    ("simplify", re.compile(r"化简|恒等变形"), "化简"),
]

_FULL2HALF = {ord(c): ord(h) for c, h in zip(
    "０１２３４５６７８９．（）＋－＊／＜＞＝，",
    "0123456789.()+-*/<>=,,")}
_SUP = {"⁰": "^0", "¹": "^1", "²": "^2", "³": "^3", "⁴": "^4",
        "⁵": "^5", "⁶": "^6", "⁷": "^7", "⁸": "^8", "⁹": "^9"}


def normalize_expr(s: str) -> str:
    """全角 -> 半角、上标 -> ^n、去空白；供服务端解析前的统一。"""
    s = s.translate(_FULL2HALF)
    for k, v in _SUP.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", "", s)


# f(x)=... / y=... 等号后的式子（最稳，优先）。
# 不用尾随前瞻：字符类本身不含空格/中文，遇类外字符即停。
_RE_EQ = re.compile(
    r"(?:[a-zA-Z]\s*\(\s*x\s*\)|y)\s*=\s*([0-9a-zA-Z+\-*/^()<>=.²³]+)")
# 独立等式/不等式全段（x^2=4、x^2-4x+3>0、f(x)>0）——solve 用
_RE_REL = re.compile(
    r"([0-9a-zA-Z+\-*/^().²³]*[<>=]=?[0-9a-zA-Z+\-*/^().²³]*[<>=]?[0-9a-zA-Z+\-*/^().²³]*)")
# 关键词后的裸式子（求导 x^3、化简 (x+1)^2-(x-1)^2、x^3 的导数）
_RE_BARE = re.compile(
    r"(?:求导|导数|化简)\s*(?:为|得|：|:)?\s*"
    r"([a-zA-Z(][0-9a-zA-Z+\-*/^().²³]{1,50})")


def detect_tool(question: str) -> str | None:
    """命中计算意图 -> 工具名；否则 None。"""
    for name, pat, _label in _INTENTS:
        if pat.search(question):
            return name
    return None


def extract_expr(question: str, tool: str) -> str | None:
    """按工具抽取表达式；抽不到或不可信返回 None。"""
    cands: list[str] = []
    if tool == "solve_equation":
        for m in _RE_EQ.finditer(question):
            cands.append(m.group(1))
        for m in _RE_REL.finditer(question):
            cands.append(m.group(1))
    else:
        for m in _RE_EQ.finditer(question):
            cands.append(m.group(1))
        for m in _RE_BARE.finditer(question):
            cands.append(m.group(1))
    for raw in cands:
        e = normalize_expr(raw)
        # 质量闸：太短/无变量字母/无运算内容的不要（避免把题干废话当式子）
        if not (2 <= len(e) <= 60):
            continue
        if not re.search(r"[a-zA-Z]", e):
            continue
        return e
    return None


def calc_text(tool: str, expr: str) -> str | None:
    """调 MCP 计算，返回带标签的可读结果。任何失败 -> None。"""
    from edu_agent.mcp_tools import mcp_call

    label = next((lb for n, _p, lb in _INTENTS if n == tool), tool)
    out = mcp_call(tool, expr=expr)
    if out is None or str(out).startswith("ERR"):
        return None
    return "%s：%s" % (label, out)


def attach_verify(question: str, answer_md: str) -> str:
    """把机器验证段附加到回答末尾。幂等 + 永不抛。"""
    if not question or not answer_md or _VERIFY_MARK in answer_md:
        return answer_md
    try:
        tool = detect_tool(question)
        if tool is None:
            return answer_md
        expr = extract_expr(question, tool)
        if expr is None:
            return answer_md
        text = calc_text(tool, expr)
        if text is None:
            return answer_md
        return "%s\n\n> **机器验证**（本地 MCP 数学服务，非教材原文）：%s" % (
            answer_md.rstrip(), text)
    except Exception:
        return answer_md
