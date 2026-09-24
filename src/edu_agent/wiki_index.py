# -*- coding: utf-8 -*-
"""wiki_index.py —— 把概念页写进向量库（chroma 集合 `edu_wiki`），供问答侧检索。

与教材库分开：`edu_textbook` = **原文**切块；`edu_wiki` = **学会之后的知识**（概念页）。
切块粒度 = 概念页的每个 `## 小节`（比整页召回准，也便于回答里带小节名）。
embedding = 本机 ollama `bge-m3`（与教材库同源），不引入新依赖。

幂等：按 chunk 文本 sha1 比对，内容没变就不重复写（也不会重复花钱建向量）。
集合名与教材库不同 → 互不影响；删集合即回退。

用法：
  PYTHONPATH=src python -m edu_agent.wiki_index --rebuild          # 全量重建（先删集合同名集合）
  PYTHONPATH=src python -m edu_agent.wiki_index                    # 增量同步（默认）
  PYTHONPATH=src python -m edu_agent.wiki_index --stats
  PYTHONPATH=src python -m edu_agent.wiki_index --query "怎么判断奇偶性" -k 3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIKI = ROOT / "content" / "wiki"
COLLECTION = "edu_wiki"


def load_env() -> dict:
    kv = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                kv[k.strip()] = v.strip().strip('"').strip("'")
    return kv


CFG = load_env()
OLLAMA = (CFG.get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
EMBED_MODEL = CFG.get("EMBEDDING_MODEL") or "bge-m3"
CHROMA_DIR = str(ROOT / (CFG.get("CHROMA_DB_DIR") or "chroma_db"))


# ---------------------------------------------------------------- 切块

def _fm(text: str) -> dict:
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                v = v.strip()
                if v.startswith("[") and v.endswith("]"):
                    fm[k.strip()] = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
                else:
                    fm[k.strip()] = v.strip("'\"")
    return fm


def chunks_of(path: Path) -> list[dict]:
    """一个概念页 → 若干 chunk（按 ## 小节切，小节前的内容并入第一个 chunk）。"""
    raw = path.read_text(encoding="utf-8", errors="replace")
    fm = _fm(raw)
    body = re.sub(r"^---\r?\n.*?\r?\n---\r?\n", "", raw, flags=re.S).strip()
    slug = fm.get("slug") or path.stem
    title = fm.get("title") or slug
    parts = re.split(r"^##\s+", body, flags=re.M)
    out = []
    for i, p in enumerate(parts):
        p = p.strip()
        if not p:
            continue
        sec = p.splitlines()[0].strip() if i > 0 else "概述"
        text = (p if i > 0 else p)
        text = f"{title} · {sec}\n{text}"
        if len(text.strip()) < 12:
            continue
        out.append({
            "id": f"{slug}--{hashlib.sha1(sec.encode('utf-8')).hexdigest()[:8]}",
            "text": text,
            "meta": {
                "slug": slug, "title": title, "section": sec,
                "pages": ",".join(str(x) for x in (fm.get("pages") or [])),
                "confidence": fm.get("confidence") or "",
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha1": hashlib.sha1(text.encode("utf-8")).hexdigest(),
            },
        })
    return out


# ---------------------------------------------------------------- embedding / chroma

def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    body = json.dumps({"model": EMBED_MODEL, "input": texts}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/embed", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read())
    return d.get("embeddings") or []


def client():
    import chromadb
    return chromadb.PersistentClient(path=CHROMA_DIR)


def get_col(rebuild: bool = False):
    cl = client()
    if rebuild:
        try:
            cl.delete_collection(COLLECTION)
        except Exception:
            pass
    return cl.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


# ---------------------------------------------------------------- 同步 / 查询

def sync(rebuild: bool = False, quiet: bool = False) -> dict:
    col = get_col(rebuild)
    files = sorted((WIKI / "concepts").glob("*.md"))
    all_chunks = [c for f in files for c in chunks_of(f)]
    existing = {}
    if not rebuild and col.count():
        got = col.get(include=["metadatas"])
        existing = {i: (m or {}).get("sha1") for i, m in zip(got["ids"], got["metadatas"])}

    todo = [c for c in all_chunks if existing.get(c["id"]) != c["meta"]["sha1"]]
    removed = [i for i in existing if i not in {c["id"] for c in all_chunks}]
    if removed:
        col.delete(ids=removed)
    added = 0
    for i in range(0, len(todo), 16):
        batch = todo[i:i + 16]
        vecs = embed([c["text"] for c in batch])
        if len(vecs) != len(batch):
            raise RuntimeError("embedding 数量不匹配（ollama 未启动？）")
        col.add(ids=[c["id"] for c in batch], documents=[c["text"] for c in batch],
                embeddings=vecs, metadatas=[c["meta"] for c in batch])
        added += len(batch)
    r = {"pages": len(files), "chunks_total": len(all_chunks), "added": added,
         "removed": len(removed), "collection_count": col.count()}
    if not quiet:
        print(json.dumps(r, ensure_ascii=False))
    return r


def search(query: str, k: int = 3) -> list[dict]:
    """给问答侧用：返回最相关的 wiki 小节（失败返回空列表，绝不影响主链路）。"""
    try:
        col = get_col()
        if not col.count():
            return []
        v = embed([query])
        if not v:
            return []
        res = col.query(query_embeddings=[v[0]], n_results=max(1, k),
                        include=["documents", "metadatas", "distances"])
        out = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            out.append({"text": doc, "meta": meta, "distance": dist, "score": 1 - dist})
        return out
    except Exception:
        return []


WIKI_HEADER = ("【知识库 · 已学会的讲义（比原文更优先引用；回答里请写 [[页面名]] 并保留页码溯源）】")


def prompt_block(query: str, k: int = 2, max_chars: int = 1400) -> str:
    """问答侧注入用：把最相关的 wiki 小节拼成一段前缀。

    设计要点：① **任何异常都返回空串**（外部/边角能力不能拖垮主链路，与 mcp_tools/skills_local 同一哲学）；
    ② 有长度上限，避免把 prompt 撑爆（学习成果进上下文要克制）；
    ③ 带上 [[页面名]] 与页码，让回答可溯源、可回链。
    """
    try:
        hits = search(query, k)
        if not hits:
            return ""
        parts, used = [], 0
        for h in hits:
            m = h.get("meta") or {}
            body = (h.get("text") or "").split("\n", 1)[-1].strip()
            item = f"- [[{m.get('title')}]] · {m.get('section')}（p{m.get('pages') or '?'}）\n  {body}"
            if used + len(item) > max_chars:
                item = item[: max(0, max_chars - used)]
            if not item.strip():
                continue
            parts.append(item)
            used += len(item)
            if used >= max_chars:
                break
        return (WIKI_HEADER + "\n" + "\n".join(parts)) if parts else ""
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--query", default="")
    ap.add_argument("-k", type=int, default=3)
    a = ap.parse_args()
    if a.query:
        hits = search(a.query, a.k)
        print(f"查询 {a.query!r} → {len(hits)} 条")
        for h in hits:
            m = h["meta"]
            print(f"  [{h['score']:.3f}] {m['title']} · {m['section']} (p{m['pages']}) {m['file']}")
            print("        " + h["text"].replace("\n", " ")[:110])
        return 0
    if a.stats:
        col = get_col()
        print(json.dumps({"collection": COLLECTION, "count": col.count(), "dir": CHROMA_DIR}, ensure_ascii=False))
        return 0
    sync(rebuild=a.rebuild)
    return 0


if __name__ == "__main__":
    sys.exit(main())
