# -*- coding: utf-8 -*-
"""PPT 优化真机验收（一条命令跑完，可复跑）。

跑什么：
  1. **体检** ppt-master 的 intake + 台账（页数 / 字体 / 字号层级 / 密度）
  2. **优化** 统一字体 + 统一字号层级 + 清动画（保守原地统一）
  3. **内容零丢失校验** ppt-master 的 `beautify_inventory.py --verify`（逐页逐串）
  4. **包完整性深检** 自己再做一遍独立核查：zip 结构 / python-pptx 能否重开 / 页数与形状数 /
     文字多重集是否与源稿一致 / 字体是否真的换成目标字体（含 `<a:ea>`）/ `p:timing` 是否清干净
  5. **（可选）WPS 真打开** `--with-wps`：走 wps-office MCP 让 WPS 真的加载优化稿
  6. **没碰 content/plans** 前后目录清单一致

用法（先「启动」，即 5174 与 WPS 可用）：
    .venv\\Scripts\\python.exe tools\\ppt_acceptance.py
    .venv\\Scripts\\python.exe tools\\ppt_acceptance.py --file "D:\\我的答辩稿.pptx" --with-wps
"""
from __future__ import annotations

import argparse
import collections
import sys
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from edu_agent import ppt_polish  # noqa: E402

DEFAULT_SAMPLE = _ROOT / "content" / "plans" / "完整课时模板（默认）.pptx"
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, extra: str = "") -> bool:
    RESULTS.append((name, bool(ok), extra))
    print(f"  {'✅' if ok else '❌'} {name}" + (f"  {extra}" if extra else ""))
    return bool(ok)


def text_multiset(path: Path) -> collections.Counter:
    """把一份 pptx 里所有可见文字收集成多重集（验"内容没多没少"）。"""
    from pptx import Presentation

    out: collections.Counter = collections.Counter()
    prs = Presentation(str(path))
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        t = (run.text or "").strip()
                        if t:
                            out[t] += 1
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        t = (cell.text or "").strip()
                        if t:
                            out[t] += 1
    return out


