"""Agent2：教案 Agent（LangGraph 协作中的 plan 节点）。

    make_plan(knowledge_point, goal) -> PlanRecord
基于课本向量库，针对老师给的 知识点 + 教学问题/目标，产出结构化教案。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]

from edu_agent import prompts
from edu_agent.config import get_chat_llm
from edu_agent.generate import Citation, plainify_math
from edu_agent.retrieve import retrieve


class FlowStep(BaseModel):
    phase: str
    minutes: int = 5
    content: str = ""


class PlanRecord(BaseModel):
    title: str = ""
    objectives: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    flow_steps: list[FlowStep] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


# ==================== 选项①：让 Agent 生成「教案模板」（2026-09-12 一期） ====================
def _strip_fence(raw: str) -> str:
    t = re.sub(r"^```(?:json)?\s*", "", (raw or "").strip())
    return re.sub(r"\s*```$", "", t)


def _para(text: str) -> dict:
    """模板里的占位段落（承载填写提示）。"""
    from edu_agent import template_rich as tr

    return {"id": tr._uid("e"), "type": "para", "text": text or "", "align": "",
            "line_spacing": None, "style": "", "level": 0,
            "runs": [{"text": text or "", "b": False, "i": False, "u": False,
                      "font": "宋体", "size": None, "color": ""}]}


def template_obj_to_rich(obj: dict, fallback_name: str = "AI 生成模板") -> dict:
    """把 LLM 产出的模板 JSON 转成富模板（v2）：板块骨架 + 填写提示 + 表格表头。"""
    from edu_agent import template_rich as tr

    blocks: list[dict] = []
    for b in (obj.get("blocks") or []):
        if not isinstance(b, dict):
            continue
        title = str(b.get("title") or "").strip()
        if not title:
            continue
        hint = str(b.get("hint") or "").strip()
        els: list[dict] = []
        expect = str(b.get("expect") or "text").lower()
        if expect == "table":
            head = [str(x).strip() for x in (b.get("table_head") or []) if str(x).strip()]
            head = head[:6] or ["环节", "内容"]
            cells = [[{"text": h, "b": True, "align": "center"} for h in head]]
            cells.append([{"text": "", "b": False, "align": ""} for _ in head])
            els.append({"id": tr._uid("e"), "type": "table", "header": True, "cells": cells})
            if hint:
                els.append(_para("（填写提示）" + hint))
        else:
            # 段落板块的填写提示也带前缀（与表格板块一致）：① 生成的模板里一眼能分出
            # 「这是提示」还是「这是内容」，教案中心也据此判断哪些板块还空着。
            els.append(_para(("（填写提示）" + hint) if hint else "（在此填写内容）"))
        blocks.append({"id": tr._uid("b"), "kind": "section",
                       "level": max(1, min(tr.MAX_LEVEL, int(b.get("level") or 1))),
                       "title": title, "elements": els})
    name = str(obj.get("title") or "").strip() or fallback_name
    return tr.normalize({"template_id": name, "name": name, "source": "ai",
                         "blocks": blocks})


def make_template(topic: str, goal: str = "", top_k: int = 4,
                  extra_req: str = "") -> dict:
    """按课题产出教案模板（富模板 dict）。检索不到片段也照做——模板是结构，不强依赖片段。"""
    hits = []
    try:
        hits = retrieve((topic + " " + goal).strip(), kinds=["concept", "section"], top_k=top_k)
    except Exception:
        hits = []

    snips = []
    for i, h in enumerate(hits, 1):
        md = h.metadata
        snips.append(prompts.SNIPPET_TMPL.format(
            i=i, chapter=md.get("chapter", ""), section=md.get("section", "") or "",
            heading=md.get("heading", "") or "", page=md.get("page", "?"), text=h.text[:500]))

    user = (
        ("【检索到的教材片段】\n\n" + "\n\n".join(snips) + "\n\n") if snips
        else "【检索到的教材片段】\n\n（无——请只依据课题给出通用的板块划分）\n\n"
    ) + ("【课题】" + (topic or "（未指定）")) \
      + ("\n【教学问题/目标】" + goal if goal else "") \
      + ("\n\n【附加要求】" + extra_req if extra_req else "") \
      + "\n\n请据此产出教案模板。\n\n" + prompts.TEMPLATE_JSON

    llm = get_chat_llm(max_tokens=1500, timeout=240)
    raw = llm.invoke([{"role": "system", "content": prompts.TEMPLATE_SYSTEM},
                      {"role": "user", "content": user}]).content or ""
    obj = json.loads(_strip_fence(raw))
    return template_obj_to_rich(obj, fallback_name=(topic or "AI 生成模板") + " 模板")


def template_to_markdown(rich: dict) -> str:
    """富模板 -> 骨架提示文本（给前端「复制骨架」用）。"""
    lines = []
    for i, b in enumerate(rich.get("blocks") or [], 1):
        kinds = {e.get("type") for e in (b.get("elements") or [])}
        tag = "【表格板块】" if "table" in kinds else ""
        lines.append(f"{i}. {tag}{b.get('title', '')}")
    return "\n".join(lines)


def build_messages(kp: str, goal: str, hits, template=None,
                   extra_req: str = "") -> list[dict]:
    snips = []
    for i, h in enumerate(hits, 1):
        md = h.metadata
        snips.append(
            prompts.SNIPPET_TMPL.format(
                i=i,
                chapter=md.get("chapter", ""),
                section=md.get("section", "") or "",
                heading=md.get("heading", "") or "",
                page=md.get("page", "?"),
                text=h.text[:800],
            )
        )
    tpl_block = ""
    if template is not None:
        from edu_agent.template_spec import template_sketch

        # 约束文案已收口到 prompts.PLAN_TEMPLATE_GUARD（2026-09-12），这里只负责拼装
        tpl_block = "\n\n" + prompts.PLAN_TEMPLATE_GUARD.format(skeleton=template_sketch(template))
    user = (
        "【检索到的教材片段】\n\n" + "\n\n".join(snips)
        + "\n\n【备课要求】知识点：" + kp
        + ("\n教学问题/目标：" + goal if goal else "")
        + tpl_block
        + ("\n\n【本次附加要求】" + extra_req if extra_req else "")
        + "\n\n请据此生成教案。\n\n" + prompts.PLAN_JSON
    )
    return [{"role": "system", "content": prompts.PLAN_SYSTEM}, {"role": "user", "content": user}]


def _parse(raw: str) -> PlanRecord:
    t = re.sub(r"^```(?:json)?\s*", "", (raw or "").strip())
    t = re.sub(r"\s*```$", "", t)
    obj = json.loads(t)
    for c in obj.get("citations", []):
        c.setdefault("index", 0)
    rec = PlanRecord(**obj)
    rec.title = plainify_math(rec.title)
    rec.objectives = [plainify_math(x) for x in rec.objectives]
    rec.key_points = [plainify_math(x) for x in rec.key_points]
    for st in rec.flow_steps:
        st.content = plainify_math(st.content)
    rec.mistakes = [plainify_math(x) for x in rec.mistakes]
    for c in rec.citations:
        c.quote = c.quote[:80]
    return rec


def make_plan(knowledge_point: str, goal: str = "", top_k: int = 3,
              template=None, style: str = "", length: str = "") -> PlanRecord:
    """检索课本相关节 -> DeepSeek 生成结构化教案。

    style/length: 控制台参数面板透传（风格：传统/探究式/项目式；篇幅：简短/详细）。
    """
    reqs = []
    if style:
        reqs.append("教案风格：" + style)
    if length:
        reqs.append("篇幅要求：" + length)
    extra_req = "；".join(reqs)
    hits = retrieve(knowledge_point + " " + goal, kinds=["concept", "section"], top_k=top_k)
    if not hits:
        return PlanRecord(
            title=f"《{knowledge_point}》教案（课本未检索到对应内容）",
            objectives=["（本册教材未收录该知识点，建议核实章节）"],
        )
    if isinstance(template, str):
        from edu_agent.template_spec import get_template

        template = get_template(template)
    if template is None:
        from edu_agent.template_spec import get_current

        template = get_current()
    llm = get_chat_llm(max_tokens=6000, timeout=300)
    raw = llm.invoke(build_messages(knowledge_point, goal, hits, template,
                                    extra_req=extra_req)).content or ""
    try:
        rec = _parse(raw)
    except Exception as e:
        # 留档便于排查（截断/格式问题）
        try:
            (ROOT / "eval").mkdir(exist_ok=True)
            (ROOT / "eval" / "_plan_raw_fail.txt").write_text(raw[:6000], encoding="utf-8")
        except Exception:
            pass
        return PlanRecord(
            title=f"《{knowledge_point}》教案（生成失败，请重试）",
            objectives=[f"解析出错：{type(e).__name__}: {e}；原文已存 eval/_plan_raw_fail.txt 供排查。"],
        )
    # 引用规整
    allowed = {i + 1: h for i, h in enumerate(hits)}
    rec.citations = [c for c in rec.citations if c.index in allowed][:5]
    for c in rec.citations:
        h = allowed.get(c.index)
        if h:
            md = h.metadata
            c.chunk_id = md.get("chunk_id", "")
            c.chapter = md.get("chapter", "")
            c.section = md.get("section", "") or ""
            c.heading = md.get("heading", "") or ""
            c.page = md.get("page")
            c.quote = c.quote or h.text[:80]
    if not rec.title:
        rec.title = f"《{knowledge_point}》教案"
    return rec


def to_markdown(p: PlanRecord) -> str:
    lines = [f"# {p.title}", ""]
    if p.objectives:
        lines += ["**教学目标**"] + [f"- {x}" for x in p.objectives] + [""]
    if p.key_points:
        lines += ["**核心知识**"] + [f"- {x}" for x in p.key_points] + [""]
    if p.flow_steps:
        lines += ["**教学过程**"]
        for st in p.flow_steps:
            lines.append(f"### {st.phase}（约 {st.minutes} 分钟）")
            lines.append(st.content)
        lines.append("")
    if p.mistakes:
        lines += ["**易错点辨析（针对学生问题）**"] + [f"- {x}" for x in p.mistakes] + [""]
    if p.citations:
        lines += ["**教材依据**"]
        for c in p.citations[:5]:
            loc = f"{c.chapter} {c.section or ''} {c.heading or ''}".strip()
            lines.append(f"- [{c.index}] {loc} ｜ p{c.page} ｜ {c.quote}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    kp = sys.argv[1] if len(sys.argv) > 1 else "函数的单调性"
    goal = sys.argv[2] if len(sys.argv) > 2 else "学生总是混淆增函数与在区间上单调递增，怎么讲清楚？"
    plan = make_plan(kp, goal)
    print(to_markdown(plan))
