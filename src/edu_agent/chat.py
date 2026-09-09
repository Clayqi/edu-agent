"""Agent A · 多轮答疑壳（官方 tool wrapper + checkpointer 模式）。

外层：LangGraph create_react_agent + 会话记忆（checkpointer），
把现有无状态 ask() 包成工具 ask_textbook：Agent 必须先检索教材再回答，
引用仍来自当轮检索（防幻觉不变），历史仅用于理解追问语境。

独立性：本模块只服务 Agent A，不触碰 Agent B/planner。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from edu_agent.config import get_chat_llm

SYSTEM = """你是课本教练（Agent A），面对学生多轮追问。
规则：
1. 每次回答前，必须调用 ask_textbook 工具检索教材并作答；不得凭记忆自答。
2. 学生可能说“刚才/这题/它/那……”等指代——结合本会话历史理解指代，把完整问题传给工具（必要时代入上一轮语境）。
3. 只依据工具返回作答（含页码引用 [n]）；越界/未收录由工具判定并诚实说明。
4. 语气：中学老师，讲清是什么为什么怎么用。"""


@tool
def ask_textbook(question: str) -> str:
    """检索本册教材并按教材作答（含页码引用）。多轮中若问题含指代，请先补全为完整问题。"""
    from edu_agent.generate import ask

    try:
        rec = ask(question)
    except Exception as e:
        return "检索/生成失败：" + type(e).__name__ + ": " + str(e)
    parts = [rec.answer_md]
    if rec.citations:
        parts.append("【引用】")
        for c in rec.citations[:4]:
            loc = (c.chapter + " " + (c.section or "") + " " + (c.heading or "")).strip()
            parts.append("[" + str(c.index) + "] " + loc + " p" + str(c.page))
    if rec.coverage == "low":
        parts.append("（本册教材未收录，按诚实降级处理）")
    return "\n".join(parts)


_checkpointer = InMemorySaver()
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = create_react_agent(model=get_chat_llm(), tools=[ask_textbook], prompt=SYSTEM)
    return _agent


def ask_chat(user_text: str, thread_id: str = "default") -> dict:
    """多轮入口：同一 thread_id 延续会话（checkpointer 记忆）。"""
    from edu_agent.generate import plainify_math

    config = {"configurable": {"thread_id": thread_id}}
    result = _get_agent().invoke({"messages": [HumanMessage(content=user_text)]}, config=config)
    msgs = result.get("messages", [])
    last = next((m for m in reversed(msgs) if isinstance(m, AIMessage) and m.content), None)
    answer = plainify_math(last.content) if last else ""
    return {"thread_id": thread_id, "answer": answer}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("q", help="学生问题")
    ap.add_argument("--thread", default="demo1")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    out = ask_chat(args.q, thread_id=args.thread)
    print(out["answer"])
