"""S7 实现（工程补强 2026-09-07 增强）：检索 -> 预处理 -> 生成 -> AnswerRecord。

    ask(question) -> AnswerRecord                    # 向后兼容：单轮主入口
    ask_turn(question, conversation) -> (AnswerRecord, Conversation)  # 多轮追问
        answer_md    答案（论断带 [n] 引用）
        citations[]  引用（坐标 + 片段原文摘录）
        coverage     high/medium/low（检索覆盖）
        confidence   0~1
越界/低置信降级见 grounded.degrade（S8）。

工程补强（2026-09-07，缺失项补齐）：
  - 查询预处理 preprocess：章/节/页/题号 坐标识别 + 术语归一，结构问法不再系统性失败；
  - 重试机制：LLM 网络/API/解析失败统一重试（默认 3 次、升温），最后才降级；
  - 会话管理 session：多轮追问指代消解 + 上文衔接（不影响单轮契约）；
  - 日志 logsetup：请求级 request_id 与结构化事件，问题可复现。
"""
from __future__ import annotations

import json
import re
import time

from pydantic import BaseModel, Field

from edu_agent import logsetup, math_verify, preprocess, prompts, session
from edu_agent.config import get_chat_llm
from edu_agent.retrieve import retrieve

log = logsetup.get_logger("generate")


class Citation(BaseModel):
    index: int = Field(description="对应检索片段的 [编号]")
    chunk_id: str = ""
    chapter: str = ""
    section: str = ""
    heading: str = ""
    page: int | None = None
    quote: str = ""


_MATH_PLAIN = {
    "\\subseteq": "⊆", "\\supseteq": "⊇", "\\subset": "⊂", "\\in": "∈",
    "\\notin": "∉", "\\cup": "∪", "\\cap": "∩", "\\emptyset": "∅",
    "\\ne": "≠", "\\leq": "≤", "\\geq": "≥", "\\cdot": "·",
    "\\log": "log", "\\ln": "ln", "\\sin": "sin", "\\cos": "cos",
    "\\tan": "tan", "\\pi": "π", "\\infty": "∞", "\\sqrt": "√",
    "\\frac": "/", "\\times": "×", "\\pm": "±", "\\alpha": "α",
    "\\beta": "β", "\\theta": "θ", "\\omega": "ω", "\\lambda": "λ",
    "\\Delta": "Δ", "\\mathbb": "", "\\mathrm": "",
}


def plainify_math(s: str) -> str:
    """把残留的 LaTeX 转成纯文本/Unicode，保证任何环境都不出现乱码。"""
    if not s:
        return s
    s = re.sub(r"\$\$|\$", "", s)          # 去掉 $ 包裹
    # 先处理 \frac{a}{b} -> (a)/(b)，保住分组可读
    s = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"(\1)/(\2)", s)
    for k, v in _MATH_PLAIN.items():       # 常用命令 -> Unicode
        s = s.replace(k, v)
    s = s.replace("\\", "")                # 清剩余反斜杠
    s = s.replace("{", "").replace("}", "")
    return s


class AnswerRecord(BaseModel):
    answer_md: str
    citations: list[Citation] = Field(default_factory=list)
    coverage: str = "medium"          # high|medium|low
    confidence: float = 0.0


def classify(question: str) -> str:
    """题型分类（轻量启发式）。委托 preprocess，保持旧入口兼容。"""
    return preprocess.classify_question(question)


def _kind_filter_for(qtype: str) -> list[str] | None:
    return preprocess.kind_filter_for(qtype)


# ---------- 检索 ----------
def _retrieve_with_fallback(rq: str, original: str, qtype: str, top_k: int,
                            proc: preprocess.Processed):
    """坐标/章节过滤优先，命中失败逐级回退（章节过滤 -> 全文 -> 原文检索）。"""
    kinds = _kind_filter_for(qtype)
    # hybrid=False：dense-only 实测 0.25s vs hybrid 4.0s，命中质量相同（09-07 单例对比）；
    # 编号/术语问法已由 preprocess 坐标解析 + 章级 metadata 过滤兜底，bm25 保留可手动开
    kw: dict = {"top_k": top_k, "hybrid": False}
    if kinds:
        kw["kinds"] = kinds
    ch = proc.ref.chapter if proc.ref else None
    if ch:
        try:
            hits = retrieve(rq, chapter=ch, **kw)
        except Exception:
            hits = []
        if hits:
            logsetup.event(log, "retrieve", scope="chapter:" + ch, hits=len(hits))
            return hits
    hits = retrieve(rq, **kw)
    if hits:
        logsetup.event(log, "retrieve", scope="full", hits=len(hits))
        return hits
    if rq != original:
        hits = retrieve(original, **kw)
        if hits:
            logsetup.event(log, "retrieve", scope="original", hits=len(hits))
            return hits
    logsetup.event(log, "retrieve", scope="none", hits=0)
    return []


