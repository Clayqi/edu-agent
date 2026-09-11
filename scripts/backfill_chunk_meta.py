"""一次性回填：给教材向量库的每个片段补 has_figure / fig_nums / fidelity 三个元数据。

背景：2026-09-10 George 报「图片公式抽不到 -> agent 幻觉」，P0 方案=
  ① 生成侧按「含图片段」注入硬指令（禁止复述/推导公式，只给页码+图号）
  ② 前端引用卡「看原页」直接贴原书页图
本脚本负责喂给①的元数据：不改文本、不改向量，只 add 三个键。

用法（在仓库根目录下执行）：
    .venv\\Scripts\\python.exe scripts\\backfill_chunk_meta.py            # 备份 + 回填
    .venv\\Scripts\\python.exe scripts\\backfill_chunk_meta.py --dry-run  # 只看统计不写库

安全：先整库备份到 data/backup/chroma-<日期>-before-meta.bak，再 update。
幂等：重复跑结果一致（纯文本派生）。
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import chromadb  # noqa: E402

from edu_agent import figdetect  # noqa: E402
from edu_agent.config import load_settings  # noqa: E402

DB = ROOT / "chroma_db"
COLLECTION = "edu_textbook"


def page_image_flags(pdf: Path | None) -> dict[int, bool]:
    """每张物理页是否含位图（1 基）。教材片段 page 是印刷页，故换算 +6。"""
    if not pdf or not Path(pdf).exists():
        return {}
    import pymupdf

    doc = pymupdf.open(str(pdf))
    try:
        return {i + 1: bool(doc[i].get_images(full=True)) for i in range(doc.page_count)}
    finally:
        doc.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只统计，不写库")
    ap.add_argument("--offset", type=int, default=6, help="印刷页 -> 物理页 偏移（教材实测 6）")
    args = ap.parse_args()

    s = load_settings()
    pdf = s.textbook_pdf
    print(f"教材 PDF: {pdf}")
    imgp = page_image_flags(pdf)
    print(f"含位图物理页: {sum(1 for v in imgp.values() if v)}/{len(imgp)}")

    client = chromadb.PersistentClient(path=str(DB))
    col = client.get_collection(COLLECTION)
    data = col.get(include=["documents", "metadatas"])
    ids, docs, metas = data["ids"], data["documents"], data["metadatas"]
    print(f"片段数: {len(ids)}")

    new_metas, stats = [], Counter()
    for cid, text, md in zip(ids, docs, metas):
        printed = md.get("page")
        phys = (int(printed) + args.offset) if printed else None
        info = figdetect.figure_info(text or "", page_has_images=bool(imgp.get(phys, False)) if phys else False)
        merged = dict(md)
        merged["has_figure"] = bool(info["has_figure"])
        merged["fig_nums"] = info["fig_nums"]
        merged["fidelity"] = info["fidelity"]
        new_metas.append(merged)
        stats["has_figure" if info["has_figure"] else "no_figure"] += 1
        stats["fidelity_low" if info["fidelity"] == "low" else "fidelity_high"] += 1
        stats["page_has_images" if info["page_has_images"] else "page_no_images"] += 1

    print("\n统计:")
    for k in ("has_figure", "no_figure", "page_has_images", "fidelity_low", "fidelity_high"):
        print(f"  {k:<18} {stats[k]}")
    sample = [(ids[i], new_metas[i].get("section"), new_metas[i].get("fig_nums"),
               new_metas[i].get("fidelity")) for i in range(len(ids))
              if new_metas[i]["fidelity"] == "low"][:6]
    print("  低保真样例(section, fig_nums, fidelity):")
    for s_ in sample:
        print(f"    - {s_}")

    if args.dry_run:
        print("\n--dry-run：未写库。")
        return 0

    bdir = ROOT / "data" / "backup"
    bdir.mkdir(parents=True, exist_ok=True)
    bak = bdir / f"chroma-{time.strftime('%Y%m%d-%H%M%S')}-before-meta.bak"
    shutil.copy2(DB / "chroma.sqlite3", bak)
    print(f"\n已备份: {bak}")

    col.update(ids=ids, metadatas=new_metas)
    got = col.get(include=["metadatas"])
    okfig = sum(1 for m in got["metadatas"] if "has_figure" in m and "fidelity" in m and "fig_nums" in m)
    print(f"回填完成：{okfig}/{len(got['metadatas'])} 条含全部三个新键")
    return 0 if okfig == len(got["metadatas"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
