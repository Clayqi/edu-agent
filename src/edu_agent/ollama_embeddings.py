"""Ollama 本地 bge-m3 Embedding 封装（requests 直调 /api/embed）。

实测（2026-09-06）：POST {model, input:[...]} 返回
  {"embeddings": [[1024 floats], ...], ...}  —— embeddings 直接是向量列表。
免去远程 embedding 的 key/网络依赖。
"""
from __future__ import annotations

import requests

BGE_M3_DIM = 1024


class OllamaBgeM3Embeddings:
    """LangChain Embeddings 兼容（embed_query/embed_documents）。

    keep_alive: 每次请求携带的 ollama 驻留时长。默认 -1 = 模型加载后常驻内存
    （解决闲置 5 分钟被卸载、首问冷加载 2-4s 的问题）；ollama 服务重启后失效，
    由下一次请求重新钉住。
    """

    def __init__(self, model: str = "bge-m3", base_url: str = "http://localhost:11434",
                 keep_alive: int | str = -1):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.keep_alive = keep_alive

    def embed_documents(self, texts: list[str], batch_size: int = 8) -> list[list[float]]:
        if not texts:
            return []
        # 分批：一次喂过多长文本 Ollama 会 400
        out: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            r = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": list(batch),
                      "keep_alive": self.keep_alive},
                # (连接超时, 读取超时)：连接层 5s 快速失败，
                # 避免 Ollama 未启动/被防火墙黑洞时一次提问挂满 300s 才报错
                timeout=(5, 300),
            )
            if r.status_code != 200:
                raise RuntimeError(f"Ollama /api/embed {r.status_code}: {r.text[:300]}")
            embs: list[list[float]] = r.json().get("embeddings") or []
            if len(embs) != len(batch):
                raise RuntimeError(f"Ollama 返回条数异常: {len(embs)} != 输入 {len(batch)}")
            for e in embs:
                if len(e) != BGE_M3_DIM:
                    raise RuntimeError(f"bge-m3 维度异常: {len(e)} != {BGE_M3_DIM}")
            out.extend(embs)
        return out

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