# ---------- Prompt 组装 ----------
def _to_conversation(history):
    """把各种 history 形态归一成 Conversation。"""
    if history is None:
        return session.Conversation()
    if isinstance(history, session.Conversation):
        return history
    if isinstance(history, dict):
        return session.Conversation.from_dict(history)
    if isinstance(history, list):
        return session.Conversation(turns=[session.Turn.from_dict(t) for t in history])
    return session.Conversation()


def build_messages(question: str, hits, history=None, hints=None) -> list[dict]:
    """组装消息。history: Conversation 或 turn 列表/dict；hints: 结构化坐标提示。"""
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
                text=h.text[:400],
            )
        )
    conv = _to_conversation(history)
    blocks = ["【检索到的教材片段】", "\n\n".join(snips)]
    hb = conv.history_block()
    if hb:
        blocks.append("【对话上文（仅作衔接理解，不是事实来源）】\n" + hb)
    if hints:
        blocks.append("【提示】\n" + "\n".join("- " + h for h in hints))
    blocks.append("【学生问题】" + question + "\n\n" + prompts.JSON_INSTRUCTION)
    if hb:
        blocks.append(prompts.HISTORY_INSTRUCTION)
    user = "\n\n".join(blocks)
    return [{"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": user}]


# 代码块围栏（避免在源码里出现裸反引号，用 chr(96) 组装）
_FENCE = chr(96) * 3


def _parse_answer(text: str) -> AnswerRecord:
    """宽松解析 LLM 输出（容忍 json 代码块包裹）。"""
    t = text.strip()
    t = re.sub(r"^\s*" + _FENCE + r"(?:json)?\s*", "", t)
    t = re.sub(_FENCE + r"\s*$", "", t)
    obj = json.loads(t)
    if not isinstance(obj, dict):
        raise ValueError("LLM 输出不是 JSON 对象")
    for c in obj.get("citations", []):
        c.setdefault("index", 0)
    rec = AnswerRecord(**obj)
    for c in rec.citations:
        c.quote = c.quote[:200]
    return rec


# ---------- 重试机制（工程补强） ----------
_TEMP_CURVE = (0.0, 0.2, 0.3)


def _generate_once(messages: list[dict], temperature: float) -> AnswerRecord:
    llm = get_chat_llm(temperature=temperature, timeout=90)
    raw = llm.invoke(messages).content or ""
    return _parse_answer(raw)


def _generate_with_retry(messages: list[dict], attempts: int = 3,
                         retry_delay: float = 0.2) -> AnswerRecord | None:
    """统一重试：网络/API/空输出/解析失败全部重试，逐次升温+小退避。

    全部失败返回 None（由调用方降级 parse_error）；日志记录每次原因。
    """
    last_err: Exception | None = None
    for i in range(1, attempts + 1):
        temp = _TEMP_CURVE[min(i - 1, len(_TEMP_CURVE) - 1)]
        t0 = time.time()
        try:
            rec = _generate_once(messages, temperature=temp)
            logsetup.event(log, "llm_ok", attempt=i, temperature=temp,
                           ms_ms=f"{(time.time() - t0) * 1000:.0f}")
            return rec
        except Exception as e:  # noqa: BLE001 —— 重试覆盖所有偶发失败
            last_err = e
            logsetup.event(log, "llm_retry", attempt=i, temperature=temp,
                           error=f"{type(e).__name__}: {str(e)[:140]}",
                           ms_ms=f"{(time.time() - t0) * 1000:.0f}")
            if i < attempts and retry_delay > 0:
                time.sleep(retry_delay)
    logsetup.event(log, "llm_gave_up", attempts=attempts,
                   last_error=f"{type(last_err).__name__}: {str(last_err)[:140]}")
    return None


