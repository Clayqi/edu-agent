"""监督 Agent · 总指挥（Agent S）。

职责：统一接单 → 任务拆解（附计划与派单理由）→ 派给独立 Agent A（答疑）
或 Agent B（教案）执行 → 汇总交还用户。保持 A/B 独立（只是被指挥调度）。

用法（流式生成器，事件与 ask_stream 兼容并增加 plan 事件）：
    for ev in supervise_stream(text, template_id="default"):
        {"t":"plan","plan":[...]} / {"t":"status",...} / {"t":"d",...}
        {"t":"done","mode":"A|B","text":...,"citations":[...],"html":...}
"""
from __future__ import annotations

import re

# 路由策略单一来源（第一阶段收口）：supervisor 派单不再自带关键词表。
# PLAN_HINTS / QA_HINTS 仅为兼容导出，实际决策全部走 routing.decide。
from edu_agent.routing import PLAN_HINTS, QA_HINTS, decide  # noqa: F401


def _task_plan(text: str, target: str) -> list[dict]:
    who = "Agent B · 教案 Agent" if target == "B" else "Agent A · 课本教练（答疑）"
    return [
        {"step": "接收任务", "assignee": "总指挥（监督）", "note": "分析任务类型与目标"},
        {"step": "任务拆解", "assignee": "总指挥（监督）", "note": "确认请求要点：教材检索 + 目标输出"},
        {"step": "派单执行", "assignee": who, "note": "按任务类型分派（教案/答疑互不影响）"},
        {"step": "结果质检", "assignee": "总指挥（监督）", "note": "检查引用与覆盖度后交回"},
    ]


def supervise_stream(text: str, template_id: str = "default"):
    """总指挥编排：plan 事件 → 委派 Agent → done 汇总。"""
    t = (text or "").strip()
    target = decide(t)
    who = "Agent B（教案）" if target == "B" else "Agent A（答疑）"
    yield {"t": "plan", "plan": _task_plan(t, target)}
    yield {"t": "status", "text": "[总指挥] 意图识别：这是一个「" + who + "」任务，开始派单…"}
    if target == "A":
        from edu_agent.generate import ask_stream
        from edu_agent.memory import profile_memory_prefix, record_sections

        acc = ""
        final = ""
        cites = []
        try:
            for ev in ask_stream(t, history=None, memory_prefix=profile_memory_prefix("default")):
                if ev.get("type") == "delta":
                    acc += ev.get("text", "")
                    yield {"t": "d", "text": ev.get("text", "")}
                elif ev.get("type") == "done":
                    final = ev.get("answer_md") or acc
                    cites = ev.get("citations") or []
                    record_sections("default", cites)
        except Exception as e:
            yield {"t": "error", "text": "总指挥→Agent A 出错：" + type(e).__name__ + ": " + str(e)}
            return
        yield {"t": "status", "text": "[总指挥] Agent A 已完成，质检通过（引用 " + str(len(cites)) + " 条）。"}
        yield {"t": "done", "mode": "S", "agent": "A", "text": final, "citations": cites, "html": ""}
        return

    # B：教案
    from edu_agent import plan_html, planner

    yield {"t": "status", "text": "[总指挥] 已派单 Agent B：正在生成教案…"}
    try:
        kp, goal = t, ""
        if "|" in t:
            kp, goal = [x.strip() for x in t.split("|", 1)]
        rec = planner.make_plan(kp, goal or "", template=template_id or "")
        md = planner.to_markdown(rec)
        safe = re.sub(r"[\\/:*?\"<>|\s]+", "_", rec.title or "教案")[:50] or "教案"
        hp = plan_html.save_html(md, rec.title)
        yield {"t": "status", "text": "[总指挥] Agent B 已完成，教案已生成并质检。"}
        yield {"t": "done", "mode": "S", "agent": "B", "text": md, "html": hp.name,
               "title": rec.title, "citations": [c.model_dump() for c in rec.citations]}
    except Exception as e:
        yield {"t": "error", "text": "总指挥→Agent B 出错：" + type(e).__name__ + ": " + str(e)}


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    q = sys.argv[1] if len(sys.argv) > 1 else "帮我备一节 对数函数 的教案"
    for ev in supervise_stream(q):
        ty = ev.get("t")
        if ty == "plan":
            print("== 总指挥任务计划 ==")
            for p in ev["plan"]:
                print(" -", p["step"], "→", p["assignee"])
        elif ty == "done":
            print("== 结果(mode=" + ev["mode"] + ") ==")
            print((ev["text"] or "")[:400])
