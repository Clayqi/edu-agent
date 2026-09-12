# -*- coding: utf-8 -*-
"""富教案模板：.docx <-> 可全量编辑的结构（板块 / 段落 / 表格 + 字符与段落格式）。

与 `template_spec.py` 的分工：
- `template_spec` 是给 Agent B 用的**简单骨架**（板块顺序 + 名称 + 备注）；
- 本模块是给教案中心**编辑**用的**富模型**：保住文字、段落结构、表格和格式。

两者**共用** `content/templates/<id>.json`：富模板写成 `spec_version: 2`，
`template_spec.get_template()` 读到 v2 会自动派生简单 blocks（见 `derive_simple`），
所以模板列表只有一个，Agent B 也能直接套用户导入并改过的模板。

JSON 形状：
    {
      "spec_version": 2,
      "template_id": "...", "name": "...", "source": "...", "updated_at": "...",
      "blocks": [
        {"id": "b1", "kind": "section"|"preamble", "level": 1, "title": "教学目标",
         "elements": [
           {"id": "e1", "type": "para", "align": "left", "line_spacing": 1.5,
            "style": "Normal", "level": 0,
            "runs": [{"text": "…", "b": false, "i": false, "u": false,
                      "font": "宋体", "size": 12, "color": "#000000"}]},
           {"id": "e2", "type": "table", "header": true,
            "cells": [[{"text": "…", "b": true, "align": "center"}]]},
           {"id": "e3", "type": "image", "alt": "图片（导入不保留，导出会跳过）"}
         ]}
      ]
    }
"""
from __future__ import annotations

import copy
import json
import re
import shutil
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

from edu_agent import template_spec as ts

ROOT = ts.ROOT
TEMPLATES_DIR = ts.TEMPLATES_DIR
ORIG_DIR = ts.ORIG_DIR
SPEC_VERSION = 2

ALIGNS = ("left", "center", "right", "justify")
DEFAULT_FONT = "宋体"
DEFAULT_ASCII_FONT = "Times New Roman"
DEFAULT_SIZE = 12.0
MAX_LEVEL = 4

# 短编号行：一、/（一）/1./1)、1
_NUM_HEAD = re.compile(r"^[（(]?[一二三四五六七八九十0-9]{1,3}[、.．)）]?\s*\S")


