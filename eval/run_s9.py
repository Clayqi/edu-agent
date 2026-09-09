# -*- coding: utf-8 -*-
"""S9：15 条概念题全量跑 ask()，质检引用/覆盖/是否误降级。"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, "src")
sys.stdout.reconfigure(encoding="utf-8")

from edu_agent.generate import ask
from edu_agent.grounded import validate

data = json.loads((Path(__file__).parent / "golden_questions.json").read_text(encoding="utf-8"))
qs = [it["q"] for it in data["questions"]]
out = []
t0 = time.time()
for i, q in enumerate(qs, 1):
    ta = time.time()
    try:
        rec = ask(q)
        issues = validate(rec)
        ok = bool(rec.citations) and rec.coverage in ("high", "medium") and not issues
        out.append({"q": q, "ok": ok, "coverage": rec.coverage,
                    "conf": round(rec.confidence, 2), "cites": len(rec.citations),
                    "issues": issues, "answer_len": len(rec.answer_md),
                    "degraded": rec.coverage == "low"})
        mark = "OK " if ok else "!! "
        print(f"{i:>2} {mark}{q[:26]:<28} cov={rec.coverage} cites={len(rec.citations)} issues={len(issues)} ({time.time()-ta:.0f}s)", flush=True)
    except Exception as e:
        out.append({"q": q, "ok": False, "error": f"{type(e).__name__}: {e}"})
        print(f"{i:>2} ERR {q[:26]} {type(e).__name__}: {e}", flush=True)
ok_n = sum(1 for r in out if r.get("ok"))
print(f"\n结果: {ok_n}/{len(qs)} 合格 | 总耗时 {time.time()-t0:.0f}s")
(Path(__file__).parent / "s9_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
sys.exit(0 if ok_n >= 12 else 1)
