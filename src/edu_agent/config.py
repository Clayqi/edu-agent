"""读取 .env 的全局配置与 OpenAI 兼容客户端工厂。

embedding 通道（择优自 textbook-coach，2026-09-06 拍板）：
  EMBEDDING_PROVIDER=ollama       本机 Ollama bge-m3（默认，免 key）
  EMBEDDING_PROVIDER=siliconflow 硅基流动 API bge-m3（远程备用，需 key）

LLM：DeepSeek（key 复用 hermes config.yaml，注入 .env，base=/v1）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# 占位符判定：Key 未就绪时不发起真实调用
_PLACEHOLDER_HINTS = ("sk-placeholder", "replace-me", "your-", "xxxx")


def is_key_ready(api_key: str | None) -> bool:
    """Key 非空且不含占位符才算就绪。"""
    if not api_key:
        return False
    low = api_key.lower()
    return not any(h in low for h in _PLACEHOLDER_HINTS)


@dataclass(frozen=True)
class Settings:
    # LLM：DeepSeek
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    # embedding：双通道
    embedding_provider: str          # ollama | siliconflow
    ollama_base_url: str
    embedding_model: str
    siliconflow_api_key: str
    siliconflow_base_url: str
    # 路径
    chroma_db_dir: Path
    content_dir: Path                # 人工精修细 chunk（kind=concept/example/exercise）
    auto_content_dir: Path           # PDF 自动切节粗 chunk（kind=section）
    textbook_pdf: Path | None
    # 运行数据根（第一阶段收口：会话/上传/日志等运行态集中于此）
    data_dir: Path
    sessions_db: Path                # 统一会话存储（host.store.SessionStore）
    log_file: Path                   # UI/CLI 默认滚动日志
    # rerank（原散落在 retrieve.py / 启动脚本 env，收口进 settings）
    rerank_on: bool
    rerank_provider: str             # local | siliconflow
    rerank_model_dir: Path           # local CrossEncoder 模型目录

    @property
    def deepseek_ready(self) -> bool:
        return is_key_ready(self.deepseek_api_key)

    @property
    def siliconflow_ready(self) -> bool:
        return is_key_ready(self.siliconflow_api_key)


def load_settings() -> Settings:
    def _path(v: str) -> Path:
        p = Path(v)
        return p if p.is_absolute() else (ROOT / p).resolve()

    pdf = os.getenv("TEXTBOOK_PDF", "")
    data_dir = _path(os.getenv("EDU_DATA_DIR", "./data"))
    return Settings(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "ollama").strip().lower(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "bge-m3"),
        siliconflow_api_key=os.getenv("SILICONFLOW_API_KEY", ""),
        siliconflow_base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
        chroma_db_dir=_path(os.getenv("CHROMA_DB_DIR", "./chroma_db")),
        content_dir=_path(os.getenv("CONTENT_DIR", "./content/structured")),
        auto_content_dir=_path(os.getenv("AUTO_CONTENT_DIR", "./content/structured_auto")),
        textbook_pdf=Path(pdf) if pdf else None,
        data_dir=data_dir,
        sessions_db=_path(os.getenv("EDU_SESSIONS_DB", str(data_dir / "edu_sessions.db"))),
        log_file=_path(os.getenv("EDU_LOG_FILE", str(data_dir / "logs" / "edu_agent.log"))),
        rerank_on=os.getenv("RERANK_ON", "") == "1",
        rerank_provider=os.getenv("RERANK_PROVIDER", "local").strip().lower(),
        rerank_model_dir=_path(os.getenv("RERANK_MODEL_DIR", "./model_cache/bge-reranker-v2-m3")),
    )


def get_chat_llm(model: str | None = None, max_tokens: int | None = None,
                 temperature: float = 0.0, timeout: float = 600):
    """DeepSeek 对话模型（OpenAI 兼容）。Key 未就绪时抛出 RuntimeError。

    timeout 语义：流式 = chunk 空闲超时；非流式 = 请求总超时。
    答疑链路（单问 <20s）建议传 60~90；教案长生成（planner）传 300。
    """
    from langchain_openai import ChatOpenAI

    s = load_settings()
    if not s.deepseek_ready:
        raise RuntimeError("DEEPSEEK_API_KEY 未就绪（缺省或占位符），请先配置真实 Key。")
    return ChatOpenAI(
        model=model or s.deepseek_model,
        api_key=s.deepseek_api_key,
        base_url=s.deepseek_base_url,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )


def get_embeddings():
    """按 EMBEDDING_PROVIDER 返回 embedding 客户端（LangChain Embeddings 兼容）。"""
    s = load_settings()
    if s.embedding_provider == "ollama":
        from edu_agent.ollama_embeddings import OllamaBgeM3Embeddings

        return OllamaBgeM3Embeddings(model=s.embedding_model, base_url=s.ollama_base_url)
    if s.embedding_provider == "siliconflow":
        if not s.siliconflow_ready:
            raise RuntimeError("SILICONFLOW_API_KEY 未就绪（缺省或占位符）。")
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=s.embedding_model,
            api_key=s.siliconflow_api_key,
            base_url=s.siliconflow_base_url,
        )
    raise RuntimeError(f"未知 EMBEDDING_PROVIDER: {s.embedding_provider!r}（应为 ollama 或 siliconflow）")
