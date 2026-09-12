# -*- coding: utf-8 -*-
"""会话里的教案内容 -> 教案中心模板：解析 / 匹配 / 填充。

链路：Agent B 在会话里生成的教案（Markdown，形如 `# 课题` + `**板块名**` + 列表 + `### 环节（约 X 分钟）`）
      -> `parse_plan_markdown()` 拆成「板块 + 内容项」
      -> `match_sections()` 与模板板块做标题匹配（归一化 + 别名 + 相似度 + 贪心分配）
      -> `fill_template()` 按模板板块的结构填充（表格板块填成行、其余填段落），
         模板的**板块顺序/标题/格式**全部保留，未被匹配到的内容追加为新区块，之后可在教案中心继续编辑。
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

from edu_agent import template_rich as tr

# 会话消息里 Agent 的标签前缀（`_tag()` 生成，且与正文之间可能没有换行）
_TAG_RE = re.compile(r"^\s*\*\*【Agent\s*[AB]?[^*]*】\*\*\s*")
_H_RE = re.compile(r"^\s*(#{1,6})\s+(.*?)\s*$")
_BOLD_ONLY_RE = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")
_LI_RE = re.compile(r"^\s*(?:[-*+]|\d+\s*[.、)])\s+(.+?)\s*$")
_TBL_RE = re.compile(r"^\s*\|.*\|\s*$")
_BULLET_PREFIX = "· "
MATCH_THRESHOLD = 0.34
PREAMBLE_TITLE = "（开头）"      # 首个板块标题之前的内容归到这里（不是真板块，不追加）

# 模板板块常见叫法（同一组的标题视为匹配）
ALIASES: tuple[tuple[str, ...], ...] = (
    ("基本信息", "课题", "课时", "课型"),
    ("教材分析", "课标依据与教材分析", "课标依据", "教材与学情分析", "教材地位"),
    ("学情分析", "学情"),
    ("教学目标", "目标", "知识目标", "能力目标", "素养目标", "教学目的", "教学目标设计"),
    ("教学重点与难点", "重难点", "教学重点", "教学难点", "重点难点", "教学重点难点"),
    ("教学方法与准备", "教学方法", "教学准备", "教法学法", "教具准备", "教学媒体"),
    ("教学过程", "教学环节", "教学流程", "课堂过程", "教学过程设计", "环节设计"),
    ("易错点辨析", "易错点", "错因分析", "常见错误"),
    ("板书设计", "板书"),
    ("作业布置", "作业设计", "课后作业", "作业", "分层作业"),
    ("教学评价", "评价设计", "教学评价设计", "评价"),
    ("教学反思", "反思", "教学反思（预案）", "课后反思"),
    ("教材依据", "教材出处", "引用来源", "参考文献"),
)


# ---------- 解析 ----------
@dataclass
class Item:
    kind: str                 # sub | para | bullet | table
    title: str = ""
    text: str = ""
    bullets: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class Section:
    title: str
    level: int = 2            # 2 = **板块名** / ## ；3 = ###
    items: list[Item] = field(default_factory=list)


def _strip_tag(md: str) -> str:
    t = (md or "").lstrip("\ufeff").strip()
    return _TAG_RE.sub("", t, count=1).strip()


def _split_table_row(line: str) -> list[str]:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


def _is_sep_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells if c != "")


def parse_plan_markdown(md: str) -> dict:
    """教案 Markdown -> {title, sections:[Section], raw_len}。"""
    text = _strip_tag(md)
    lines = text.splitlines()
    title = ""
    sections: list[Section] = []
    cur: Section | None = None
    cur_sub: Item | None = None
    tbl: list[list[str]] = []

    def flush_table():
        nonlocal tbl
        if tbl and cur is not None:
            rows = [r for r in tbl if not _is_sep_row(r)]
            if rows:
                cur.items.append(Item(kind="table", rows=rows))
        tbl = []

    def ensure_sec(t: str, level: int = 2) -> Section:
        nonlocal cur, cur_sub
        flush_table()
        s = Section(title=t.strip() or "（未命名板块）", level=level)
        sections.append(s)
        cur, cur_sub = s, None
        return s

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        if _TBL_RE.match(line):
            tbl.append(_split_table_row(line))
            continue
        flush_table()

        m = _H_RE.match(line)
        if m:
            lvl, body = len(m.group(1)), m.group(2).strip()
            if lvl == 1 and not title:
                title = body
                continue
            if lvl <= 2:
                ensure_sec(body, 2)
            else:
                if cur is None:
                    ensure_sec(body, 3)
                else:
                    cur_sub = Item(kind="sub", title=body)
                    cur.items.append(cur_sub)
            continue

        m = _BOLD_ONLY_RE.match(line)
        if m:
            ensure_sec(m.group(1), 2)
            continue

        m = _LI_RE.match(line)
        if m:
            item_text = m.group(1).strip()
            if cur_sub is not None:
                cur_sub.bullets.append(item_text)
            elif cur is not None:
                cur.items.append(Item(kind="bullet", text=item_text))
            continue

        # 普通段落：若当前在小节里就进小节，否则进板块
        clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line.strip())
        if cur is None:
            ensure_sec(PREAMBLE_TITLE, 2)
        if cur_sub is not None:
            if cur_sub.text:
                cur_sub.text += "\n" + clean
            else:
                cur_sub.text = clean
        else:
            cur.items.append(Item(kind="para", text=clean))

    flush_table()
    # 去掉纯标题的空板块（生成物里偶发的 `**xxx**` 后面没内容）
    sections = [s for s in sections if s.items or s.level == 2]
    return {"title": title or "（未命名教案）", "sections": sections, "raw_len": len(text)}


# ---------- 匹配 ----------
_NUM_RE = re.compile(r"^[\s（(]*[一二三四五六七八九十0-9]{1,3}\s*[、.．)）]\s*")
_PAREN_RE = re.compile(r"[（(][^）)]*[）)]")
_PUNCT_RE = re.compile(r"[\s:：\-—_、,.，。；;!！?？\"'“”‘’·|]+")


def norm_title(t: str) -> str:
    """标题归一化：去编号、去括号补注、去标点空白。"""
    s = str(t or "")
    s = _NUM_RE.sub("", s)
    s = _PAREN_RE.sub("", s)
    return _PUNCT_RE.sub("", s)


def _alias_score(a: str, b: str) -> float:
    """同一别名组 -> 高分。"""
    for group in ALIASES:
        g = {norm_title(x) for x in group}
        if a in g and b in g:
            return 0.88
        # 一方是另一方的别名（含子串）
        for x in g:
            if x and (x in a or x in b) and min(len(x), 4) <= max(len(a), len(b)):
                if x in a and x in b:
                    return 0.82
    return 0.0


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def title_score(a: str, b: str) -> float:
    """两个板块标题的匹配分（0~1）。"""
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.9
    al = _alias_score(na, nb)
    if al:
        return al
    return min(0.6, _jaccard(na, nb))


def match_sections(blocks: list[dict], sections: list[Section],
                   threshold: float = MATCH_THRESHOLD) -> tuple[list[tuple[int, int, float]], list[int], list[int]]:
    """贪心匹配：返回 (pairs[(block_idx, section_idx, score)], 未匹配的 block 下标, 未匹配的 section 下标)。"""
    cands = []
    for bi, b in enumerate(blocks):
        for si, s in enumerate(sections):
            sc = title_score(b.get("title", ""), s.title)
            if sc >= threshold:
                cands.append((sc, bi, si))
    cands.sort(key=lambda x: (-x[0], x[1], x[2]))
    used_b: set[int] = set()
    used_s: set[int] = set()
    pairs: list[tuple[int, int, float]] = []
    for sc, bi, si in cands:
        if bi in used_b or si in used_s:
            continue
        used_b.add(bi)
        used_s.add(si)
        pairs.append((bi, si, round(sc, 3)))
    pairs.sort(key=lambda x: x[0])
    return pairs, [i for i in range(len(blocks)) if i not in used_b], \
        [i for i in range(len(sections)) if i not in used_s]


# ---------- 填充 ----------
def _style_from_block(block: dict) -> dict:
    """取模板板块首个段落的字符格式，作为填充内容的默认样式（字体/字号/颜色）。"""
    for e in block.get("elements") or []:
        if e.get("type") == "para":
            runs = e.get("runs") or []
            if runs:
                r0 = runs[0]
                return {"font": r0.get("font") or "", "size": r0.get("size"), "color": r0.get("color") or ""}
    return {"font": "", "size": None, "color": ""}


def _para(text: str, style: dict, align: str = "") -> dict:
    text = (text or "").strip()
    return {"id": tr._uid("e"), "type": "para", "text": text, "align": align,
            "line_spacing": None, "style": "", "level": 0,
            "runs": [{"text": text, "b": False, "i": False, "u": False,
                      "font": style.get("font") or "", "size": style.get("size"),
                      "color": style.get("color") or ""}]}


def _table_element(rows: list[list[str]], header: bool = True) -> dict:
    cells = []
    for ri, r in enumerate(rows):
        line = []
        for c in r:
            line.append({"text": str(c), "b": bool(header and ri == 0),
                         "align": "center" if (header and ri == 0) else ""})
        cells.append(line)
    return {"id": tr._uid("e"), "type": "table", "header": header, "cells": cells}


def _template_table(block: dict) -> dict | None:
    for e in block.get("elements") or []:
        if e.get("type") == "table":
            return e
    return None


def _looks_like_header(row: list) -> bool:
    """表头判定：整行都是短标签（≤6 字、无句读）才当真表头。

    这样「教学环节/教师活动/学生活动/设计意图/时间」会被当表头保留，
    而「数学抽象 | 通过分析解析式…」这种标签+长正文的行不会被误当表头。
    """
    if not row:
        return False
    texts = [str(c.get("text") or "").strip() for c in row if isinstance(c, dict)]
    texts = [t for t in texts if t]
    if not texts:
        return False
    return all(len(t) <= 6 and "。" not in t and "，" not in t for t in texts)


def _split_label(text: str) -> tuple[str, str]:
    """「重点：xxx」-> ("重点", "xxx")；没有标签前缀就返回 ("", 原文)。"""
    m = re.match(r"^([^：:]{1,8})[：:]\s*(.+)$", (text or "").strip())
    return (m.group(1), m.group(2)) if m else ("", (text or "").strip())


def _rows_for(cols: int, header: list | None, subs: list[Item], items: list[Item]) -> list[list[str]]:
    rows: list[list[str]] = []
    if header:
        cells = [str(c.get("text") or "") for c in header]
        rows.append(cells[:cols] + [""] * max(0, cols - len(cells)))
    for it in subs:
        body = (it.text or "").strip()
        if it.bullets:
            body = (body + "\n" if body else "") + "\n".join(it.bullets)
        if cols >= 2:
            rows.append(([it.title, body] + [""] * (cols - 2))[:cols])
        else:
            rows.append([it.title])
    for it in items:
        text = (it.text or "").strip()
        if not text:
            continue
        if cols == 2:
            label, body = _split_label(text)
            rows.append([label, body])
        elif cols > 2:
            rows.append(([text] + [""] * (cols - 1))[:cols])
        else:
            rows.append([text])
    return rows


def _elements_for(block: dict, sec: Section) -> tuple[list[dict], int]:
    """把一个 section 的内容装进 block 的结构里。返回 (elements, 填入的内容块数)。"""
    style = _style_from_block(block)
    tpl_tbl = _template_table(block)
    subs = [it for it in sec.items if it.kind == "sub"]
    tables = [it for it in sec.items if it.kind == "table"]
    plains = [it for it in sec.items if it.kind in ("para", "bullet") and (it.text or "").strip()]

    # 1) 生成的 markdown 自带表格 -> 直接用
    if tables:
        els = [_table_element(t.rows) for t in tables]
        for it in plains[:6]:
            els.append(_para(it.text, style))
        return els, len(els)

    # 2) 模板该板块是表格 -> 保留（识别出的）表头，用生成内容重排表格体
    if tpl_tbl is not None:
        cells = tpl_tbl.get("cells") or []
        cols = max((len(r) for r in cells), default=2)
        header = cells[0] if (cells and _looks_like_header(cells[0])) else None
        rows = _rows_for(cols, header, subs, plains)
        if rows:
            # header 要如实标：模板表格没有真表头时，第一行就是内容行，
            # 不能让它被当表头加粗、也不能让「空板块」判定把它跳过（否则填了也报空）
            return [_table_element(rows, header=bool(header))], len(rows) - (1 if header else 0)

    # 3) 默认：逐项成段（要点带 · 前缀，读起来像列表）
    els: list[dict] = []
    for it in sec.items:
        if it.kind == "sub":
            els.append(_para(it.title, {**style, "font": style.get("font") or "黑体"}))
            if it.text:
                els.append(_para(it.text, style))
            for b in it.bullets:
                els.append(_para(_BULLET_PREFIX + b, style))
        elif it.kind == "para":
            els.append(_para(it.text, style))
        elif it.kind == "bullet":
            els.append(_para(_BULLET_PREFIX + it.text, style))
    return els, len(els)


def fill_template(rich: dict, parsed: dict, threshold: float = MATCH_THRESHOLD,
                  append_unmatched: bool = True) -> tuple[dict, dict]:
    """把解析出来的教案内容填进富模板。返回 (filled_rich, report)。"""
    out = copy.deepcopy(rich or {})
    out.setdefault("blocks", [])
    sections: list[Section] = parsed.get("sections") or []
    blocks = out["blocks"]

    pairs, miss_b, miss_s = match_sections(blocks, sections, threshold)
    report = {"title": parsed.get("title", ""), "matched": [], "unmatched_blocks": [],
              "appended": [], "threshold": threshold}

    for bi, si, sc in pairs:
        sec = sections[si]
        els, filled = _elements_for(blocks[bi], sec)
        blocks[bi]["elements"] = els
        report["matched"].append({"block": blocks[bi].get("title", ""), "section": sec.title,
                                  "score": sc, "filled": filled})
    for bi in miss_b:
        report["unmatched_blocks"].append(blocks[bi].get("title", ""))

    if append_unmatched:
        for si in miss_s:
            sec = sections[si]
            if sec.title == PREAMBLE_TITLE:          # 开头散句不是板块，别造垃圾板块
                report["skipped_preamble"] = sum(len(i.text or "") for i in sec.items)
                continue
            els, _ = _elements_for({"elements": []}, sec)
            blocks.append({"id": tr._uid("b"), "kind": "section", "level": 2,
                           "title": sec.title, "elements": els})
            report["appended"].append(sec.title)

    out["plan_title"] = parsed.get("title", "")
    out["updated_at"] = tr.normalize(out).get("updated_at")
    out["_sync_report"] = report
    return out, report


# ---------- 「这个板块还空着吗」 ----------
# 模板里的占位文字：① 生成的模板带「（填写提示）」前缀；导入的模板常留「（在此填写内容）」
PLACEHOLDER_PREFIXES = ("（填写提示）", "（在此填写内容）")


def _cell_text(c) -> str:
    return (c.get("text") if isinstance(c, dict) else str(c or "")) or ""


def _is_blank_block(block: dict) -> bool:
    """板块是否「没内容」：没有元素，或元素全是占位文字 / 空表格（表头不算内容）。"""
    els = block.get("elements") or []
    if not els:
        return True
    for e in els:
        et = e.get("type")
        if et == "para":
            t = (e.get("text") or "").strip()
            if t and not t.startswith(PLACEHOLDER_PREFIXES):
                return False
        elif et == "table":
            rows = e.get("cells") or []
            body = rows[1:] if e.get("header") else rows      # 表头是模板给的，不算内容
            for row in (body or []):
                for c in (row or []):
                    t = _cell_text(c).strip()
                    if t and not t.startswith(PLACEHOLDER_PREFIXES):
                        return False
    return True


def blank_blocks(rich: dict) -> list[str]:
    """还空着的板块标题（教案中心的黄条提示用）。"""
    return [(b.get("title") or "（未命名板块）") for b in (rich.get("blocks") or [])
            if b.get("kind") != "preamble" and _is_blank_block(b)]


# ---------- 骨架模板（v1）也要能填 ----------
_NOTE_HEAD_RE = re.compile(r"表头\s*[:：]\s*([^;；\n]+)")


def _header_from_note(note: str) -> list[str]:
    """从骨架模板的 note 里还原表头：`表头: 环节 / 教师活动 / 学生活动; 6 行内容`。"""
    m = _NOTE_HEAD_RE.search(note or "")
    if not m:
        return []
    parts = [p.strip() for p in re.split(r"[/／|｜]", m.group(1))]
    return [p for p in parts if p][:6]


def rich_from_skeleton(spec) -> dict:
    """把「只有板块名」的骨架模板（v1，含内置 default）搭成可填充的富模板。

    为什么要这样：老师选中 `default` 这类内置模板时，它既不是 v2 富模板、`orig/` 里也没有原件，
    原先直接报「不是可编辑模板」——可老师要的只是「把教案按这套板块排好」，
    而起填充只需要**板块标题**，骨架里正好有。表格板块的 note 里若留着表头，也一并还原。
    """
    blocks: list[dict] = []
    for b in (getattr(spec, "blocks", None) or []):
        btype = getattr(b, "type", "") or ""
        if btype == "preamble":
            continue
        els: list[dict] = []
        if btype == "table":
            head = _header_from_note(getattr(b, "note", "") or "")
            cells = [[{"text": h, "b": True, "align": "center"} for h in head]] if head else []
            if not cells:
                cells = [[{"text": "", "b": False, "align": ""}]]
            els.append({"id": tr._uid("e"), "type": "table", "header": bool(head), "cells": cells})
        blocks.append({"id": tr._uid("b"), "kind": "section", "level": 1,
                       "title": getattr(b, "title", "") or "", "elements": els})
    return tr.normalize({"template_id": getattr(spec, "template_id", "") or "skeleton",
                         "name": getattr(spec, "name", "") or "骨架模板",
                         "source": "skeleton", "blocks": blocks})


def sync(session_markdown: str, rich: dict, threshold: float = MATCH_THRESHOLD) -> dict:
    """一步到位：Markdown + 富模板 -> 填充后的富模板 + 报告。"""
    parsed = parse_plan_markdown(session_markdown)
    real = [s for s in parsed["sections"] if s.title != PREAMBLE_TITLE]
    if not real or not any(s.items for s in real):
        return {"ok": False,
                "error": "没能从这段内容里解析出教案板块（需要 # 课题 / **板块名** / 列表 这样的结构）"}
    filled, report = fill_template(rich, parsed, threshold)
    return {"ok": True, "template": filled, "report": report, "parsed": {
        "title": parsed["title"],
        "sections": [{"title": s.title, "items": len(s.items)} for s in parsed["sections"]]}}


if __name__ == "__main__":      # 自检：python -m edu_agent.plan_sync <教案.md> <模板id>
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    from edu_agent import capabilities  # noqa: F401  仅确保包路径正确

    if len(sys.argv) < 3:
        print("用法: python -m edu_agent.plan_sync <教案.md> <模板id>")
        raise SystemExit(1)
    md = open(sys.argv[1], encoding="utf-8").read()
    tpl = tr.load_rich(sys.argv[2])
    if tpl is None:
        print("模板不是富模板或不存在:", sys.argv[2])
        raise SystemExit(1)
    res = sync(md, tpl)
    print(json.dumps(res.get("report") or res, ensure_ascii=False, indent=2))
