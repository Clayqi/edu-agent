"""routing.py —— 意图路由的单一事实来源（第一阶段收口）。

背景（收口前的问题）：supervisor.py、graph.py、web_server.py / api.py 各自维护
一份"教案类/答疑类"关键词表，已出现互相漂移（如 supervisor 独有的"上课/导学"、
graph 独有的"课件/教案模板"）。同一个句子在 S 路径和 auto 路径可能路由到不同 Agent。

收口后：只在本文件维护一份 PLAN_HINTS / QA_HINTS 与 decide()，所有消费方
（supervisor 派单、web 网关 auto、graph Router）一律调用本文件，不再自带词表。
行为约定（与旧规则一致）：
  - 显式 mode 优先（"A"/"B" 或 "coach"/"plan"）；
  - 无显式 mode 时：命中任一教案类词 → B（教案 Agent）；否则 → A（课本教练）。
"""
from __future__ import annotations

# 教案意图词（命中任一即 B）。刻意小而准；可在此集中增删。
PLAN_HINTS = (
    "教案", "备课", "教学设计", "怎么讲", "怎么教", "如何教", "如何讲",
    "教学目标", "板书设计", "教学环节", "课件", "课堂设计", "教案模板",
    "上课", "导学",
)

# 答疑意图词（A 侧信号；decide 默认即 A，此表供分类/统计与未来策略使用）
QA_HINTS = (
    "是什么", "为什么", "怎么解", "怎么判断", "区别", "证明",
    "求", "等于", "练习", "题", "帮我算", "讲解",
)

# 规范化代号：任意形态 → "A" | "B"
_CODE_MAP = {
    "A": "A", "coach": "A", "答疑": "A",
    "B": "B", "plan": "B", "教案": "B",
}


def want_plan(text: str) -> bool:
    """文本是否含教案类意图词。"""
    t = text or ""
    return any(h in t for h in PLAN_HINTS)


def decide(text: str, mode: str | None = None) -> str:
    """统一派单决策：返回 "A"（课本教练）或 "B"（教案 Agent）。

    mode 接受 A/B、coach/plan、auto/空（=None）。显式 A/B 优先于关键词。
    """
    m = _CODE_MAP.get((mode or "").strip())
    if m:
        return m
    return "B" if want_plan(text) else "A"


def label(mode: str) -> str:
    """把内部代号转成对外标签（旧 web 文案兼容）。"""
    return "coach" if decide("", mode=mode) == "A" else "plan"