# ---------- 引用规整与防线（沿 S8 逻辑） ----------
def _regularize(rec: AnswerRecord, hits, question: str = "") -> AnswerRecord:
    """规整 citations/编号 -> 校验 -> 置信度；校验不过/过低置信返回降级记录。

    question: 原学生问题，降级记录用它回显"（你的问题：…）"尾巴
    （2026-09-07 修复：曾传空串导致降级文案丢失问题回显，行为回退）。
    """
    from edu_agent.grounded import degrade, validate

    allowed = {i + 1: h for i, h in enumerate(hits)}
    used = set(int(m) for m in re.findall(r"\[(\d+)\]", rec.answer_md))
    rec.citations = [c for c in rec.citations if c.index in allowed and c.index in used]
    ok_idx = {c.index for c in rec.citations}
    rec.answer_md = re.sub(
        r"\[(\d+)\]",
        lambda m: m.group(0) if int(m.group(1)) in ok_idx else "",
        rec.answer_md,
    )
    for c in rec.citations:
        h = allowed.get(c.index)
        if h:
            md = h.metadata
            c.chunk_id = md.get("chunk_id", "")
            c.chapter = md.get("chapter", "")
            c.section = md.get("section", "") or ""
            c.heading = md.get("heading", "") or ""
            c.page = md.get("page")
            c.quote = c.quote or h.text[:120]
    best = hits[0].score if hits else float("inf")
    rec.coverage = "high" if (len(hits) >= 3 and best < 0.75) else ("medium" if hits else "low")
    rec.confidence = max(0.0, min(1.0, 1.0 - best / 2.0)) if hits else 0.0
    rec.answer_md = plainify_math(rec.answer_md)

    issues = validate(rec)
    if issues:
        return degrade(question, reason="引用校验未通过: " + "; ".join(issues[:3]),
                       kind="parse_error")
    if not rec.citations or rec.coverage == "low" or best > 1.05:
        return degrade(question, reason="检索置信过低或无有效引用，不硬编",
                       kind="low_confidence")
    return rec


# ---------- 主入口 ----------
def ask(question: str, top_k: int = 3, attempts: int = 3, retry_delay: float = 0.2,
        retrieval_query: str | None = None, history=None) -> AnswerRecord:
    """主问答入口（向后兼容单轮）：预处理 -> 检索 -> 重试生成 -> 规整。

    retrieval_query: 多轮追问时由会话解析出的检索词（prompt 仍用原问题）。
    history: Conversation / turn 列表 / dict（多轮衔接；None = 单轮）。
    """
    from edu_agent.grounded import degrade

    proc = preprocess.preprocess(question)
    rq = (retrieval_query or "").strip() or proc.query or question
    t0 = time.time()
    logsetup.event(log, "ask_start", question_len=len(question), qtype=proc.qtype)

    hits = _retrieve_with_fallback(rq, question, proc.qtype, top_k, proc)
    if not hits:
        logsetup.latency(log, "ask_degraded", t0, kind="empty")
        return degrade(question, reason="检索为空（已含章节回退）", kind="empty")

    messages = build_messages(question, hits, history=history, hints=proc.hints)
    rec = _generate_with_retry(messages, attempts=attempts, retry_delay=retry_delay)
    if rec is None:
        logsetup.latency(log, "ask_degraded", t0, kind="parse_error")
        return degrade(question, reason="生成解析失败（已重试）", kind="parse_error")

    final = _regularize(rec, hits, question)
    final.answer_md = math_verify.attach_verify(question, final.answer_md)
    logsetup.latency(log, "ask_done", t0, coverage=final.coverage,
                     confidence=f"{final.confidence:.2f}", citations=len(final.citations))
    return final


def ask_turn(question: str, conversation=None, attempts: int = 3,
             retry_delay: float = 0.2, top_k: int = 3) -> tuple:
    """多轮追问入口：解析指代 + 调用 ask + 记录轮次。返回 (AnswerRecord, Conversation)。

    conversation: Conversation 实例（推荐，含历史）；None 时新建。
    """
    conv = _to_conversation(conversation)
    rq, is_fu = conv.resolve_query(question)
    if is_fu:
        logsetup.event(log, "turn_followup", query=rq[:80])
    rec = ask(question, top_k=top_k, attempts=attempts, retry_delay=retry_delay,
              retrieval_query=rq, history=conv)
    conv.add("user", question)
    pages = sorted({c.page for c in rec.citations if c.page})
    conv.add("assistant", rec.answer_md, meta={
        "coverage": rec.coverage,
        "confidence": round(rec.confidence, 2),
        "pages": pages,
        "is_follow_up": is_fu,
    })
    return rec, conv



_STREAM_MARK = "===JSON==="


def _summarize_history(history, max_chars: int = 600) -> str:
    """把最近几轮对话压成可注入的前情（只用于理解指代）。"""
    if not history:
        return ""
    lines = []
    for m in list(history)[-4:]:
        who = "学生" if m.get("role") == "user" else "教练"
        t = (m.get("content") or "").replace("\n", " ").strip()
        lines.append(who + "：" + t[:160])
    s = "\n".join(lines)
    return s[:max_chars]