# ---------- 小工具 ----------
def _uid(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def _slug(s: str) -> str:
    return ts._slugify(s)


def _hex(color) -> str:
    """python-docx 的颜色对象 -> #RRGGBB（取不到返回空）。"""
    try:
        rgb = getattr(color, "rgb", None)
        if rgb is None:
            return ""
        return "#" + str(rgb).upper()
    except Exception:
        return ""


def _run_font(run) -> str:
    """取中文字体优先（eastAsia），退回 ascii 字体。"""
    try:
        from docx.oxml.ns import qn

        rpr = run._element.rPr
        if rpr is not None:
            rfonts = rpr.find(qn("w:rFonts"))
            if rfonts is not None:
                ea = rfonts.get(qn("w:eastAsia"))
                if ea:
                    return ea
    except Exception:
        pass
    return run.font.name or ""


def _para_align(p) -> str:
    try:
        a = p.alignment
        if a is None:
            return ""
        name = str(a).split()[0].lower()
        return {"left": "left", "center": "center", "right": "right",
                "justify": "justify", "both": "justify"}.get(name, "")
    except Exception:
        return ""


def _heading_level(p, text: str) -> int:
    """0 = 不是标题；1..4 = 标题层级。

    比 template_spec._looks_heading **更严格**：富模型要保真，宁可少判标题，
    也不要把整句正文（如「教学重点：理解函数的概念，掌握…」）当成板块名。
    规则：样式命中 > 短编号行 > 全加粗短行 > 关键词精确/短前缀命中。
    """
    style = (p.style.name or "") if p.style is not None else ""
    if "Head" in style or "标题" in style or "Title" in style:
        m = re.search(r"(\d+)", style)
        lvl = int(m.group(1)) if m else 1
        return max(1, min(MAX_LEVEL, lvl))

    t = (text or "").strip()
    if not t or len(t) > 30:
        return 0
    if t.endswith(("。", "！", "？", "；", "，", ".", "!", "?", ";", ",")):
        return 0
    if _NUM_HEAD.match(t):
        return 1
    runs = [r for r in p.runs if (r.text or "").strip()]
    if runs and all(r.bold for r in runs):
        return 1
    if t in ts.BLOCK_KEYWORDS:
        return 1
    for k in ts.BLOCK_KEYWORDS:
        if t.startswith(k) and len(t) <= len(k) + 6:
            return 1
    return 0


def _line_spacing(p) -> float | None:
    try:
        ls = p.paragraph_format.line_spacing
        if ls is None:
            return None
        if isinstance(ls, (int, float)):
            return round(float(ls), 2)
        return round(float(ls.pt), 2)      # Length（固定值）
    except Exception:
        return None


# ---------- .docx -> 富模型 ----------
def _runs_of(p) -> list[dict]:
    """段落里的字符格式（逐 run）。"""
    runs = []
    for r in p.runs:
        t = r.text or ""
        if not t:
            continue
        runs.append({
            "text": t,
            "b": bool(r.bold),
            "i": bool(r.italic),
            "u": bool(r.underline),
            "font": _run_font(r),
            "size": round(float(r.font.size.pt), 1) if r.font.size else None,
            "color": _hex(r.font.color),
        })
    return runs


def _para_element(p) -> dict | None:
    text = (p.text or "").strip()
    runs = _runs_of(p)
    if not text and not runs:
        # 可能是图片段落
        try:
            if p._element.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}drawing"):
                return {"id": _uid("e"), "type": "image", "alt": "图片（导入不保留，导出会跳过）"}
        except Exception:
            pass
        return None
    return {
        "id": _uid("e"), "type": "para", "text": text,
        "align": _para_align(p), "line_spacing": _line_spacing(p),
        "style": (p.style.name or "") if p.style is not None else "",
        "level": 0,
        "runs": runs or [{"text": text, "b": False, "i": False, "u": False,
                          "font": "", "size": None, "color": ""}],
    }


def _table_element(tbl) -> dict:
    cells: list[list[dict]] = []
    for ri, row in enumerate(tbl.rows):
        line = []
        for cell in row.cells:
            paras = [pp for pp in cell.paragraphs]
            text = "\n".join((pp.text or "").strip() for pp in paras if (pp.text or "").strip())
            bold = False
            try:
                for pp in paras:
                    for r in pp.runs:
                        if (r.text or "").strip():
                            bold = bool(r.bold)
                            break
                    if bold:
                        break
            except Exception:
                bold = False
            align = _para_align(paras[0]) if paras else ""
            line.append({"text": text, "b": bold or ri == 0, "align": align or ("center" if ri == 0 else "")})
        cells.append(line)
    return {"id": _uid("e"), "type": "table", "header": True, "cells": cells}


def docx_to_rich(path: str | Path, template_id: str | None = None,
                 name: str | None = None) -> dict:
    """解析 .docx -> 富模板 dict（不落盘）。标题行开新板块，其余归到当前板块。"""
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    doc = Document(str(path))

    blocks: list[dict] = []

    def new_block(kind: str, title: str, level: int = 1, para=None) -> dict:
        b = {"id": _uid("b"), "kind": kind, "level": max(1, min(MAX_LEVEL, level)),
             "title": title, "elements": []}
        if para is not None:          # 保住标题自己的格式，导出时还原
            b["title_align"] = _para_align(para)
            b["title_runs"] = _runs_of(para)
        blocks.append(b)
        return b

    cur: dict | None = None
    image_only = 0
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            p = Paragraph(child, doc)
            text = (p.text or "").strip()
            lvl = _heading_level(p, text) if text else 0
            if lvl > 0:
                cur = new_block("section", text, lvl, para=p)
                continue
            el = _para_element(p)
            if el is None:
                continue
            if el["type"] == "image":
                image_only += 1
            if cur is None:
                cur = new_block("preamble", "（模板开头）", 1)
            cur["elements"].append(el)
        elif child.tag == qn("w:tbl"):
            tbl = Table(child, doc)
            if not tbl.rows:
                continue
            if cur is None:
                cur = new_block("preamble", "（模板开头）", 1)
            cur["elements"].append(_table_element(tbl))

    return {
        "spec_version": SPEC_VERSION,
        "template_id": template_id or _slug(path.stem),
        "name": name or path.stem,
        "source": str(path),
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "blocks": blocks,
        "stats": {"blocks": len(blocks),
                  "elements": sum(len(b["elements"]) for b in blocks),
                  "images_skipped": image_only},
    }


