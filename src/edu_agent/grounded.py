"""S8 实现：引用校验 + 诚实降级。

防幻觉三层防线（依计划 §3.2-4）：
  1) 约束生成：论断带 [n] 引用（generate.py 已做）
  2) 引用规整：只保留真实编号并补齐坐标（generate.py 已做）
  3) 置信降级：无有效引用 / 检索置信过低 -> 诚实说明而非硬编
"""
from __future__ import annotations

import re

from edu_agent import prompts
from edu_agent.generate import AnswerRecord, Citation


def validate(rec: AnswerRecord) -> list[str]:
    """规则级引用校验，返回问题列表（空 = 通过）。

    检查：答案里用到的 [n] 都在 citations 中；每个 citation 带坐标。
    """
    issues: list[str] = []
    used = set(int(m) for m in re.findall(r"\[(\d+)\]", rec.answer_md))
    cited = {c.index for c in rec.citations}
    for n in used:
        if n not in cited:
            issues.append(f"答案引用 [{n}] 无对应 citation")
    for c in rec.citations:
        if not (c.chapter and (c.section or c.heading)):
            issues.append(f"citation [{c.index}] 缺坐标")
    return issues


_DEGRADE_KIND = {
    "empty": prompts.DEGRADE_EMPTY,
    "parse_error": prompts.DEGRADE_PARSE,
    "low_confidence": prompts.DEGRADE_LOWCONF,
    "out_of_scope": prompts.DEGRADE_TEXT,
}


def _infer_kind(reason: str) -> str:
    """无显式 kind 时按 reason 关键词推断降级类型（向后兼容旧调用）。"""
    if not reason:
        return "out_of_scope"
    if "解析失败" in reason or "校验" in reason:
        return "parse_error"
    if "检索为空" in reason:
        return "empty"
    if "置信" in reason or "引用" in reason:
        return "low_confidence"
    return "out_of_scope"


def degrade(question: str, reason: str = "", kind: str | None = None) -> AnswerRecord:
    """诚实降级：按失败原因给不同话术，绝不把系统问题说成"教材未收录"。

    kind（2026-09-07 P0 修复后按原因分型）：
      empty          没检索到内容（问法太口语/太简略）
      parse_error    生成/解析/校验失败（系统问题，引导重试）
      low_confidence 检索置信过低（引导换问法）
      out_of_scope   教材真的没讲（默认，沿用 DEGRADE_TEXT）
    reason 以"内部原因"小字附在文末，便于 George 排查，不干扰学生阅读。
    """
    k = kind or _infer_kind(reason)
    body = _DEGRADE_KIND.get(k, prompts.DEGRADE_TEXT)
    note = f"\n\n> 内部原因：{reason}" if reason else ""
    tail = f"\n\n（你的问题：{question}）" if question else ""
    return AnswerRecord(
        answer_md=body + note + tail,
        citations=[],
        coverage="low",
        confidence=0.0,
    )
