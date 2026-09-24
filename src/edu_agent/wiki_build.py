# -*- coding: utf-8 -*-
"""wiki_build.py —— 把教材的「一节」学成 wiki 概念页（Phase 1 管道）

对齐《教育agent-知识库学习内化方案-LLMWiki-2026-09-22.md》第五节的六步：
  ① 分节  给定物理页范围（本次学哪一节）
  ② 读图  每页渲成 PNG → 视觉模型抽取结构（定义/公式/图/边栏/例题/表格）
  ③ 抽公式 视觉模型直接给 LaTeX；再与 PDF 文字层规范化比对，冲突单独记下来（不覆盖、不猜）
  ④ 抽例题 题干/步骤/答案 结构化
  ⑤ 写概念页 按 content/wiki/SCHEMA.md 模板生成，**段级 ^[pXX] 溯源**
  ⑥ 建索引 写 content/wiki/concepts/*.md、更新 index.md、追加 log.md

用法：
  python -m edu_agent.wiki_build --pages 88-91 --section 3.2.2 --title 函数的奇偶性
  python -m edu_agent.wiki_build --pages 88-91 --no-assemble     # 只跑到"读图+抽公式"，看每页结构
  python -m edu_agent.wiki_build --pages 88-91 --dry-run         # 不写任何文件

缓存：data/wiki_raw/_cache/p<物理页>.json（有缓存就不再花钱重跑；删掉即重学）
三层落地位置见 SCHEMA.md：原文/图/例题 → data/wiki_raw/（不入库）；概念页/索引/规则 → content/wiki/（入库）
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env"
WIKI = ROOT / "content" / "wiki"
RAW = ROOT / "data" / "wiki_raw"
CACHE = RAW / "_cache"

# ---------------------------------------------------------------- 配置 / HTTP

def load_env() -> dict:
    kv = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                kv[k.strip()] = v.strip().strip('"').strip("'")
    return kv


CFG = load_env()
API_BASE = (CFG.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1").rstrip("/")
API_KEY = CFG.get("DEEPSEEK_API_KEY") or ""
MODEL = CFG.get("DEEPSEEK_MODEL") or "deepseek-v4-flash"
PDF = CFG.get("TEXTBOOK_PDF") or ""   # 仓库规则：禁盘符绝对路径 → 只从 .env 取，不写默认值
BOOK = "必修第一册"
PAGE_OFFSET = 6          # 本书：物理页 = 书页 + 6

USAGE = {"prompt": 0, "completion": 0, "reasoning": 0, "calls": 0}
LAST = {}          # 最近一次调用的 finish_reason / usage，用于诊断"正文为空"这类问题


def chat(messages: list, max_tokens: int = 6000, timeout: int = 300) -> str:
    """一次对话调用。DeepSeek 是思考型模型 → max_tokens 必须给足（低于 ~2000 正文会空）。

    实测：思考 token 先扣，预算不够时 finish_reason=length 且 content 为空。
    """
    import urllib.request
    if not API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 没配（.env）")
    body = json.dumps({"model": MODEL, "max_tokens": max_tokens, "messages": messages}).encode()
    req = urllib.request.Request(API_BASE + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + API_KEY})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    u = d.get("usage") or {}
    USAGE["prompt"] += u.get("prompt_tokens", 0)
    USAGE["completion"] += u.get("completion_tokens", 0)
    USAGE["reasoning"] += (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
    USAGE["calls"] += 1
    ch = d["choices"][0]
    LAST.clear()
    LAST.update({"finish_reason": ch.get("finish_reason"), "max_tokens": max_tokens,
                 "reasoning": (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0),
                 "completion": u.get("completion_tokens", 0)})
    return ch["message"].get("content") or ""


def parse_json(text: str):
    """从模型回复里抠出第一个 JSON 对象/数组（容忍 ```json 围栏与前后废话）。

    用括号配平扫描而不是"逐前缀试 json.loads"——后者对 20KB 回复是 O(n²)，会卡死。
    """
    if not text:
        return None
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    starts = [i for i, ch in enumerate(t) if ch in "[{"]
    for s in starts:
        pairs = {"[": "]", "{": "}"}
        stack, in_str, esc = [], False, False
        for i in range(s, len(t)):
            ch = t[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch in pairs:
                stack.append(pairs[ch])
            elif stack and ch == stack[-1]:
                stack.pop()
                if not stack:
                    try:
                        return json.loads(t[s:i + 1])
                    except Exception:
                        break
    return None


# ---------------------------------------------------------------- ① 分节 / 页面渲染

def render_page(doc, page: int, dpi: int, outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / (f"p{page}.png")
    if not out.exists():
        out.write_bytes(doc[page].get_pixmap(dpi=dpi).tobytes("png"))
    return out


# ---------------------------------------------------------------- ③ 文字层（比对基准）

FW = str.maketrans({
    "犳": "f", "狓": "x", "犵": "g", "犐": "I", "犚": "R", "犕": "M", "犪": "a", "犫": "b",
    "－": "-", "＋": "+", "＝": "=", "（": "(", "）": ")", "，": ",", "．": ".", "：": ":",
    "１": "1", "２": "2", "３": "3", "４": "4", "５": "5", "６": "6", "７": "7", "８": "8",
    "９": "9", "０": "0",
})


def norm_math(s: str) -> str:
    """把文字层的怪字符规范化，便于和模型给的 LaTeX 做数字/字母级比对。"""
    s = (s or "").translate(FW)
    s = re.sub(r"[\s\u3000]+", "", s)
    s = re.sub(r"[}{\\$^_]", "", s)
    return s


def text_layer(doc, page: int) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"text-p{page}.txt"
    if f.exists():
        return f.read_text(encoding="utf-8")
    t = doc[page].get_text()
    f.write_text(t, encoding="utf-8")
    return t


def cross_check(formulas: list, text: str) -> list:
    """公式双通道核对（视觉 vs 文字层）：数字序列对不上就记冲突，不自动改。"""
    tn = norm_math(text)
    conflicts = []
    for f in formulas or []:
        latex = (f or {}).get("latex") if isinstance(f, dict) else str(f)
        if not latex:
            continue
        ln = norm_math(latex)
        digits = re.sub(r"[^0-9]", "", ln)
        if digits and digits not in tn:
            # 退一步：单个数字都在文字层出现，只是顺序/粘连不同 → 只算"需看"不算"冲突"
            if all(d in tn for d in set(digits)):
                conflicts.append({"latex": latex, "level": "look",
                                  "note": "数字都出现过但串不连续（多为公式粘连/分数排版所致，需人工看原页）"})
            else:
                conflicts.append({"latex": latex, "level": "conflict",
                                  "note": "文字层里找不到这些数字，可能是视觉模型读错"})
    return conflicts


# ---------------------------------------------------------------- ② 读图

VISION_PROMPT = """你是高中数学教材（人教A版必修一）的校对助手。下面给你这一页的扫描图，只描述你**实际看到**的内容。

只输出一个 JSON（不要解释、不要 markdown 围栏），字段如下；看不清的填 null，**严禁编造**：
{
 "section_no": "本页所属小节编号，如 3.2.2（若本页是上一节延续，填该节编号）",
 "section_title": "小节标题",
 "definitions": ["教材给出的定义原文（数学符号用 LaTeX，如 f(x)=x^2+1）"],
 "formulas": [{"latex": "公式", "context": "出现在哪句话/哪道题里"}],
 "figures": [{"num": "图3.2-7", "desc": "图里画了什么：函数表达式、坐标轴范围、形状、对称性等"}],
 "tables": [{"num": "表3.2-1", "desc": "表格内容摘要"}],
 "margin_notes": ["页面两侧方框（探究/思考/旁批）里的原文"],
 "examples": [{"no": "例3", "stem": "题干", "steps": ["解题步骤"], "answer": "最终答案"}],
 "exercises": ["练习/习题题干"],
 "key_points": ["本页强调的结论"]
}"""


VISION_KEYS = ("section_no", "section_title", "definitions", "formulas", "figures",
               "tables", "margin_notes", "examples", "exercises", "key_points")
_HAS = ("definitions", "formulas", "figures", "examples", "key_points")


def _norm_vision(data) -> dict:
    """把模型返回的**任意形状**归一成 dict —— 实测它有时无视字段、返回数组甚至纯字符串。

    这是刻意的容错：学习管道不能因为一次格式漂移就整节失败。
    """
    if isinstance(data, dict):
        out = {k: data.get(k) for k in VISION_KEYS}
        if data.get("_parse"):
            out["_parse"] = data["_parse"]
        return out
    if isinstance(data, list):
        out = {k: [] for k in VISION_KEYS}
        out["section_no"] = None
        out["section_title"] = None
        for it in data:
            if isinstance(it, dict):
                for k, v in it.items():
                    if k in out and isinstance(out.get(k), list) and isinstance(v, list):
                        out[k] += v
                    elif k in out:
                        out[k] = v
            elif isinstance(it, str):
                out["definitions"].append(it)      # 纯字符串一律按"定义原文"收下
        out["_parse"] = "list-normalized"
        return out
    out = {k: None for k in VISION_KEYS}
    out["_parse"] = "failed"
    out["_raw"] = str(data)[:500]
    return out


def lst(d: dict, k: str) -> list:
    v = (d or {}).get(k)
    return v if isinstance(v, list) else ([] if v is None else [v])


def _parse_note(d: dict) -> str:
    """模型输出形状有漂移时在日志里标注（正常走 retry-ok 就不吵）。"""
    v = (d or {}).get("_parse")
    return f"[{v}] " if v and v != "retry-ok" else ""


def vision_extract(png: Path, page: int, force: bool = False) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    cf = CACHE / f"p{page}.json"
    rf = CACHE / f"p{page}.raw.txt"
    if cf.exists() and not force:
        return _norm_vision(json.loads(cf.read_text(encoding="utf-8")))

    import base64 as _b64
    b64 = _b64.b64encode(png.read_bytes()).decode()
    msg = {"role": "user", "content": [
        {"type": "text", "text": VISION_PROMPT},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}]}
    txt = chat([msg], max_tokens=6000)
    rf.write_text(txt, encoding="utf-8")
    data = _norm_vision(parse_json(txt))

    if not any(lst(data, k) for k in _HAS):        # 形状漂移 → 带图纠正重试一次
        txt2 = chat([
            {"role": "user", "content": [
                {"type": "text", "text": VISION_PROMPT},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}]},
            {"role": "assistant", "content": (txt or "")[:800]},
            {"role": "user", "content": "你上面的输出不是要求的格式。请**只输出一个 JSON 对象**"
                                        "（以 { 开头、以 } 结尾），字段齐全，不要数组、不要代码围栏、不要解释。"},
        ], max_tokens=6000)
        rf.write_text((txt or "") + "\n\n===== RETRY =====\n" + (txt2 or ""), encoding="utf-8")
        d2 = _norm_vision(parse_json(txt2))
        if any(lst(d2, k) for k in _HAS):
            data, data["_parse"] = d2, "retry-ok"
        else:
            data["_parse"] = "failed-after-retry"

    cf.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


# ---------------------------------------------------------------- ⑤ 组装概念页

ASSEMBLE_PROMPT = """你在维护一个高中数学知识库（LLM Wiki 形态）。下面给你：
【A】教材一节里**每一页的结构化抽取结果**（视觉模型读页图产出，页码 = 物理页）
【B】同一节的 PDF 文字层原文（可能有乱码/公式粘连，只作交叉核对用）
【C】知识库写作规则 SCHEMA

请**写概念页**（不是抄原文，是读懂后的讲义）。要求：
1. 只写这一节真正讲到的概念；一个概念一页；本节的量控制在 2~4 页之间
2. 每页必须符合 SCHEMA 的模板与 frontmatter 字段；`pages` 写物理页数组
3. **任何来自教材的陈述句句末标 ^[pXX]**（物理页）；你自己归纳的内容必须放进标题含「（归纳，非原文）」的小节，
   并且该页 `confidence` 只能是 medium 或 low
4. 公式只用【A】里出现过的 LaTeX，**不要自己补**；【B】和【A】不一致的地方不要擅自选一个，
   而是在页面里写一行 `> ⚠ 公式待核：…`，并列进 conflicts
5. 每页至少 2 条 `[[其他概念名]]` 出链（可以指向本节其他页或预期会有的前置概念）
6. 图象特征写【A】的 figures 描述（含图号），不要描述你没看到的东西

只输出 JSON（不要围栏）：
{
 "pages": [{"slug":"函数的奇偶性","title":"函数的奇偶性","tags":["函数","奇偶性"],
            "confidence":"high|medium|low","pages":[88,89,90,91],"body":"完整 markdown 正文（含标题行）"}],
 "conflicts": [{"item":"公式","vision":"模型读到的","text":"文字层的","page":88}],
 "index_summary": "一句话说明这次学到什么"
}"""


def assemble(section: str, page_data: dict, texts: dict, schema: str, max_tokens: int = 32000) -> dict:
    """组装概念页。预算要足：实测 12000 会被思考吃光、正文为空（finish_reason=length）。

    分级降级：32000 → 16000 → 8192；每次把原始回复落盘，便于事后诊断。
    """
    payload = {
        "A_每页结构化": {f"p{p}": d for p, d in sorted(page_data.items())},
        "B_文字层原文": {f"p{p}": re.sub(r"\s+", "", t)[:1600] for p, t in sorted(texts.items())},
        "C_SCHEMA": schema[:6000],
        "section": section,
    }
    msg = [{"role": "user", "content": ASSEMBLE_PROMPT + "\n\n" + json.dumps(payload, ensure_ascii=False)}]
    CACHE.mkdir(parents=True, exist_ok=True)
    rf = CACHE / f"_assemble-{section}.raw.txt"
    last_txt = ""
    for budget in (max_tokens, 16000, 8192):
        try:
            txt = chat(msg, max_tokens=budget, timeout=600)
        except Exception as e:                      # 预算超上限会被 API 拒绝 → 降一档
            last_txt += f"\n[budget {budget} failed] {e}\n"
            continue
        rf.write_text(last_txt + f"\n===== budget {budget} finish={LAST.get('finish_reason')} "
                                 f"reasoning={LAST.get('reasoning')} =====\n" + (txt or ""), encoding="utf-8")
        data = parse_json(txt)
        if isinstance(data, dict) and (data.get("pages") or data.get("conflicts")):
            return data
        last_txt += f"\n[budget {budget} finish={LAST.get('finish_reason')} 空或解析失败]\n" + (txt or "")[:1500]
    return {"pages": [], "conflicts": [], "_parse": "failed", "_note": "三次预算都没拿到可用 JSON，见 _assemble-*.raw.txt"}


# ---------------------------------------------------------------- ⑥ 落盘 / 索引 / 日志

def write_page(w, page: dict) -> Path:
    (WIKI / "concepts").mkdir(parents=True, exist_ok=True)
    slug = page["slug"]
    today = time.strftime("%Y-%m-%d")
    tags = ", ".join(page.get("tags") or [])
    pages = ", ".join(str(x) for x in (page.get("pages") or []))
    body = page.get("body") or ""
    body = re.sub(r"^---\r?\n.*?\r?\n---\r?\n", "", body, flags=re.S)      # 模型自己写了 frontmatter 就剥掉
    fm = (f"---\ntitle: {page.get('title') or slug}\nslug: {slug}\ncreated: {today}\nupdated: {today}\n"
          f"type: concept\ntags: [{tags}]\nbook: {BOOK}\nsources: [raw/{BOOK}/{w.section}.md]\n"
          f"pages: [{pages}]\nconfidence: {page.get('confidence') or 'medium'}\ncontradictions: []\n---\n\n")
    p = WIKI / "concepts" / f"{slug}.md"
    exist = p.exists()
    if exist:                                                               # 更新：保留 created，bump updated
        old = p.read_text(encoding="utf-8")
        m = re.search(r"^created: (.+)$", old, re.M)
        if m:
            fm = fm.replace("created: " + today, "created: " + m.group(1))
    p.write_text(fm + body.strip() + "\n", encoding="utf-8")
    w.touched.append(("update" if exist else "new", p))
    return p


def _clean_line(s: str) -> str:
    s = re.sub(r"\$\$.*?\$\$", "", s)
    s = re.sub(r"\\\(.*?\\\)", "", s)
    s = re.sub(r"\^\[p[\d\-\s,]+\]", "", s).replace("**", "")
    s = re.sub(r"[，。、；：]{2,}", "，", s)
    s = re.sub(r"（\s*）|\(\s*\)", "", s)
    return re.sub(r"\s*，\s*(?=[，。])", "", s).strip(" ，。；-* ")


def _summary_of(body: str) -> str:
    """给索引取一句摘要：**优先取「归纳/判定/步骤」这类纯文字小节**，取不到才退回定义句。

    （定义句里公式多，剥掉 LaTeX 后全是空格，做目录行不好读。）
    """
    prefer, fallback = "", ""
    in_prefer = False
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("#"):
            in_prefer = any(k in s for k in ("归纳", "判定", "步骤", "易错", "使用"))
            continue
        if not s or s[0] in ">|" or s.startswith(("- ", "* ")):
            continue
        t = _clean_line(s)
        if len(t) < 10:
            continue
        if not fallback:
            fallback = t
        if in_prefer and not prefer:
            prefer = t
            break
    return (prefer or fallback or "（尚无摘要）")[:60]


def rebuild_index(conflicts: list | None = None, pending: list | None = None):
    """按 concepts/ 现有文件重建索引（幂等）；同时把「待审核」区刷新为冲突 + 待学概念。"""
    (WIKI / "concepts").mkdir(parents=True, exist_ok=True)
    rows = []
    for p in sorted((WIKI / "concepts").glob("*.md")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        title = re.search(r"^title: (.+)$", raw, re.M)
        title = title.group(1).strip() if title else p.stem
        conf = re.search(r"^confidence: (.+)$", raw, re.M)
        body = re.sub(r"^---\r?\n.*?\r?\n---\r?\n", "", raw, flags=re.S)
        rows.append(f"- [[{title}]] — {_summary_of(body)}（confidence: {(conf.group(1).strip() if conf else '?')}）")
    idx = WIKI / "index.md"
    txt = idx.read_text(encoding="utf-8") if idx.exists() else "# Wiki Index\n\n## 概念（Concept）\n\n## 待审核（Review）\n"
    block = "\n".join(rows) if rows else "（尚未学习任何章节）"
    txt = re.sub(r"(## 概念（Concept）\n)(.*?)(\n## )", lambda m: m.group(1) + block + "\n" + m.group(3),
                 txt, flags=re.S)

    review = []
    for c in (conflicts or []):
        review.append(f"- ⚠ **公式待核（p{c.get('page')}）**：视觉读到 `{c.get('vision')}`，"
                      f"文字层是 `{c.get('text')}` → {c.get('item')}（人工看原页定夺）")
    if pending:
        review.append("- 待学概念（被引用但还没建页）：" + "、".join(f"`{x}`" for x in pending))
    if not review:
        review.append("（空）")
    txt = re.sub(r"(## 待审核（Review）\n\n>.*?\n\n)(.*?)(\n*$)",
                 lambda m: m.group(1) + "\n".join(review) + "\n", txt, flags=re.S)
    txt = re.sub(r"Last updated: \d{4}-\d{2}-\d{2}", "Last updated: " + time.strftime("%Y-%m-%d"), txt)
    txt = re.sub(r"Total pages: \d+", f"Total pages: {len(rows)}", txt)
    idx.write_text(txt, encoding="utf-8")


def update_pending() -> list:
    """把「被引用但还没建页」的概念写进 pending.md（= 下一步该学什么），返回清单。"""
    slugs = {p.stem for p in (WIKI / "concepts").glob("*.md")}
    titles = set()
    for p in (WIKI / "concepts").glob("*.md"):
        m = re.search(r"^title: (.+)$", p.read_text(encoding="utf-8", errors="replace"), re.M)
        titles.add((m.group(1).strip() if m else p.stem))
    known = slugs | titles
    miss = set()
    for p in (WIKI / "concepts").glob("*.md"):
        body = p.read_text(encoding="utf-8", errors="replace")
        miss |= {m.strip() for m in re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", body)}
    miss = sorted(miss - known - {""})
    f = WIKI / "pending.md"
    head = ("# 待学概念（Pending）\n\n"
            "> 由 `wiki_build.py` 自动维护：概念页里引用到、但知识库还没有页的概念。\n"
            "> **这不是断链**（lint 只报 WARN）；它同时是「下一步该学哪一节」的清单。\n\n")
    f.write_text(head + ("\n".join(f"- [[{x}]]" for x in miss) if miss else "（无）") + "\n", encoding="utf-8")
    return miss


def append_log(section: str, title: str, written: list, conflicts: list, secs: float):
    log = WIKI / "log.md"
    lines = [f"\n## [{time.strftime('%Y-%m-%d')}] learn | {BOOK} {section} {title}",
             f"- 物理页：{CFG.get('_pages', '')}；耗时 {secs:.0f}s；token：prompt {USAGE['prompt']} / completion {USAGE['completion']}"
             f"（其中 reasoning {USAGE['reasoning']}），共 {USAGE['calls']} 次调用",
             f"- 页面：{'；'.join(f'{a} {p.name}' for a, p in written) or '（无）'}"]
    if conflicts:
        lines.append(f"- ⚠ 公式待核 {len(conflicts)} 条：写进了页面与 index.md 的待审核区")
    else:
        lines.append("- 公式核对：视觉与文字层未见冲突")
    with log.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- main

def parse_pages(s: str) -> list:
    out = []
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-"); out += list(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def sync_vectors(verbose: bool = True) -> dict | None:
    """写完概念页后同步向量库（独立函数 → 可单测；失败只提示、不影响落盘）。

    2026-09-22 起：审核改过页面后如果忘了重同步，问答侧就会用旧内容。
    """
    try:
        from edu_agent import wiki_index

        r = wiki_index.sync(quiet=True)
        if verbose:
            print(f"      向量库自动同步：chunks={r['chunks_total']} 新增/更新={r['added']} "
                  f"删除={r['removed']} 集合总数={r['collection_count']}")
        return r
    except Exception as e:  # noqa: BLE001
        if verbose:
            print(f"      ⚠ 向量库同步失败（不影响落盘）：{type(e).__name__}: {e}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, help="物理页，如 88-91 或 88,89,90")
    ap.add_argument("--section", required=True, help="小节号，如 3.2.2")
    ap.add_argument("--title", default="", help="小节标题")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--no-assemble", action="store_true", help="只跑读图+抽公式，不写概念页")
    ap.add_argument("--dry-run", action="store_true", help="不写任何文件")
    ap.add_argument("--force-vision", action="store_true", help="忽略缓存重新读图")
    w = ap.parse_args()
    w.touched = []
    CFG["_pages"] = w.pages

    if not PDF:
        raise SystemExit("未配置教材 PDF：请在 .env 里写 TEXTBOOK_PDF=<绝对路径>"
                         "（仓库禁止写死盘符路径，所以这里不给默认值）")
    import pymupdf
    doc = pymupdf.open(PDF)
    pages = parse_pages(w.pages)
    print(f"[1/6] 分节：{BOOK} {w.section} {w.title} → 物理页 {pages[0]}~{pages[-1]}（共 {len(pages)} 页）")

    print("[2/6] 读图 + [3/6] 抽公式（视觉模型；首次跑每页约 15~60s，之后走缓存）")
    page_data, texts, all_conflicts = {}, {}, []
    for p in pages:
        png = render_page(doc, p, w.dpi, RAW / "assets" / BOOK / w.section)
        t0 = time.time()
        d = vision_extract(png, p, force=w.force_vision)
        texts[p] = text_layer(doc, p)
        page_data[p] = d
        cf = cross_check(lst(d, "formulas"), texts[p])
        all_conflicts += [dict(c, page=p) for c in cf]
        warn = f" | ⚠公式待核 {len(cf)}" if cf else ""
        print(f"      p{p}: {d.get('section_no') or '?'} {d.get('section_title') or ''} | "
              f"公式 {len(lst(d, 'formulas'))} 图 {len(lst(d, 'figures'))} "
              f"例题 {len(lst(d, 'examples'))} 边栏 {len(lst(d, 'margin_notes'))} "
              f"| {_parse_note(d)}{time.time() - t0:.0f}s{warn}")

    if w.no_assemble:
        print("[4~6/6] --no-assemble：跳过组装/落盘。token 用量:", USAGE)
        if not w.dry_run:
            (CACHE / f"_pages-{w.section}.json").write_text(
                json.dumps(page_data, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0

    print("[4/6] 抽例题 + [5/6] 写概念页（文本模型，约 1~3 分钟）")
    t0 = time.time()
    schema = (WIKI / "SCHEMA.md").read_text(encoding="utf-8")
    res = assemble(w.section, page_data, texts, schema)
    print(f"      组装完成 {time.time()-t0:.0f}s；冲突 {len(res.get('conflicts') or [])} 条；"
          f"页面 {len(res.get('pages') or [])} 页")
    if w.dry_run:
        print(json.dumps(res, ensure_ascii=False)[:1500])
        return 0

    # 例题结构化（入库到 data/wiki_raw，含原文不入 git）
    ex = []
    for p, d in page_data.items():
        for e in lst(d, "examples"):
            item = e if isinstance(e, dict) else {"stem": str(e)}
            item = dict(item, page=p, section=w.section)
            ex.append(item)
    if ex:
        ef = RAW / "examples.json"
        old = json.loads(ef.read_text(encoding="utf-8")) if ef.exists() else []
        ef.parent.mkdir(parents=True, exist_ok=True)
        ef.write_text(json.dumps(old + ex, ensure_ascii=False, indent=1), encoding="utf-8")

    for page in res.get("pages") or []:
        write_page(w, page)
    pend = update_pending()
    conflicts = res.get("conflicts") or []
    rebuild_index(conflicts=conflicts, pending=pend)
    # 概念页一改，向量库就可能过期（2026-09-22 踩到：审核改完页没重同步）→ 写完页就自动同步
    sync_vectors()
    if w.touched:
        append_log(w.section, w.title or res.get("index_summary", ""), w.touched, conflicts, 0)
    else:
        print("      ⚠ 本次没写出任何页面 → 不记学习日志（失败运行不留脏记录）")

    print("[6/6] 落盘完成：")
    for act, p in w.touched:
        print(f"      {'新增' if act == 'new' else '更新'} {p}")
    print("      index.md / log.md 已更新")
    print("token 用量:", USAGE)
    (CACHE / f"_pages-{w.section}.json").write_text(
        json.dumps({"page_data": page_data, "conflicts": all_conflicts, "assemble": res},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