# ---------- 派生给 Agent B 的简单骨架 ----------
def derive_simple(rich: dict) -> list[dict]:
    """富模型 -> template_spec.Block 列表（order/type/title/note）。"""
    out: list[dict] = []
    for i, b in enumerate(rich.get("blocks") or [], 1):
        els = b.get("elements") or []
        kind = b.get("kind") or "section"
        title = (b.get("title") or "").strip() or f"板块{i}"
        paras = [e.get("text", "").strip() for e in els if e.get("type") == "para"]
        paras = [t for t in paras if t]
        table = next((e for e in els if e.get("type") == "table"), None)
        if kind == "preamble":
            out.append({"order": i, "type": "preamble", "title": title,
                        "note": " ".join(paras)[:200]})
        elif table is not None and not paras:
            head = " / ".join(c.get("text", "") for c in (table.get("cells") or [[]])[0])
            out.append({"order": i, "type": "table", "title": title,
                        "note": f"表头: {head}; {max(0, len(table.get('cells') or []) - 1)} 行内容"})
        else:
            out.append({"order": i, "type": "heading", "title": title,
                        "note": "；".join(paras)[:300]})
    return out


# ---------- 规范化（前端回传的模型先过这里，防脏数据） ----------
def normalize(rich: dict) -> dict:
    out = copy.deepcopy(rich or {})
    out["spec_version"] = SPEC_VERSION
    tid = _slug(str(out.get("template_id") or out.get("name") or "template"))
    out["template_id"] = tid
    out["name"] = str(out.get("name") or tid)[:120]
    out.setdefault("source", "")
    out["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    blocks = []
    for b in (out.get("blocks") or []):
        if not isinstance(b, dict):
            continue
        nb = {"id": str(b.get("id") or _uid("b")),
              "kind": "preamble" if b.get("kind") == "preamble" else "section",
              "level": max(1, min(MAX_LEVEL, int(b.get("level") or 1))),
              "title": str(b.get("title") or "").strip(),
              "elements": []}
        if b.get("title_align") in ALIGNS:
            nb["title_align"] = b["title_align"]
        if isinstance(b.get("title_runs"), list):
            nb["title_runs"] = [{"text": str(r.get("text") or ""),
                                 "b": bool(r.get("b")), "i": bool(r.get("i")), "u": bool(r.get("u")),
                                 "font": str(r.get("font") or ""),
                                 "size": float(r["size"]) if r.get("size") else None,
                                 "color": str(r.get("color") or "")}
                                for r in b["title_runs"] if isinstance(r, dict)]
        for e in (b.get("elements") or []):
            if not isinstance(e, dict):
                continue
            et = e.get("type")
            if et == "table":
                cells = []
                for row in (e.get("cells") or []):
                    line = []
                    for c in (row or []):
                        if isinstance(c, dict):
                            line.append({"text": str(c.get("text") or ""),
                                         "b": bool(c.get("b")),
                                         "align": c.get("align") if c.get("align") in ALIGNS else ""})
                        else:
                            line.append({"text": str(c or ""), "b": False, "align": ""})
                    cells.append(line)
                if not cells:
                    cells = [[{"text": "", "b": True, "align": "center"},
                              {"text": "", "b": True, "align": "center"}]]
                width = max(len(r) for r in cells)
                cells = [r + [{"text": "", "b": False, "align": ""}] * (width - len(r)) for r in cells]
                nb["elements"].append({"id": str(e.get("id") or _uid("e")), "type": "table",
                                       "header": bool(e.get("header", True)), "cells": cells})
            elif et == "image":
                nb["elements"].append({"id": str(e.get("id") or _uid("e")), "type": "image",
                                       "alt": str(e.get("alt") or "图片（不保留）")})
            else:
                text = str(e.get("text") or "")
                runs = []
                for r in (e.get("runs") or []):
                    if not isinstance(r, dict):
                        continue
                    runs.append({"text": str(r.get("text") or ""),
                                 "b": bool(r.get("b")), "i": bool(r.get("i")), "u": bool(r.get("u")),
                                 "font": str(r.get("font") or ""),
                                 "size": float(r["size"]) if r.get("size") else None,
                                 "color": str(r.get("color") or "")})
                if not runs:
                    runs = [{"text": text, "b": False, "i": False, "u": False,
                             "font": "", "size": None, "color": ""}]
                nb["elements"].append({
                    "id": str(e.get("id") or _uid("e")), "type": "para", "text": text,
                    "align": e.get("align") if e.get("align") in ALIGNS else "",
                    "line_spacing": (float(e["line_spacing"]) if e.get("line_spacing") else None),
                    "style": str(e.get("style") or ""),
                    "level": max(0, min(MAX_LEVEL, int(e.get("level") or 0))),
                    "runs": runs})
        blocks.append(nb)
    out["blocks"] = blocks
    return out


# ---------- 存取 ----------
def save_rich(rich: dict, docx_source: str | Path | None = None,
              set_current: bool = False) -> Path:
    """把富模板写进 content/templates/<id>.json（原件备份到 orig/）。"""
    rich = normalize(rich)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    ORIG_DIR.mkdir(parents=True, exist_ok=True)
    p = TEMPLATES_DIR / f"{rich['template_id']}.json"
    p.write_text(json.dumps(rich, ensure_ascii=False, indent=2), encoding="utf-8")
    src = docx_source or rich.get("source")
    if src and Path(src).exists() and Path(src).suffix.lower() == ".docx":
        try:
            dst = ORIG_DIR / f"{rich['template_id']}.docx"
            # 源就是目的（例如「用原件升级」后再保存）就不必自拷，避免无谓的文件占用
            same = False
            try:
                same = Path(src).resolve() == dst.resolve()
            except Exception:
                same = False
            if not same:
                shutil.copy2(src, dst)
            rich["source"] = f"orig/{rich['template_id']}.docx"
            p.write_text(json.dumps(rich, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    if set_current:
        ts.set_current(rich["template_id"])
    return p


def load_rich(template_id: str) -> dict | None:
    """读富模板；不存在或不是 v2 返回 None。"""
    p = TEMPLATES_DIR / f"{template_id}.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if int(d.get("spec_version") or 1) < SPEC_VERSION:
        return None
    return d


def is_rich(template_id: str) -> bool:
    return load_rich(template_id) is not None


def delete_template(template_id: str) -> dict:
    """删除已保存的模板（**软删**：移到 `content/templates/_trash/<时间戳>_<id>/`）。

    为什么软删：模板是老师自己导入/整理出来的资产，误点一下不该就没了。
    真要彻底清除，去 `_trash/` 把对应目录删掉即可（目录名带时间戳）。

    一起处理三件事：
      - `<id>.json`（模板本体）与 `orig/<id>.docx`（原件备份）都移走；
      - 如果删的正是「当前模板」，把当前切回内置 `default`（否则 Agent B 会指向一个不存在的模板）；
      - 删 `default` 时它只是「存档覆盖了内置骨架」，删掉即恢复内置版。
    """
    tid = (template_id or "").strip()
    if not tid:
        return {"ok": False, "error": "缺少 template_id"}
    p = TEMPLATES_DIR / f"{tid}.json"
    orig = ORIG_DIR / f"{tid}.docx"
    if not p.exists() and not orig.exists():
        if tid == "default":
            return {"ok": False, "error": "「default」是内置模板，没有存档可删"}
        return {"ok": False, "error": f"没有模板「{tid}」（可能已被删除）"}

    was_current = False
    try:
        was_current = ts.get_current().template_id == tid
    except Exception:
        was_current = False
    name = ""
    try:
        d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        name = str(d.get("name") or "")
    except Exception:
        name = ""

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    trash = TEMPLATES_DIR / "_trash" / f"{stamp}_{_slug(tid)}"
    trash.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    for f in (p, orig):
        try:
            if f.exists():
                shutil.move(str(f), str(trash / f.name))
                moved.append(f.name)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"删除失败（已移走 {moved or '无'}）：{type(e).__name__}: {e}",
                    "trash": str(trash), "moved": moved}
    if was_current:
        ts.set_current("default")
    return {"ok": True, "template_id": tid, "name": name, "moved": moved,
            "trash": str(trash), "was_current": was_current,
            "builtin_now": tid == "default",
            "current": ts.get_current().template_id}


def stats(rich: dict) -> dict:
    blocks = rich.get("blocks") or []
    els = [e for b in blocks for e in (b.get("elements") or [])]
    return {
        "blocks": len(blocks),
        "paragraphs": sum(1 for e in els if e.get("type") == "para"),
        "tables": sum(1 for e in els if e.get("type") == "table"),
        "images": sum(1 for e in els if e.get("type") == "image"),
        "chars": sum(len(e.get("text") or "") for e in els if e.get("type") == "para"),
    }


def blank_rich(name: str = "新模板") -> dict:
    """空白模板（UI 里「新建」用）。"""
    return normalize({
        "template_id": _slug(name), "name": name, "source": "",
        "blocks": [{"id": _uid("b"), "kind": "section", "level": 1, "title": "教学目标",
                    "elements": [{"id": _uid("e"), "type": "para", "text": "",
                                  "align": "", "runs": []}]},
                   {"id": _uid("b"), "kind": "section", "level": 1, "title": "教学重难点",
                    "elements": [{"id": _uid("e"), "type": "para", "text": "",
                                  "align": "", "runs": []}]},
                   {"id": _uid("b"), "kind": "section", "level": 1, "title": "教学过程",
                    "elements": [{"id": _uid("e"), "type": "para", "text": "",
                                  "align": "", "runs": []}]},
                   {"id": _uid("b"), "kind": "section", "level": 1, "title": "板书设计",
                    "elements": [{"id": _uid("e"), "type": "para", "text": "",
                                  "align": "", "runs": []}]},
                   {"id": _uid("b"), "kind": "section", "level": 1, "title": "作业布置",
                    "elements": [{"id": _uid("e"), "type": "para", "text": "",
                                  "align": "", "runs": []}]},
                   {"id": _uid("b"), "kind": "section", "level": 1, "title": "教学反思",
                    "elements": [{"id": _uid("e"), "type": "para", "text": "",
                                  "align": "", "runs": []}]}],
    })


if __name__ == "__main__":      # 自检：python -m edu_agent.template_rich <模板.docx> [--save]
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("用法: python -m edu_agent.template_rich <模板.docx> [--save]")
        raise SystemExit(1)
    rich = docx_to_rich(sys.argv[1])
    print(json.dumps({"id": rich["template_id"], "name": rich["name"],
                      "stats": stats(rich),
                      "blocks": [{"title": b["title"], "kind": b["kind"], "level": b["level"],
                                  "elements": [e["type"] for e in b["elements"]]}
                                 for b in rich["blocks"][:8]]},
                     ensure_ascii=False, indent=2))
    if "--save" in sys.argv:
        print("已存档:", save_rich(rich, sys.argv[1]))
