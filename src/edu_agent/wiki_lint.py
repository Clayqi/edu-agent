# -*- coding: utf-8 -*-
"""wiki_lint.py —— 知识库自检（SCHEMA.md 第六节的校验规则）

为什么必须有它：git diff 只说明"变了什么"，不说明"变对了没有"。commit 前的闸门就是这条。
用法：
    python -m edu_agent.wiki_lint              # 检查 content/wiki/
    python -m edu_agent.wiki_lint --json       # 机器可读输出
退出码：0 = 无 ERROR（WARN 不算失败）；1 = 有 ERROR。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIKI = ROOT / "content" / "wiki"
CONCEPTS = WIKI / "concepts"

REQUIRED = ["title", "slug", "created", "updated", "type", "tags", "book", "sources", "pages", "confidence"]
TAGS = {
    "集合", "逻辑", "不等式", "函数", "指数", "对数", "三角函数",
    "单调性", "奇偶性", "对称性", "周期性", "最值", "定义域", "值域",
    "公式", "图象", "定义", "例题", "易错点", "课本", "课标", "外部资料",
}
LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
PAGE_RE = re.compile(r"\^\[p(\d+)(?:\s*[-–]\s*(\d+))?\]")
FW_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.S)
PENDING_FILE = "pending.md"


def pending_set(wiki: Path) -> set:
    """待学概念清单（由 wiki_build 自动维护）。

    设计取舍：指向"还没学到的前置概念"（如 [[函数]]）**不算断链**——那是学习进度，不是错误。
    真正的断链是"指向一个连清单里都没有的名字"。这样 lint 才不会被进度问题刷屏。
    """
    f = wiki / PENDING_FILE
    if not f.exists():
        return set()
    return {m.strip() for m in LINK_RE.findall(f.read_text(encoding="utf-8", errors="replace"))}


def parse_fm(text: str) -> tuple[dict, str]:
    """极简 YAML frontmatter 解析（只支持 scalar 与 [a, b] 列表，够用不引依赖）。"""
    m = FW_RE.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            fm[k.strip()] = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
        elif v in ("null", "~", ""):
            fm[k.strip()] = None
        else:
            fm[k.strip()] = v.strip("'\"")
    return fm, text[m.end():]


def lint(wiki: Path = WIKI) -> dict:
    pages = sorted((wiki / "concepts").glob("*.md")) if (wiki / "concepts").exists() else []
    errors, warns, infos = [], [], []
    slugs, outbound, meta = set(), {}, {}
    bodies = {}

    for p in pages:
        raw = p.read_text(encoding="utf-8", errors="replace")
        fm, body = parse_fm(raw)
        slug = fm.get("slug") or p.stem
        slugs.add(slug)
        meta[slug] = fm
        bodies[slug] = body
        links = [x.strip() for x in LINK_RE.findall(body)]
        outbound[slug] = links

        if not fm:
            errors.append(f"{p.name}: 缺 frontmatter")
            continue
        missing = [k for k in REQUIRED if k not in fm]
        if missing:
            errors.append(f"{p.name}: frontmatter 缺字段 {missing}")
        bad_tags = [t for t in (fm.get("tags") or []) if t not in TAGS]
        if bad_tags:
            errors.append(f"{p.name}: 标签不在 SCHEMA 标签表内 {bad_tags}")
        if len(links) < 2:
            errors.append(f"{p.name}: 出链只有 {len(links)} 条（SCHEMA 要求 ≥2）")
        if not PAGE_RE.search(body):
            errors.append(f"{p.name}: 正文没有段级溯源 ^[pXX]")
        if fm.get("confidence") == "high" and "（归纳，非原文）" in body:
            errors.append(f"{p.name}: confidence=high 但含「（归纳，非原文）」小节")
        if fm.get("confidence") in ("low", "medium"):
            warns.append(f"{p.name}: confidence={fm.get('confidence')}（需人工过一眼）")
        if fm.get("contradictions"):
            warns.append(f"{p.name}: 声明了冲突 {fm.get('contradictions')}，需裁决")

    # 断链 / 孤儿（指向"待学概念"的只算 WARN，见 pending.md）
    pend = pending_set(wiki)
    for slug, links in outbound.items():
        for l in links:
            if l in slugs or (WIKI / "examples" / f"{l}.md").exists():
                continue
            if l in pend:
                warns.append(f"{slug}: [[{l}]] 是**待学概念**（在 pending.md 里，不算断链）")
            else:
                errors.append(f"{slug}: 断链 [[{l}]]（既没有页面，也不在 pending.md）")
    inbound = {s: 0 for s in slugs}
    for slug, links in outbound.items():
        for l in links:
            if l in inbound and l != slug:
                inbound[l] += 1
    for slug, n in inbound.items():
        if n == 0 and len(slugs) > 1:
            warns.append(f"{slug}: 孤儿页（没有任何入链）")

    # 索引一致性
    idx = (wiki / "index.md").read_text(encoding="utf-8", errors="replace") if (wiki / "index.md").exists() else ""
    for slug in slugs:
        if f"[[{slug}]]" not in idx:
            warns.append(f"{slug}: 未出现在 index.md 里")

    return {
        "pages": len(pages), "slugs": sorted(slugs),
        "errors": errors, "warns": warns, "infos": infos,
        "ok": not errors,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--wiki", default=str(WIKI))
    a = ap.parse_args()
    r = lint(Path(a.wiki))
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"wiki_lint: {r['pages']} 页 | ERROR {len(r['errors'])} | WARN {len(r['warns'])}")
        for e in r["errors"]:
            print("  [ERROR]", e)
        for w in r["warns"]:
            print("  [WARN ]", w)
        print("结论:", "通过（无 ERROR）" if r["ok"] else "不通过，先修 ERROR")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
