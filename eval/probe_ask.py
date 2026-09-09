# -*- coding: utf-8 -*-
"""S7/S8 探测：ask() 合法性 + 引用 + 越界降级。"""
import json, sys
sys.path.insert(0, "src")
sys.stdout.reconfigure(encoding="utf-8")

from edu_agent.generate import ask
from edu_agent.grounded import validate

qs = [
    "函数的单调性怎么判断？",
    "集合的含义是什么？并集怎么定义？",
    "正弦函数、余弦函数的图象与性质有哪些？",
    "计算不定积分 ∫x^2 dx（大学内容，越界题）",
]
for q in qs:
    print("\n" + "=" * 70)
    print("Q:", q)
    try:
        rec = ask(q)
    except Exception as e:
        print("!! ask 异常:", type(e).__name__, e)
        continue
    issues = validate(rec)
    print("--- answer_md ---")
    print(rec.answer_md[:600])
    print(f"coverage={rec.coverage} conf={rec.confidence:.2f} citations={len(rec.citations)} issues={issues}")
    for c in rec.citations[:3]:
        print(f"   [{c.index}] {c.chapter} {c.section} {c.heading} p{c.page} | q={c.quote[:50]!r}")
