"""编排层：LangGraph Router 模式 —— 路由到两个【独立】Agent（课本教练 A / 教案 Agent B）。

架构定位（对照官方 docs.langchain.com Multi-agent 五模式之 Router，2026-09-07 学习落地）：
  - Router = 一个路由步骤把输入分类并导向专用 agent；本文件即该模式的无状态实现：
    分类依据 = 显式 mode 参数优先，其次 PLAN_HINTS 关键词规则（输入类别清晰时官方推荐确定性规则，不上 LLM）。
  - 独立性（《多Agent协作计划书 v0.2》§0 红线，逐条保持）：
      * Agent A（edu_agent.generate.ask/ask_turn）与 Agent B（edu_agent.planner.make_plan）
        各自独立模块、独立入口、独立输出契约（AnswerRecord / PlanRecord）；
      * 本文件只做路由与上下文传递，不内嵌任何一方的提示词与逻辑；
      * 节点内 lazy import + try/except 故障隔离：A/B 任一异常不影响对方与进程。
  - P1 协作（M5，可选增强）：State.coach_summary 携带 A 刚答过的学情摘要 -> B 的 goal
    自动拼接"学生前情"，B 独立决定是否采纳；不传时 B 照常出教案（独立性验收点）。

数据流：
  ask(text)            文本 → _route（关键词/显式 mode）→ coach | plan → END
  ask_coach(text)      强制走 Agent A（答疑页）
  ask_plan(kp, goal..) 强制走 Agent B（教案页），可带 A 的学情摘要 coach_summary

用法：
  python src/edu_agent/graph.py "怎么判断函数单调性？"     # 自动路由（普通问 -> A）
  python src/edu_agent/graph.py --plan "函数的单调性" "重点班45分钟"
"""
from __future__ import annotations

import re
import sys
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from edu_agent import logsetup
from edu_agent.routing import PLAN_HINTS, want_plan  # noqa: F401 —— 路由单一来源（收口）

log = logsetup.get_logger("graph")


class State(TypedDict, total=False):
    """编排层共享状态（LangGraph State）。字段分三组：输入 / Agent B 专用 / 输出。

    输入组：
      text: str            原始输入（自动路由时用；进 A 时为学生问题，进 B 时为知识点兜底）
      mode: str            显式路由："coach" 强制 A；"plan" 强制 B（缺省=按 text 关键词路由）
      coach_summary: str   （P1 协作）Agent A 刚答过的学情摘要，如 "学生问了函数的单调性怎么判断，
                           A 答：按定义作差比较[3.2 p76]。涉及页码 76-77"；传给 B 作为学生前情。
                           B 不依赖它，缺省照常出教案。
    输入组（Agent B 专用）：
      knowledge_point: str 知识点（B 的 make_plan 第一参数；缺省回退用 text）
      goal: str            教学问题/目标（老师给 B 的额外要求；与 coach_summary 自动拼接）
      template_id: str     教案模板 id（缺省=当前模板；对应 planner 的 template 参数）
    输出组：
      output_md: str       最终展示文本（A 的 answer_md 或 B 的教案 markdown）
      error: str           空=成功；非空=节点异常摘要（"类型: 消息"）
      mode: str            实际执行分支（"coach"/"plan"，便于 UI/日志区分）
    """

    # 输入组
    text: str
    mode: str
    coach_summary: str
    # 输入组（Agent B 专用）
    knowledge_point: str
    goal: str
    template_id: str
    # 输出组
    output_md: str
    error: str


def _want_plan(text: str) -> bool:
    """轻量意图判断：委托 routing（单一来源，不再自维护词表）。"""
    return want_plan(text)


def _route(state: State) -> Literal["coach", "plan"]:
    """条件边：返回下一节点名。显式 mode 优先，其次关键词规则。"""
    mode = state.get("mode")
    if mode in ("coach", "plan"):
        return mode
    return "plan" if _want_plan(state.get("text", "")) else "coach"


def _coach_node(state: State) -> dict:
    """Agent A 课本教练节点（独立）。lazy import + 异常隔离，输出 answer_md。

    输入取 state.text（学生问题）；history 透传由上层（session/前端）负责，
    本节点只承接单次提问（多轮用 generate.ask_turn 或经 web 网关会话，见 web_server.py）。
    """
    t0 = __import__("time").time()
    try:
        from edu_agent.generate import ask

        rec = ask(state.get("text", ""))
        logsetup.latency(log, "graph_coach_done", t0,
                         coverage=rec.coverage, confidence=f"{rec.confidence:.2f}")
        return {"output_md": rec.answer_md, "error": "", "mode": "coach"}
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        logsetup.event(log, "graph_coach_error", error=msg[:200])
        return {"output_md": f"⚠️ Agent A（课本教练）不可用或出错：{msg}",
                "error": msg, "mode": "coach"}


