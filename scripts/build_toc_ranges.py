"""生成教材目录页码范围 data/toc_ranges.json（供「看原页」浏览器翻页/跳页用）。

数据来源：教材向量库 edu_textbook 的 151 个片段（每个片段带 chapter/section/heading/page，
page = 印刷页码）。教材连续排版，故：
  节范围  = 本节最小印刷页 .. 同章下一节最小印刷页-1（章内最后一节 -> 章末）
  章范围  = 该章最小印刷页 .. 下一章最小印刷页-1（最后一章 -> 全书印刷末页）
印刷页 -> 物理页的换算仍由 web_server/page_image 负责（offset=6）。

用法：.venv\\Scripts\\python.exe scripts\\build_toc_ranges.py
产物：data/toc_ranges.json（前端 GET /api/textbook/toc 读它）
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import chromadb  # noqa: E402

OUT = ROOT / "content" / "toc_ranges.json"   # 放 content/：属"可再生的静态内容"，随仓库走（data/ 被 .gitignore 排除）
OUT_LEGACY = ROOT / "data" / "toc_ranges.json"  # 旧位置，保留兼容
OFFSET = 6


def cn_chapter_order(ch: str) -> int:
    m = re.search(r"第([一二三四五六七八九十]+)章", ch or "")
    if not m:
        return 99
    cn = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    s = m.group(1)
    if "十" in s:
        a, _, b = s.partition("十")
        return (cn.get(a) or 1) * 10 + (cn.get(b, 0) if b else 0)
    return cn.get(s, 99)


def chapter_open_pages(pdf, offset: int, ordered: list[tuple[str, int]]) -> dict[str, int]:
    """章首页（印刷页码）：在「上一章首页 .. 本章第一节页」窗口内找章名最早出现的物理页。

    注意：PDF 前部有目录页（物理 5~6），目录里列出所有章名，所以**不能全书盲扫**——
    必须限定在各章的窗口内，且从印刷第 1 页（物理 7）之后开始。
    ordered: [(章名, 该章第一节的印刷页), ...] 按章序。
    """
    import pymupdf

    found: dict[str, int] = {}
    if not pdf or not Path(pdf).exists():
        return found
    doc = pymupdf.open(str(pdf))
    try:
        lo_printed = 1
        for ch, first_sec_page in ordered:
            hi_printed = first_sec_page
            lo = max(7, lo_printed + offset)          # 物理页 >= 7 = 印刷页 >= 1（跳过封面/目录）
            hi = min(doc.page_count, hi_printed + offset)
            for p in range(lo, hi + 1):
                if ch in doc[p - 1].get_text():
                    found[ch] = p - offset
                    break
            lo_printed = found.get(ch, first_sec_page)
        # 兜底：窗口内没找到就用第一节页
        for ch, first_sec_page in ordered:
            found.setdefault(ch, first_sec_page)
    finally:
        doc.close()
    return found


def main() -> int:
    import pymupdf

    from edu_agent.config import load_settings

    s = load_settings()
    pdf = s.textbook_pdf
    total_phys = pymupdf.open(str(pdf)).page_count if pdf and Path(pdf).exists() else None
    printed_last = (total_phys - OFFSET) if total_phys else None

    col = chromadb.PersistentClient(path=str(ROOT / "chroma_db")).get_collection("edu_textbook")
    data = col.get(include=["metadatas"])
    items = []
    for md in data["metadatas"]:
        if md.get("page") is None:
            continue
        items.append({
            "chapter": md.get("chapter") or "",
            "section": md.get("section") or "",
            "heading": md.get("heading") or "",
            "page": int(md["page"]),
        })

    # 章按页序排；节按页序排
    chapters: dict[str, list[dict]] = {}
    for it in items:
        chapters.setdefault(it["chapter"], []).append(it)

    ch_list = sorted(chapters.items(), key=lambda kv: (min(x["page"] for x in kv[1]), cn_chapter_order(kv[0])))
    opens = chapter_open_pages(pdf, OFFSET, [(c, min(x["page"] for x in a)) for c, a in ch_list])
    out_chapters = []
    for idx, (ch, arr) in enumerate(ch_list):
        # 去重合并同 section（同 section 可能有多块）
        secs: dict[str, dict] = {}
        for it in sorted(arr, key=lambda x: x["page"]):
            key = it["section"] or "(旁栏)"
            cur = secs.get(key)
            if cur is None:
                secs[key] = {"section": it["section"], "heading": it["heading"], "start": it["page"], "end": it["page"]}
            else:
                cur["end"] = max(cur["end"], it["page"])
                if not cur["heading"]:
                    cur["heading"] = it["heading"]
        sec_list = sorted(secs.values(), key=lambda x: x["start"])
        # 章首页：优先用 PDF 里章名最早出现页（含章首图/引言），否则退回首节页
        ch_start = opens.get(ch) or (sec_list[0]["start"] if sec_list else None)
        if sec_list and ch_start > sec_list[0]["start"]:
            ch_start = sec_list[0]["start"]
        nxt = ch_list[idx + 1] if idx + 1 < len(ch_list) else None
        ch_end = printed_last
        if nxt:
            nx_open = opens.get(nxt[0])
            ch_end = (nx_open - 1) if nx_open else (min(x["page"] for x in nxt[1]) - 1)
        for j, sec in enumerate(sec_list):
            # 下一节起点-1 作为本节末（最后一节落到章末；旁栏没有明确边界，用同法则）
            sec["end"] = (sec_list[j + 1]["start"] - 1) if j + 1 < len(sec_list) else ch_end
        out_chapters.append({"chapter": ch, "start": ch_start, "end": ch_end, "sections": sec_list})

    doc = {
        "ok": True,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "offset": OFFSET,
        "book": "数学 必修第一册（人教A版2019课标版）",
        "printed_first": 1,
        "printed_last": printed_last,
        "physical_pages": total_phys,
        "chapters": out_chapters,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"写出 {OUT}")
    print(f"全书: 印刷 p1..p{printed_last}（物理 {total_phys} 页, offset {OFFSET}）")
    for c in out_chapters:
        print(f"  {c['chapter']}  p{c['start']}–p{c['end']}  ({len(c['sections'])} 节)")
        for sec in c["sections"][:3]:
            print(f"      {sec['section']} {sec['heading']}  p{sec['start']}–p{sec['end']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
