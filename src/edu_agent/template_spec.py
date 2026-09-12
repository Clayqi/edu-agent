"""Agent B · 教案模板认定模块（独立）：Word .docx -> TemplateSpec。

TemplateSpec = {template_id, name, source, blocks:[{order, type, title, note}]}
  type: heading(板块标题) | preamble(开头无标题段) | table(表格板块)

认定流程（编排层/UI 驱动）：
  1) recognize_docx(path) -> TemplateSpec（仅解析，不落盘）
  2) 老师回读确认/增删改
  3) save_template(spec, docx源) -> content/templates/<id>.json + 原件备份
当前模板：content/templates/_current.json 记录生效 id（默认 default）。
"""
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT / "content" / "templates"
ORIG_DIR = TEMPLATES_DIR / "orig"
CURRENT_FILE = TEMPLATES_DIR / "_current.json"

BLOCK_KEYWORDS = (
    "教学目标", "知识目标", "能力目标", "素养目标", "重难点", "教学重点", "教学难点",
    "教学过程", "导入新课", "课堂导入", "情境导入", "新知讲授", "新课讲授", "合作探究",
    "典型例题", "例题精讲", "巩固练习", "随堂练习", "课堂小结", "小结",
    "板书设计", "作业布置", "作业设计", "课后作业", "教学反思", "评价设计",
    "教学准备", "教具准备", "学情分析", "教材分析", "教法学法", "时间分配",
    "教学环节", "教师活动", "学生活动", "设计意图", "设计说明", "教学媒体",
)

_NUM_HEAD = re.compile(r"^[（(]?[一二三四五六七八九十0-9]{1,3}[、.．)）]?\S")


@dataclass
class Block:
    order: int
    type: str = "heading"        # heading | preamble | table
    title: str = ""
    note: str = ""


@dataclass
class TemplateSpec:
    template_id: str
    name: str
    source: str = ""
    blocks: list[Block] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TemplateSpec":
        return cls(template_id=d["template_id"], name=d.get("name", ""),
                   source=d.get("source", ""),
                   blocks=[Block(**b) for b in d.get("blocks", [])])


def _looks_heading(text: str, style: str, runs) -> bool:
    t = text.strip()
    if not t or len(t) > 60:
        return False
    if "Head" in style or "标题" in style or "Title" in style:
        return True
    if any(k in t for k in BLOCK_KEYWORDS):
        return True
    if _NUM_HEAD.match(t):
        return True
    bold_runs = [r for r in runs if r.text.strip()]
    if bold_runs and all(r.bold for r in bold_runs):
        return True
    return False


def _block_list(doc) -> list[dict]:
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    blocks: list[dict] = []
    cur: dict | None = None

    def push(p_or_note, type_: str, title: str, note: str):
        nonlocal cur
        b = {"order": len(blocks) + 1, "type": type_, "title": title, "note": note.strip()}
        blocks.append(b)
        cur = b

    for child in doc.element.body.iterchildren():
        tag = child.tag
        if tag == qn("w:p"):
            p = Paragraph(child, doc)
            txt = (p.text or "").strip()
            if not txt:
                continue
            if _looks_heading(txt, p.style.name or "", p.runs):
                push(None, "heading", txt, "")
            else:
                if cur is None:
                    push(None, "preamble", "（模板开头）", "")
                cur["note"] = (cur["note"] + "\n" + txt).strip()
        elif tag == qn("w:tbl"):
            t = Table(child, doc)
            if t.rows:
                head = " / ".join(c.text.strip() for c in t.rows[0].cells)
                info = f"表头: {head}; {len(t.rows)-1} 行内容"
            else:
                info = "空表格"
            push(None, "table", f"表格({len(t.columns)}列)", info)
    return blocks


def _slugify(s: str) -> str:
    """文件名 -> 模板 id：保留中英数，其余转 _。"""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[\W_]+", "_", s, flags=re.UNICODE).strip("_") or "template"
    return s[:60]


def recognize_docx(path: str | Path) -> TemplateSpec:
    """解析 Word docx -> TemplateSpec（不落盘）。需要 python-docx。"""
    from docx import Document

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    doc = Document(str(path))
    spec = TemplateSpec(
        template_id=_slugify(path.stem),
        name=path.stem,
        source=str(path),
        blocks=[],
    )
    spec.blocks = [Block(**b) for b in _block_list(doc)]
    return spec


