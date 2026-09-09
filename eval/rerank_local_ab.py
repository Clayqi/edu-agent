# -*- coding: utf-8 -*-
import sys, json, time
sys.path.insert(0, "src")
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from edu_agent.retrieve import retrieve
from sentence_transformers import CrossEncoder

data = json.loads((Path("eval") / "golden_questions.json").read_text(encoding="utf-8"))
gg = data["questions"]

def expect(h, e):
    return h.metadata.get("chapter") == e["chapter"] and str(h.metadata.get("section", "")).startswith(e["section"])

def metr(runs):
    rec = mrr = 0.0
    for qs, e in runs:
        rk = next((r for r, h in enumerate(qs, 1) if expect(h, e)), None)
        rec += int(rk is not None)
        if rk: mrr += 1.0 / rk
    return int(rec), round(mrr / len(runs), 3)

# A: 生产默认（rerank OFF）
A = [(retrieve(x["q"], top_k=3), x["expect"]) for x in gg]

# B: 生产路径 rerank ON（retrieve 默认 top3 池内 rerank）
import os
os.environ["RERANK_ON"] = "1"
B = [(retrieve(x["q"], top_k=3), x["expect"]) for x in gg]

# C: 池10 -> rerank -> top3（上限）
print("加载本地 reranker ...", flush=True)
t0 = time.time()
rm = CrossEncoder("model_cache/bge-reranker-v2-m3")
print("模型就绪 %.0fs" % (time.time() - t0), flush=True)
C = []
for x in gg:
    pool = retrieve(x["q"], top_k=10)
    pairs = [[x["q"], h.text[:800]] for h in pool]
    sc = rm.predict(pairs)
    C.append(([h for h, _ in sorted(zip(pool, sc), key=lambda z: z[1], reverse=True)][:3], x["expect"]))

print("A 默认(off):     Recall@3=%d/15 MRR=%s" % metr(A))
print("B 生产 rerank ON: Recall@3=%d/15 MRR=%s" % metr(B))
print("C 池10+rerank:    Recall@3=%d/15 MRR=%s" % metr(C))
txt = ["A off: %s" % (metr(A),), "B on(prod): %s" % (metr(B),), "C pool10+rerank: %s" % (metr(C),)]
(Path("eval") / "rerank_local_ab.txt").write_text("\n".join(txt), encoding="utf-8")
