"""S6 实现：过滤检索 + top_k。

用法：
    hits = retrieve("函数的单调性怎么判断", top_k=3)
    hits = retrieve(q, kinds=["concept"])              # 只搜概念卡
    hits = retrieve(q, kinds=["example", "exercise"])  # 只搜题目类
    hits = retrieve(q, chapter="第一章")
当前库以 kind=section 自动整节块为主（细卡就绪后 kinds 过滤即生效）。
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass


@dataclass
class Hit:
    chunk_id: str
    text: str
    metadata: dict
    score: float


# 进程内缓存检索客户端：每次提问重建 Chroma 要 1~3s，缓存后同库热问降到亚秒。
# chromadb 的 local client 多线程并发 query 有风险，因此用锁把 query 串行化
# （embed 网络调用也在这把锁内；本系统单用户场景可接受）。
_CHROMA_LOCK = threading.Lock()
_DB_CACHE: dict[tuple, object] = {}


def _get_db(persist_dir=None, collection: str | None = None):
    from langchain_chroma import Chroma

    from edu_agent.config import get_embeddings, load_settings

    s = load_settings()
    pd = persist_dir or s.chroma_db_dir
    return Chroma(
        persist_directory=str(pd),
        embedding_function=get_embeddings(),
        collection_name=collection or "edu_textbook",
    )


def _is_main(md: dict) -> bool:
    """主节（带编号 4.2）vs 旁栏（阅读与思考/信息技术应用/小结 等 section 为空）。"""
    return bool(re.match(r"^\d+\.\d+$", str(md.get("section") or "").strip()))


def _rrf(dense_ids: list[str], sparse_ids: list[str], k: int = 60) -> dict:
    """RRF 融合：score = sum 1/(k + rank)。"""
    score: dict[str, float] = {}
    for i, cid in enumerate(dense_ids, 1):
        score[cid] = score.get(cid, 0.0) + 1.0 / (k + i)
    for i, cid in enumerate(sparse_ids, 1):
        score[cid] = score.get(cid, 0.0) + 1.0 / (k + i)
    return score


def _rerank_local(query: str, hits: list[Hit]) -> list[Hit] | None:
    """本地 CrossEncoder（模型目录经 config 收口：RERANK_MODEL_DIR 可覆盖）。"""
    from edu_agent.config import load_settings

    local = str(load_settings().rerank_model_dir)
    try:
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(local)
        pairs = [[query, h.text[:800]] for h in hits]
        scores = model.predict(pairs)
        return [h for h, _ in sorted(zip(hits, scores), key=lambda z: z[1], reverse=True)]
    except Exception:
        return None


def _rerank_remote(query: str, hits: list[Hit]) -> list[Hit] | None:
    """硅基流动 bge-reranker API（key 经 config 收口）。"""
    from edu_agent.config import is_key_ready, load_settings

    s = load_settings()
    if not is_key_ready(s.siliconflow_api_key):
        return None
    try:
        import requests

        r = requests.post(
            s.siliconflow_base_url + "/rerank",
            headers={"Authorization": "Bearer " + s.siliconflow_api_key},
            json={"model": "BAAI/bge-reranker-v2-m3", "query": query,
                  "documents": [h.text[:800] for h in hits], "top_n": len(hits)},
            timeout=30,
        )
        r.raise_for_status()
        order = [d["index"] for d in r.json().get("results", [])]
        return [hits[i] for i in order if i < len(hits)]
    except Exception:
        return None


def rerank(query: str, hits: list[Hit]) -> list[Hit]:
    """第6层 Rerank 适配层（双通道，默认关）。

    启用：RERANK_ON=1 后按 RERANK_PROVIDER 尝试：
      1) local        -> 本地 model_cache/bge-reranker-v2-m3/（文件就绪时）
      2) siliconflow  -> 硅基流动 API（.env 配好 key 时）
    均不可用则原序返回（不影响主链路）。配置统一走 config.load_settings。
    """
    from edu_agent.config import load_settings

    s = load_settings()
    if not s.rerank_on or len(hits) < 2:
        return hits
    provider = s.rerank_provider
    out = None
    if provider == "local":
        out = _rerank_local(query, hits)
    elif provider == "siliconflow":
        out = _rerank_remote(query, hits)
    return out or hits


def retrieve(query: str, kinds: list[str] | None = None, top_k: int = 3,
             chapter: str | None = None, min_score: float | None = None,
             prefer_main: bool = True, hybrid: bool = True,
             source: str | None = None, persist_dir=None, collection: str | None = None) -> list[Hit]:
    """检索并返回命中 chunk（含坐标元数据），按相关度降序。

    第5层：多路召回（Dense 向量 + BM25 稀疏）经 RRF 融合；
    第6层：可选 rerank（rerank()）；主节（编号节）硬优先于旁栏。
    source/persist_dir/collection：用于用户上传 PDF 独立库（跳过 BM25）。
    """
    from edu_agent.config import load_settings

    # Chroma 客户端缓存（同库同 collection 复用实例）
    s = load_settings()
    cache_key = (str(persist_dir or s.chroma_db_dir), collection or "edu_textbook")
    if cache_key not in _DB_CACHE:
        _DB_CACHE[cache_key] = _get_db(persist_dir, collection)
    db = _DB_CACHE[cache_key]

    where: dict | None = {}
    if kinds:
        where["kind"] = {"$in": list(kinds)} if len(kinds) > 1 else kinds[0]
    if chapter:
        where["chapter"] = chapter
    if source:
        where["source"] = source
    if not where:
        where = None
    if persist_dir is not None:
        hybrid = False
    pool = max(top_k + 7, 10)
    # chromadb local client 并发 query 有风险：串行化（embed 网络调用含在内）
    with _CHROMA_LOCK:
        raw = db.similarity_search_with_score(query, k=pool, filter=where)
    dense_map: dict[str, Hit] = {}
    dense_ids: list[str] = []
    for d, score in raw:
        hit = Hit(
            chunk_id=d.metadata.get("chunk_id", ""),
            text=d.page_content,
            metadata=dict(d.metadata),
            score=float(score),
        )
        dense_map[hit.chunk_id] = hit
        dense_ids.append(hit.chunk_id)

    if hybrid:
        try:
            from edu_agent import bm25_index


            sparse_ids = bm25_index.search(query, top_k=8, kinds=kinds, chapter=chapter)
        except Exception:
            sparse_ids = []
        fused = _rrf(dense_ids, sparse_ids)
        order = sorted(fused.items(), key=lambda kv: (-kv[1], dense_map.get(kv[0]).score if kv[0] in dense_map else 9.9))
        hits = [dense_map[cid] for cid, _ in order if cid in dense_map]
        # 补漏：dense 有而 RRF 未纳入的
        hits += [dense_map[cid] for cid in dense_ids if cid not in fused]
    else:
        hits = [dense_map[cid] for cid in dense_ids]

    if prefer_main:
        hits.sort(key=lambda h: (0 if _is_main(h.metadata) else 1, h.score))
    hits = hits[:max(top_k, len(hits))]
    # rerank 只做精排，不得破坏"主节硬优先"不变量：末尾再按主/旁栏稳定分组
    # （Python sort 稳定 → 组内顺序保留 rerank 结果，旁栏仅在主节不足时补位）
    hits = rerank(query, hits)
    if prefer_main:
        hits.sort(key=lambda h: 0 if _is_main(h.metadata) else 1)
    hits = hits[:top_k]
    if min_score is not None:
        hits = [h for h in hits if h.score <= min_score]
    return hits