def deep_package_check(src: Path, dst: Path, *, latin: str, ea: str) -> None:
    """独立核查优化稿：结构、页数、文字、字体、动画。"""
    from pptx import Presentation

    with zipfile.ZipFile(dst) as z:
        bad = z.testzip()
        names = set(z.namelist())
        slides = sorted(n for n in names if n.startswith("ppt/slides/slide"))
        slide_xml = [z.read(n).decode("utf-8", "replace") for n in slides]
    check("zip 结构完好（testzip 无坏项）", bad is None, f"坏项={bad}")
    check("必要部件齐全", {"[Content_Types].xml", "ppt/presentation.xml"} <= names)
    check("有 slide 部件", len(slides) > 0, f"{len(slides)} 个")

    a, b = Presentation(str(src)), Presentation(str(dst))
    check("页数一致", len(a.slides.__iter__.__self__._sldIdLst) == len(b.slides.__iter__.__self__._sldIdLst),  # noqa: SLF001
          f"{len(a.slides._sldIdLst)} 页")  # noqa: SLF001
    ta, tb = text_multiset(src), text_multiset(dst)
    check("文字多重集与源稿一致（没多没少）", ta == tb,
          f"源 {sum(ta.values())} 段 / 优化后 {sum(tb.values())} 段")

    fonts, ea_hits = set(), 0
    for slide in b.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if (run.text or "").strip():
                        fonts.add(run.font.name)
    xml = "".join(slide_xml)
    ea_hits = xml.count(f'<a:ea typeface="{ea}"')
    check("西文字体已统一", fonts == {latin}, f"实际 {sorted(x for x in fonts if x)}")
    check(f"中文字体已写进 <a:ea>（{ea}）", ea_hits > 0, f"{ea_hits} 处")
    check("动画节点已清（无 p:timing）", "<p:timing" not in xml)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT_SAMPLE), help="要验收的 .pptx（默认用仓库样例）")
    ap.add_argument("--with-wps", action="store_true", help="额外让 WPS 真打开一次（需要 WPS 可用）")
    ap.add_argument("--keep", action="store_true", help="保留任务目录（默认保留，便于人工看产物）")
    ap.add_argument("--ea", default="微软雅黑")
    ap.add_argument("--latin", default="Calibri")
    args = ap.parse_args()

    src = Path(args.file)
    print("PPT 优化真机验收")
    print("  源文件:", src)
    if not src.is_file():
        print("  ❌ 源文件不存在")
        return 2

    st = ppt_polish.status()
    print("\n[0] 安装自检")
    check("ppt-master 就绪", st.get("intake_ready"), f"commit={st.get('commit')} root={st.get('root')}")
    if not st.get("intake_ready"):
        print("\n  提示：跑 deploy/setup_ppt_master.cmd，或设 PPT_MASTER_HOME")
        return 2

    plans = _ROOT / "content" / "plans"
    before = {p.name for p in plans.glob("*")} if plans.is_dir() else set()

    job = ppt_polish.new_job(src)
    print(f"\n[1] 体检（任务 {job['job_id']}）")
    rep = ppt_polish.intake(job)
    check("体检成功", rep.get("ok"), str(rep.get("error") or ""))
    if not rep.get("ok"):
        return 1
    t, tot, fl = rep.get("theme") or {}, rep.get("totals") or {}, rep.get("flags") or {}
    print(f"       {rep.get('slides')} 页 · {tot.get('chars')} 字 · 主题字体 {t.get('title_font')}/{t.get('body_font')}"
          f" · 字号层级 {(t.get('body_levels') or [])[:5]}")
    print(f"       对象：表 {tot.get('tables')} 图 {tot.get('charts')} 图示 {tot.get('diagrams')} 图片 {tot.get('images')}"
          f" · 需留意：稀疏 {fl.get('sparse_pages')} 密集 {fl.get('dense_pages')} 待确认 {fl.get('needs_confirmation')}")

    print("\n[2] 优化（统一字体 + 字号层级 + 清动画）")
    pol = ppt_polish.polish(job, ["font", "size", "strip-anim"], target_ea=args.ea, target_latin=args.latin)
    check("优化成功", pol.get("ok"), str(pol.get("error") or ""))
    if not pol.get("ok"):
        return 1
    for a in pol.get("applied", []):
        print(f"       {a.get('label')}: " + ", ".join(f"{k}={v}" for k, v in a.items()
                                                       if k not in ("action", "label") and not isinstance(v, list)))
    out = Path(pol["file"])

    print("\n[3] 内容零丢失校验（ppt-master --verify）")
    v = ppt_polish.verify(job, out)
    check("逐页逐串都在", v.get("ok"), (v.get("detail") or "").splitlines()[-1][:80] if v.get("detail") else "")

    print("\n[4] 包完整性深检（独立核查）")
    deep_package_check(src, out, latin=args.latin, ea=args.ea)

    if args.with_wps:
        print("\n[5] WPS 真打开")
        try:
            from edu_agent import mcp_tools

            r = mcp_tools.call_tool("wps-office", "wps_ppt_open_presentation", {"filePath": str(out)}, timeout=120)
            check("WPS 打开了优化稿", bool(r), str(r)[:120])
        except Exception as e:  # noqa: BLE001
            check("WPS 打开了优化稿", False, f"{type(e).__name__}: {e}")

    print("\n[6] 没碰 content/plans")
    after = {p.name for p in plans.glob("*")} if plans.is_dir() else set()
    check("目录清单前后一致", before == after, f"{len(before)} 项")

    print(f"\n产物：{out}")
    print(f"任务目录：{job['dir']}")
    ok = sum(1 for _, o, _ in RESULTS if o)
    print(f"\n结果：{ok}/{len(RESULTS)} 项通过")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
