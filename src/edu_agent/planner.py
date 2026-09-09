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

        tpl_block = (
            "\n\n【本次教案必须使用的模板（板块名称与顺序严格照此产出，不得增删板块；表格板块请输出为 Markdown 表格；"
            "板块标题若含具体课题名（如《函数的概念》）且本次课题不同，可把课题名替换为本次课题，其余标题措辞保持模板原样）。"
            "篇幅纪律：内容精炼可上课用——每板块简而准，目标每条不超过40字，不要空话套话】\n"
            + template_sketch(template)
        )
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
