# -*- coding: utf-8 -*-
"""Rerank A/B：候选池10 -> 无rerank(top3) vs bge-reranker精排 -> Recall@3/MRR"""
import sys, json, time
sys.path.insert(0, "src")
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from edu_agent.retrieve import retrieve

data = json.loads((Path("eval") / "golden_questions.json").read_text(encoding="utf-8"))
gg = data["questions"]

def expect(h, e):
    return h.metadata.get("chapter") == e["chapter"] and str(h.metadata.get("section", "")).startswith(e["section"])

print("加载 bge-reranker-v2-m3 ...", flush=True)
t0 = time.time()
from sentence_transformers import CrossEncoder
rm = CrossEncoder("BAAI/bge-reranker-v2-m3")
print(f"模型就绪 {time.time()-t0:.0f}s", flush=True)

base_rec = base_mrr = rk_rec = rk_mrr = 0
per = []
for x in gg:
    q = x["q"]
    pool = retrieve(q, top_k=10)
    top3 = pool[:3]
    t1 = time.time()
    pairs = [[q, h.text[:800]] for h in pool]
    scores = rm.predict(pairs)
    ranked = [h for h, _ in sorted(zip(pool, scores), key=lambda z: z[1], reverse=True)][:3]
    dt = time.time() - t1
    def rr(hs):
        return next((r for r, h in enumerate(hs, 1) if expect(h, x["expect"])), None)
    b, k = rr(top3), rr(ranked)
    base_rec += int(b is not None); base_mrr += (1.0 / b if b else 0)
    rk_rec += int(k is not None); rk_mrr += (1.0 / k if k else 0)
    hit = "OK" if (k or b) else "xx"
    imp = ("+" if k and (not b or k < b) else ("=" if k == b else ("-" if not k and b else "")))
    per.append((q[:20], b, k, f"{dt:.2f}s"))

n = len(gg)
print("\n===== 结果 =====")
print(f"基准 top3(无rerank):   Recall@3={base_rec}/{n}  MRR={base_mrr/n:.3f}")
print(f"rerank(bge-reranker): Recall@3={rk_rec}/{n}  MRR={rk_mrr/n:.3f}")
print("\n逐题(rank base -> rank rerank | rerank耗时):")
for row in per:
    print(" ", row)
out = "\n".join([
  f"rerank A/B {time.strftime(chr(37)+chr(89)+chr(45)+chr(109)+chr(45)+chr(100)+chr(32)+chr(37)+chr(72)+chr(58)+chr(37)+chr(77))}",
  f"基准: Recall@3={base_rec}/{n} MRR={base_mrr/n:.3f}",
  f"rerank: Recall@3={rk_rec}/{n} MRR={rk_mrr/n:.3f}",
])
(Path("eval") / "rerank_ab.txt").write_text(out, encoding="utf-8")
print("\n已存 eval/rerank_ab.txt")