def default_template() -> TemplateSpec:
    """内置默认完整课时模板（常驻，可用 docx 认定替换/并存）。"""
    titles = [
        "教材与学情分析", "教学目标", "教学重难点",
        "教学过程", "板书设计", "作业布置", "教学反思",
    ]
    return TemplateSpec(
        template_id="default",
        name="完整课时模板（默认）",
        source="builtin",
        blocks=[Block(order=i + 1, type="heading", title=t) for i, t in enumerate(titles)],
    )


def _ensure_dirs():
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    ORIG_DIR.mkdir(parents=True, exist_ok=True)


def save_template(spec: TemplateSpec, docx_source: str | Path | None = None) -> Path:
    """存档认定模板：json 落 content/templates/<id>.json，原件备份到 orig/。"""
    _ensure_dirs()
    p = TEMPLATES_DIR / f"{spec.template_id}.json"
    p.write_text(json.dumps(spec.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    if docx_source and Path(docx_source).exists():
        shutil.copy2(docx_source, ORIG_DIR / f"{spec.template_id}.docx")
    return p


def list_templates() -> list[dict]:
    """列出可用模板（内置 default + content/templates/*.json，排除 _current）。

    富模板（spec_version>=2，见 template_rich.py）会带 rich=True，UI 可据此进富编辑器。
    """
    out = []
    if TEMPLATES_DIR.exists():
        for f in sorted(TEMPLATES_DIR.glob("*.json")):
            if f.name.startswith("_"):
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                out.append({"template_id": d.get("template_id"), "name": d.get("name"),
                            "blocks": len(d.get("blocks", [])),
                            "rich": int(d.get("spec_version") or 1) >= 2})
            except Exception:
                continue
    if not any(o["template_id"] == "default" for o in out):
        dt = default_template()
        out.insert(0, {"template_id": "default", "name": dt.name, "blocks": len(dt.blocks),
                       "rich": False})
    return out


def get_template(template_id: str) -> TemplateSpec:
    """读指定模板；缺省回退 default。

    富模板（template_rich 写的 spec_version>=2）在这里**派生**成简单骨架，
    因此 Agent B 的模板列表与教案中心的富编辑器共用同一批模板文件。

    注：`default` 只有**在没有同名存档文件时**才用内置骨架。否则「按内置 default 填好教案 →
    保存为模板」会出现「教案中心显示的是填好的那份、Agent B 却还在用内置骨架」的错位。
    """
    if not template_id:
        return default_template()
    p = TEMPLATES_DIR / f"{template_id}.json"
    if template_id == "default" and not p.exists():
        return default_template()
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return default_template()
        if int(d.get("spec_version") or 1) >= 2:
            try:
                from edu_agent import template_rich          # 延迟导入避免环

                return TemplateSpec(template_id=d.get("template_id", template_id),
                                    name=d.get("name", ""),
                                    source=d.get("source", ""),
                                    blocks=[Block(**b) for b in template_rich.derive_simple(d)])
            except Exception:
                return default_template()
        try:
            return TemplateSpec.from_dict(d)
        except Exception:
            pass
    return default_template()


def get_current() -> TemplateSpec:
    """当前生效模板。"""
    tid = "default"
    if CURRENT_FILE.exists():
        try:
            tid = json.loads(CURRENT_FILE.read_text(encoding="utf-8")).get("template_id", "default")
        except Exception:
            pass
    return get_template(tid)


def set_current(template_id: str) -> None:
    _ensure_dirs()
    CURRENT_FILE.write_text(json.dumps({"template_id": template_id}, ensure_ascii=False), encoding="utf-8")


def template_sketch(spec: TemplateSpec) -> str:
    """给编排/LLM 的模板骨架文本（板块顺序与名称）。"""
    lines = []
    for b in spec.blocks:
        if b.type == "table":
            lines.append(f"{b.order}. 【表格板块】{b.title}（{b.note}）")
        elif b.type == "preamble":
            continue
        else:
            lines.append(f"{b.order}. {b.title}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python template_spec.py <模板.docx> [--save]")
        raise SystemExit(1)
    sp = recognize_docx(sys.argv[1])
    print("=== 模板认定预览 ===")

    print(f"模板名: {sp.name} | id: {sp.template_id} | 板块数: {len(sp.blocks)}")
    print(template_sketch(sp))
    if "--save" in sys.argv:
        save_template(sp, sys.argv[1])
        print(f"\n已存档: content/templates/{sp.template_id}.json")