def ask_stream(question: str, history=None, memory_prefix: str = "",
               top_k: int = 3, snippet_len: int = 400,
               source: str | None = None, persist_dir=None, collection: str | None = None):
    """流式问答生成器。

    依次 yield：
      {"type":"status","text":...}
      {"type":"delta","text":...}          # 正文增量
      {"type":"done","answer_md":...,"citations":[...],"coverage":...,"confidence":...}
    """
    from edu_agent.grounded import degrade

    kk = None if source else _kind_filter_for(classify(question))
    hits = retrieve(question, kinds=kk, top_k=top_k, hybrid=False,
                    source=source, persist_dir=persist_dir, collection=collection)
    if not hits:
        yield {"type": "status", "text": "检索无结果"}
        rec = degrade(question, reason="检索为空")
        yield {"type": "done", "answer_md": rec.answer_md, "citations": [], "coverage": "low", "confidence": 0.0}
        return

    blocks = []
    if memory_prefix:
        blocks.append("【长期记忆】" + memory_prefix)
    if history:
        blocks.append("【最近对话（仅用于理解指代）】\n" + _summarize_history(history))
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
                text=h.text[:snippet_len],
            )
        )
    blocks.append("【检索到的教材片段】\n" + "\n\n".join(snips))
    blocks.append("【学生问题】" + question)
    user = "\n\n".join(blocks) + "\n\n" + prompts.STREAM_INSTR
    messages = [{"role": "system", "content": prompts.SYSTEM_PROMPT}, {"role": "user", "content": user}]

    yield {"type": "status", "text": "正在检索教材并作答…"}
    llm = get_chat_llm(max_tokens=1000, timeout=90)
    raw = ""
    emitted = 0
    text_on = True
    # ===JSON=== 可能被流式 chunk 边界拆开（如 "===JS"+"ON==="），
    # 不能只等完整标记：尾部若命中标记前缀，先扣住等下一 chunk 补齐，
    # 否则半截标记会泄漏成正文（2026-09-10 修复）。
    _mark_prefixes = sorted((_STREAM_MARK[:i] for i in range(1, len(_STREAM_MARK) + 1)),
                            key=len, reverse=True)
    for chunk in llm.stream(messages):
        raw += chunk.content or ""
        if text_on:
            if _STREAM_MARK in raw:
                seg = raw[: raw.find(_STREAM_MARK)]
                text_on = False
            else:
                hold = 0
                for p in _mark_prefixes:
                    if raw.endswith(p):
                        hold = len(p)
                        break
                seg = raw if hold == 0 else raw[:-hold]
            if len(seg) > emitted:
                yield {"type": "delta", "text": seg[emitted:]}
                emitted = len(seg)

    # 冲刷流结束时仍被扣住的尾部（正文恰以标记前缀结尾等边界），避免丢字
    if text_on and emitted < len(raw):
        yield {"type": "delta", "text": raw[emitted:]}

    if _STREAM_MARK in raw:
        text_part, json_part = raw.split(_STREAM_MARK, 1)
    else:
        text_part, json_part = raw, ""
    answer = plainify_math(text_part).strip()
    citations = []
    coverage = "medium"
    confidence = 0.5
    if json_part.strip():
        try:
            obj = json.loads(json_part.strip())
            coverage = obj.get("coverage", "medium")
            confidence = float(obj.get("confidence", 0.5))
            allowed = {i + 1: h for i, h in enumerate(hits)}
            for c in obj.get("citations", []):
                idx = int(c.get("index", 0))
                h = allowed.get(idx)
                if not h:
                    continue
                md = h.metadata
                citations.append({
                    "index": idx,
                    "chapter": md.get("chapter", ""),
                    "section": md.get("section", "") or "",
                    "heading": md.get("heading", "") or "",
                    "page": md.get("page"),
                    "source": md.get("source", ""),
                    "book": md.get("book", ""),
                    "quote": (c.get("quote") or h.text[:80])[:80],
                })
        except Exception:
            citations = []
    if not citations and "未收录" in answer:
        coverage = "low"
        confidence = 0.0
    answer = math_verify.attach_verify(question, answer)
    yield {"type": "done", "answer_md": answer, "citations": citations,
           "coverage": coverage, "confidence": min(max(confidence, 0.0), 1.0)}


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    logsetup.setup(level="INFO")
    args = sys.argv[1:]
    if args and args[0] == "--chat":
        conv = session.Conversation()
        print("课本教练多轮模式：输入问题（空行退出）")
        while True:
            try:
                q = input("你 > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not q:
                break
            rec, conv = ask_turn(q, conversation=conv)
            print("教练 >")
            print(rec.answer_md)
            print("-" * 60)
    else:
        q = args[0] if args else "函数的单调性怎么判断？"
        rec = ask(q)
        print("=" * 60)
        print(rec.answer_md)
        print("=" * 60)
        print(f"coverage={rec.coverage} confidence={rec.confidence:.2f}")
        for c in rec.citations:
            print(f"  [{c.index}] {c.chapter} {c.section} {c.heading} p{c.page} | {c.quote[:60]}")
