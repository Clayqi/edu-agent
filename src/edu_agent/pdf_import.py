"""PDF 自动切节工具（择优自 textbook-coach 路线，2026-09-06 实测修版）。

源：TEXTBOOK_PDF（数学人教A版必修第一册，266 页文字层，无内置书签）
目录页结构（实测）：每条目跨三行 —— 标题行 / 页码行 / 点线行。
方法：
  1) 扫正文前页面，按"标题+数字行成对"识别目录页；
  2) 成对解析出有序条目 (标题, 印刷页码)，按第X章分组；
  3) 由第一章正文起始物理页求 印刷->物理 偏移；
  4) 按节切片抽文本、清洗章眉/页脚 -> 每章一个 md（kind=整节/section）。
用法：python src\\edu_agent\\pdf_import.py [--pdf PATH] [--out DIR]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from edu_agent.config import load_settings  # noqa: E402

FULLWIDE = str.maketrans(
    {c: str(i) for i, c in enumerate("０１２３４５６７８９")} | {"．": ".", "，": ","}
)


def norm(s: str) -> str:
    s = s.translate(FULLWIDE)
    s = re.sub(r"[\ue000-\uf8ff\ue012]", "", s)  # 私用区杂字
    return re.sub(r"\s+", " ", s).strip()


def _pair_count(page_text: str) -> int:
    """统计一页里"标题行+紧随数字行"成对的数量（目录页特征）。"""
    lines = [norm(x) for x in page_text.splitlines()]
    pairs = 0
    for i, ln in enumerate(lines):
        if not ln or re.fullmatch(r"[….．\s]+", ln) or len(ln) < 2:
            continue
        j = i + 1
        while j < len(lines) and (not lines[j] or re.fullmatch(r"[….．\s]+", lines[j])):
            j += 1
        if j < len(lines) and re.fullmatch(r"\d{1,3}", lines[j]):
            pairs += 1
    return pairs


def find_toc_pages(doc) -> tuple[int, int]:
    q = [i for i in range(min(18, doc.page_count)) if _pair_count(doc[i].get_text()) >= 6]
    if not q:
        raise RuntimeError("未识别出目录页（需 >=6 条标题+页码成对）。")
    return min(q), max(q)


def parse_toc(doc, p0: int, p1: int) -> list[dict]:
    """成对解析目录页 -> 有序条目 [(title, page)]（跳过小结前的杂项过滤）。"""
    raw_pairs: list[tuple[str, int]] = []
    for idx in range(p0, p1 + 1):
        lines = [norm(x) for x in doc[idx].get_text().splitlines()]
        pending: str | None = None
        for ln in lines:
            if not ln or re.fullmatch(r"[….．\s]+", ln):
                continue
            if re.fullmatch(r"\d{1,3}", ln) and pending is not None:
                raw_pairs.append((pending, int(ln)))
                pending = None
            elif len(ln) >= 2:
                pending = ln
    # 只保留章/节/正文条目，丢弃书末索引之类
    drop = ("部分中英文词汇索引", "目录")
    return [{"title": t, "page": p} for t, p in raw_pairs if not any(d in t for d in drop)]


def find_offset(doc, toc_p1: int) -> int:
    """phys_idx = printed + offset。第一章(印刷1)在目录页后的首出现物理页。"""
    for i in range(toc_p1 + 1, min(20, doc.page_count)):
        if norm(doc[i].get_text()).startswith("第一章"):
            return i - 1  # printed1 -> idx i => offset = i-1
    return 5  # 兜底（实测偏移 5）


def is_chapter(t: str) -> bool:
    return bool(re.match(r"^第[一二三四五六七八九十]+章", t))


def _alnum(s: str) -> str:
    """去标点空格，用于比对重复的章眉/节眉/页码行。"""
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", s)


def clean_body_text(t: str, drop_keys: set[str]) -> str:
    """清洗一页正文：去页脚页码行、重复的章眉/节眉行（按字母数字指纹比对）。"""
    out = []
    for raw in t.splitlines():
        line = norm(raw)
        if not line:
            continue
        if re.fullmatch(r"\d{1,3}", line):          # 页脚页码
            continue
        if _alnum(line) in drop_keys:               # 重复的页眉（章/节标题）
            continue
        out.append(line)
    return "\n".join(out)


def extract_and_write(doc, entries: list[dict], offset: int, out_dir: Path) -> int:
    # 章边界
    ch_idx = [i for i, e in enumerate(entries) if is_chapter(e["title"])]
    total = 0
    for ci, cpos in enumerate(ch_idx):
        ch_title_full = entries[cpos]["title"]          # 如 第一章 集合与常用逻辑用语
        m = re.match(r"^(第[一二三四五六七八九十]+章)(.*)$", ch_title_full)
        ch_label, ch_name = m.group(1), m.group(2).strip()
        cn = ci + 1
        nxt = ch_idx[ci + 1] if ci + 1 < len(ch_idx) else len(entries)
        bucket = entries[cpos + 1:nxt]                  # 本章条目（节/小结/复习）
        last_printed = (entries[nxt]["page"] - 1 if nxt < len(entries) else doc.page_count - offset)
        md: list[str] = [
            "---",
            "subject: 数学",
            "book: 必修第一册",
            "version: 人教A版2019课标版",
            f"chapter: {ch_label}",
            f"chapter_title: {ch_name}",
            "---",
            "",
        ]
        n_chunk = 0
        for bi, e in enumerate(bucket):
            start = e["page"]
            end = bucket[bi + 1]["page"] - 1 if bi + 1 < len(bucket) else last_printed
            drop_keys = {_alnum(f"{ch_label}{ch_name}")}
            for be in bucket:
                drop_keys.add(_alnum(be["title"]))
            texts = []
            for printed in range(start, end + 1):
                idx = printed + offset
                if 0 <= idx < doc.page_count:
                    texts.append(clean_body_text(doc[idx].get_text(), drop_keys))
            body = "\n".join(t for t in texts if t.strip()).strip()
            if not body:
                continue
            sec = e["title"]
            m2 = re.match(r"^(\d+(?:\.\d+)*)", sec)
            if m2:
                sec_no, heading = m2.group(1), sec[m2.end():].strip()
            else:
                sec_no, heading = "", sec
            cid = f"math-m1-c{cn}-{sec_no.replace('.', '_')}" if sec_no else f"math-m1-c{cn}-x{bi + 1:02d}"
            md.append(f"【整节】{cid}|{sec_no}|{heading}|p{start}|整节正文")
            md.append(body)
            md.append("")
            n_chunk += 1
        if n_chunk:
            p = out_dir / f"数学必修一_{ch_label}_{ch_name}_auto.md"
            p.write_text("\n".join(md), encoding="utf-8")
            chars = sum(len(x) for x in md) - sum(len(x) for x in md if not x.strip())
            print(f"-> {p.name}: {n_chunk} 节")
            total += n_chunk
        else:
            print(f"!! {ch_label} {ch_name}: 0 节，跳过")
    return total


def main() -> None:
    import pymupdf

    s = load_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=str(s.textbook_pdf or ""))
    ap.add_argument("--out", default=str(s.auto_content_dir))
    args = ap.parse_args()

    pdf = Path(args.pdf)
    if not pdf.exists():
        raise SystemExit(f"PDF 不存在: {pdf}（在 .env 配置 TEXTBOOK_PDF）")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(str(pdf))
    print(f"PDF: {pdf.name} | pages: {doc.page_count}")
    p0, p1 = find_toc_pages(doc)
    print(f"目录页(0-based): {p0}..{p1}")
    entries = parse_toc(doc, p0, p1)
    print(f"解析条目: {len(entries)} 条")
    for e in entries[:6]:
        print("  toc:", e)
    offset = find_offset(doc, p1)
    print(f"印刷->物理 偏移: +{offset}（phys_idx = printed + offset）")

    total = extract_and_write(doc, entries, offset, out_dir)
    print(f"合计整节 chunk: {total}")

    # 抽查第一章第一节
    f1 = out_dir / "数学必修一_第一章_集合与常用逻辑用语_auto.md"
    if f1.exists():
        lines = f1.read_text(encoding="utf-8").splitlines()
        hdr = next((i for i, l in enumerate(lines) if l.startswith("【整节】")), None)
        if hdr is not None:
            print("\n===== 抽查 =====")
            print(lines[hdr])
            print("\n".join(lines[hdr + 1:hdr + 6])[:400])


if __name__ == "__main__":
    main()
