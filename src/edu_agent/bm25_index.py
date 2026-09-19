"""BM25 稀疏检索（第5层·多路召回之一）。

- 词元化：CJK 用重叠二元组 + ASCII 词，免 jieba 依赖；
- 语料：直接读取 Chroma 全量（chunk_id/text/metadata）构建，惰性+缓存；
- 返回带 score 的候选，供 retrieve() 做 RRF 融合。
"""
from __future__ import annotations

import re

_ascii = re.compile(r"[a-zA-Z0-9]+")
_cjk = re.compile(r"[\u4e00-\u9fff]")


def zh_tokens(text: str) -> list[str]:
    out: list[str] = []
    for w in _ascii.findall(text):
        out.append(w.lower())
    for m in _cjk.finditer(text):
        out.append(m.group(0))
    # 相邻汉字二元组（提升短语匹配）
    chars = [m.group(0) for m in _cjk.finditer(text)]
    out.extend("".join(chars[i:i + 2]) for i in range(len(chars) - 1))
    return out


_cache = {"docs": None, "bm25": None, "ids": []}


def _load():
    from edu_agent.retrieve import _get_db

    db = _get_db()
    got = db.get(include=["documents", "metadatas"])
    ids = got.get("ids") or []
    docs = got.get("documents") or []
    metas = got.get("metadatas") or []
    return ids, docs, metas


def ensure(refresh: bool = False):
    """惰性构建 BM25（语料数变化时自动重建）。"""
    from rank_bm25 import BM25Okapi

    if _cache["bm25"] is not None and not refresh:
        return _cache
    ids, docs, metas = _load()
    corpus = [zh_tokens(t) for t in docs]
    _cache["ids"] = ids
    _cache["docs"] = dict(zip(ids, docs))
    _cache["metas"] = dict(zip(ids, metas))
    _cache["bm25"] = BM25Okapi(corpus) if corpus else None
    _cache["doc_ids"] = ids
    return _cache


def search(query: str, top_k: int = 8, kinds=None, chapter=None) -> list[str]:
    """返回按 BM25 分数排序的 chunk_id 列表。"""
    c = ensure()
    bm = c.get("bm25")
    if bm is None:
        return []
    toks = zh_tokens(query)
    if not toks:
        return []
    scores = bm.get_scores(toks)
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    out = []
    for i in order:
        if scores[i] <= 0:
            continue
        cid = c["doc_ids"][i]
        md = c["metas"].get(cid, {})
        if kinds and md.get("kind") not in kinds:
            continue
        if chapter and md.get("chapter") != chapter:
            continue
        out.append(cid)
        if len(out) >= top_k:
            break
    return out
