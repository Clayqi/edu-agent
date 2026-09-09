# -*- coding: utf-8 -*-
"""S10 排练 + 裸 GPT 对照（问答为主）。

1) 演示题组真实跑一遍（计时），全量答案存档 -> eval/demo_canned_answers.md
2) 其中 5 题做「有教材库 vs 裸 DeepSeek」对照存档 -> eval/s10_naked_compare.md
"""
import sys, time
from pathlib import Path
sys.path.insert(0, "src")
sys.stdout.reconfigure(encoding="utf-8")

from edu_agent.generate import ask
from edu_agent.config import get_chat_llm

DEMO = [
    "集合的含义是什么？集合中的元素有哪些特性？",
    "并集、交集、补集分别是怎样定义的？",
    "什么是充分条件、必要条件和充要条件？",
    "基本不等式是什么？什么时候取等号？",
    "函数的概念是什么？什么是定义域和值域？",
    "怎么判断一个函数在某区间上的单调性？",
    "正弦函数、余弦函数的图象与性质有哪些？",
    "计算不定积分 ∫x^2 dx（越界题，验证降级）",
]
NAKED = DEMO[:5] + [DEMO[5]]
EVAL = Path(__file__).parent

# ---------- 1) 排练：8 题全跑（计时 + 答案存档） ----------
canned = ["# 演示备用答案存档（预跑自录，现场兜底）\n"]
times = []
for i, q in enumerate(DEMO, 1):
    ta = time.time()
    rec = ask(q)
    dt = time.time() - ta
    times.append((q, dt, rec.coverage))
    canned.append(f"\n## {i}. Q：{q}\n")
    canned.append(f"> 端到端 {dt:.1f}s ｜ coverage={rec.coverage} conf={rec.confidence:.2f}\n")
    canned.append(rec.answer_md)
    if rec.citations:
        canned.append("\n**引用：**")
        for c in rec.citations[:4]:
            loc = f"{c.chapter} {c.section or ''} {c.heading or ''}".strip()
            canned.append(f"- [{c.index}] {loc} ｜ p{c.page} ｜ {c.quote[:80]}")
    print(f"{i:>2} {dt:5.1f}s cov={rec.coverage} cites={len(rec.citations)} {q[:24]}", flush=True)
(EVAL / "demo_canned_answers.md").write_text("\n".join(canned), encoding="utf-8")
print("\n时间: " + ", ".join(f"{dt:.0f}s" for _, dt, _ in times))

# ---------- 2) 裸 GPT 对照（前 6 题） ----------
sys_p = "你是高中老师，请直接、清晰地回答学生的问题。"
out = ["# 对照实验：教材库 RAG vs 裸 DeepSeek（同模型 deepseek-v4-flash）\n",
       "> 意义：演示 RAG 的价值——同样的问题，有教材库的版本带 [编号] 引用与页码、且不越界硬编；裸模型无坐标、无边界。\n"]
llm = get_chat_llm()
for q in NAKED:
    out.append(f"\n## Q：{q}\n")
    rec = ask(q)
    out.append("### ① 课本教练（有教材库）\n")
    out.append(rec.answer_md[:800])
    out.append("\n")
    if rec.citations:
        loc = f"{rec.citations[0].chapter} {rec.citations[0].section or ''} {rec.citations[0].heading or ''}"
        out.append(f"- 引用示例：{loc} p{rec.citations[0].page}\n")
    naked = (llm.invoke([{"role": "system", "content": sys_p}, {"role": "user", "content": q}]).content or "")
    out.append("\n### ② 裸 DeepSeek（无教材库）\n")
    out.append(naked[:800])
    out.append("\n---\n")
    print("compare done:", q[:20], flush=True)
(EVAL / "s10_naked_compare.md").write_text("\n".join(out), encoding="utf-8")
print("\n存档：demo_canned_answers.md / s10_naked_compare.md")
