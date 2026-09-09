"""工程补强(2026-09-07)：会话管理 —— 多轮追问。

目标（缺失项 #2 -> 影响「无法多轮追问」）：
  - Conversation：有界轮次(默认 6)，记录 user/assistant 轮，可序列化（gr.State/落盘）；
  - is_follow_up / resolve_query：识别"它/那/为什么/再举一例"等指代追问，
    把上一问的话题并入本次检索词，否则"那它和指数函数什么关系"整句检索必失败；
  - history_block()：生成给 LLM 的"对话上文"文本块（只作衔接理解，不作事实来源）。

契约：不侵入 AnswerRecord（generate 侧签名保持向后兼容，新增 ask_turn）。
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Turn:
    role: str                 # user | assistant
    text: str                 # 原问题 / 答案 markdown
    meta: dict = field(default_factory=dict)   # 答案侧：coverage/confidence/pages

    def to_dict(self) -> dict:
        return {"role": self.role, "text": self.text, "meta": self.meta}

    @classmethod
    def from_dict(cls, d: dict) -> "Turn":
        return cls(role=d.get("role", "user"), text=d.get("text", ""), meta=d.get("meta", {}))


# 追问特征：短问 + 指代/承接词（无独立主题）
_FOLLOW_WORDS = (
    "它", "这个", "那个", "这题", "那题", "还有", "再", "那", "那么", "为什么",
    "怎么判断", "所以", "然后", "举例", "例如", "请再", "继续", "接着说",
    "什么意思", "是什么", "关系呢", "区别", "比较", "呢",
)
_FOLLOW_RE = re.compile(r"^(它|这个|那个|这|那|还|再|然后|所以|为什么|怎么|举例|请|继续|接着|嗯|对|好)")

_QUESTION_TAIL = re.compile(r"[？?。！!，,\s]*$")
_QUESTION_HEAD = re.compile(r"^(那|那么|所以|然后|还|再|请|帮我|它的|这个|那个)")


def _topic_of(q: str) -> str:
    """从问题里抽"话题主干"：去掉追问头尾与疑问词，供并入检索。"""
    t = _QUESTION_HEAD.sub("", q.strip())
    t = _QUESTION_TAIL.sub("", t)
    for w in ("怎么判断", "怎么解", "是什么", "为什么", "如何", "关系", "区别", "定义", "性质", "怎么求", "怎么做"):
        idx = t.find(w)
        if idx > 0:
            t = t[:idx]
    return t.strip()


class Conversation:
    """一轮有界会话。纯数据 + 规则，无 IO；可 dump/load 便于 UI 状态与落盘。"""

    def __init__(self, turns: list[Turn] | None = None, max_turns: int = 6,
                 session_id: str | None = None):
        self.turns: list[Turn] = turns if turns is not None else []
        self.max_turns = max_turns
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.created_at = time.time()

    # ---- 基本操作 ----
    def add(self, role: str, text: str, meta: dict | None = None) -> None:
        self.turns.append(Turn(role=role, text=text, meta=meta or {}))
        if len(self.turns) > self.max_turns * 2:
            self.turns = self.turns[-(self.max_turns * 2):]

    def last_user_text(self) -> str:
        for t in reversed(self.turns):
            if t.role == "user":
                return t.text
        return ""

    def is_empty(self) -> bool:
        return not self.turns

    # ---- 追问判定与检索词解析 ----
    def is_follow_up(self, question: str) -> bool:
        q = question.strip()
        if not q:
            return False
        if _FOLLOW_RE.match(q):
            return True
        # 短问无教材术语 -> 视为承接上一问
        has_topic = re.search(r"([一二三四五六七八九十]?\d(?:[.．]\d){0,2}|集合|函数|单调|奇|偶|指数|对数|幂|不等式|三角|正弦|余弦|正切|弧度|零点|图象|图像|定义|性质|概念)", q)
        if len(q) <= 12 and not has_topic:
            return True
        return False

    def resolve_query(self, question: str) -> tuple[str, bool]:
        """返回 (用于检索的 query, 是否追问)。追问则把上一问话题并入。"""
        q = question.strip()
        if self.is_follow_up(q):
            prev = _topic_of(self.last_user_text())
            if prev and prev not in q:
                return f"{prev} {q}", True
            return f"{prev or ''} {q}".strip(), True
        return q, False

    # ---- 供 LLM 的对话上文 ----
    def history_block(self, max_turns: int = 4) -> str:
        """把最近几轮压缩成衔接文本；空会话返回空串。"""
        lines: list[str] = []
        for t in self.turns[-(max_turns * 2):]:
            if t.role == "user":
                lines.append(f"- 学生上一问：{t.text[:120]}")
            else:
                meta = t.meta
                pages = ""
                ps = meta.get("pages") if isinstance(meta.get("pages"), list) else []
                if ps:
                    pages = "（引 p" + "、p".join(str(p) for p in ps[:4]) + "）"
                first_line = t.text.split("\n")[0][:100] if t.text else ""
                lines.append(f"- 教练上一答要点：{first_line}{pages}")
        if not lines:
            return ""
        return "\n".join(lines)

    # ---- 序列化（gr.State / 落盘 / 传输） ----
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "max_turns": self.max_turns,
            "turns": [t.to_dict() for t in self.turns],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Conversation":
        conv = cls(
            turns=[Turn.from_dict(x) for x in d.get("turns", [])],
            max_turns=d.get("max_turns", 6),
            session_id=d.get("session_id"),
        )
        return conv
