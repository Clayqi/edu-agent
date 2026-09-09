# -*- coding: utf-8 -*-
"""S6 检索冒烟：golden 15 题 -> top3 命中期望 章/节。

判据：期望 chapter+section 出现在任一 top3 结果的 metadata。
达标线：>=12/15。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from edu_agent.retrieve import retrieve  # noqa: E402

data = json.loads((Path(__file__).parent / "golden_questions.json").read_text(encoding="utf-8"))
qs = data["questions"]

def _is_expect(h, exp):
    return h.metadata.get("chapter") == exp["chapter"] and str(h.metadata.get("section", "")).startswith(exp["section"])


ok = 0
rr_sum = 0.0
rows = []
for i, item in enumerate(qs, 1):
    hits = retrieve(item["q"], top_k=3)
    rank = next((r for r, h in enumerate(hits, 1) if _is_expect(h, item["expect"])), None)
    hit = rank is not None
    ok += int(hit)
    if rank:
        rr_sum += 1.0 / rank
    top = f"{hits[0].metadata.get('chapter')} {hits[0].metadata.get('section','')} {hits[0].metadata.get('heading','')}(p{hits[0].metadata.get('page')})" if hits else "-"
    rows.append((i, "✅" if hit else "❌", item["q"][:26], top))

for i, mark, q, top in rows:
    print(f"{i:>2} {mark} {q:<28} -> {top}")
print(f"\nRecall@3 = {ok}/{len(qs)}   MRR = {rr_sum / len(qs):.3f}   (达标线 Recall >= {int(len(qs) * 0.8)})")
sys.exit(0 if ok >= int(len(qs) * 0.8) else 1)