def _plan_node(state: State) -> dict:
    """Agent B 教案 Agent 节点（独立）。lazy import + 异常隔离，输出教案 markdown。

    goal 拼接逻辑：若 state 带 coach_summary（A 的学情），自动追加"学生前情"段落，
    让教案回应学生刚问过的问题（P1 协作）；无 coach_summary 时 goal 原样传给 B。
    """
    t0 = __import__("time").time()
    try:
        from edu_agent import planner

        kp = state.get("knowledge_point") or state.get("text", "")
        goal_parts: list[str] = []
        if state.get("goal"):
            goal_parts.append(state["goal"])
        if state.get("coach_summary"):
            goal_parts.append(
                "【学生前情（Agent A 刚答疑过，请在设计教案时呼应）】"
                + state["coach_summary"])
        goal = "\n".join(goal_parts)
        rec = planner.make_plan(kp, goal, template=state.get("template_id"))
        logsetup.event(log, "graph_plan_done", title=rec.title[:60],
                       steps=len(rec.flow_steps))
        return {"output_md": planner.to_markdown(rec), "error": "", "mode": "plan"}
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        logsetup.event(log, "graph_plan_error", error=msg[:200])
        return {"output_md": f"⚠️ Agent B（教案 Agent）不可用或出错：{msg}",
                "error": msg, "mode": "plan"}


# 编译图缓存（单例：图结构不变，重复编译浪费）
_graph = None


def _get_graph():
    """构建并缓存编译后的 StateGraph（Router：START -> route -> coach|plan -> END）。"""
    global _graph
    if _graph is None:
        builder = StateGraph(State)
        builder.add_node("coach", _coach_node)
        builder.add_node("plan", _plan_node)
        builder.add_conditional_edges(START, _route,
                                      {"coach": "coach", "plan": "plan"})
        builder.add_edge("coach", END)
        builder.add_edge("plan", END)
        _graph = builder.compile()
    return _graph


def ask(text: str) -> dict:
    """自动路由入口：普通提问 -> A（课本教练）；教案/备课话术 -> B（教案 Agent）。

    参数:
      text: str  学生/老师原始输入（必填）。含教案意图词则走 B，否则走 A。
    返回:
      dict（State 输出组）：{"output_md": ..., "error": "", "mode": "coach"|"plan"}
    """
    return _get_graph().invoke({"text": text})


def ask_coach(text: str) -> dict:
    """强制走 Agent A（答疑）。用于 UI「答疑」Tab，绕过关键词路由。

    参数:
      text: str  学生问题（必填）。
    返回:
      dict：A 的 answer_md + 引用信息在 output_md；mode="coach"。
    """
    return _get_graph().invoke({"text": text, "mode": "coach"})


def ask_plan(knowledge_point: str, goal: str = "", template_id: str = "",
             coach_summary: str = "") -> dict:
    """强制走 Agent B（教案），可携带 Agent A 的学情摘要（P1 协作）。

    参数:
      knowledge_point: str  知识点（必填），如 "函数的单调性"。
      goal: str             教学问题/目标（可选），如 "重点班 45 分钟，注意与图象结合"。
      template_id: str      教案模板 id（可选）；空 = 用当前模板（planner 默认）。
      coach_summary: str    学生前情（可选）= Agent A 刚答过的摘要；非空时自动拼进
                            B 的 goal，让教案呼应学生刚问的问题；B 不依赖它。
    返回:
      dict：教案 markdown 在 output_md；mode="plan"。
    """
    return _get_graph().invoke({
        "knowledge_point": knowledge_point,
        "goal": goal,
        "template_id": template_id or "",
        "coach_summary": coach_summary,
        "mode": "plan",
    })


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) >= 2 and sys.argv[1] == "--plan":
        kp = sys.argv[2] if len(sys.argv) > 2 else "函数的单调性"
        goal = sys.argv[3] if len(sys.argv) > 3 else ""
        out = ask_plan(kp, goal)
    else:
        text = sys.argv[1] if len(sys.argv) > 1 else "怎么判断函数单调性？"
        out = ask(text)
    print(out.get("mode", "?"), "->", out.get("error") or "OK")
    print("-" * 60)
    print(out.get("output_md", "")[:1500])
