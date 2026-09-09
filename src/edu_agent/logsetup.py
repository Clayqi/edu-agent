"""工程补强(2026-09-07)：日志系统。

目标（缺失项 #3 日志系统 -> 影响「复现问题靠用户截图」）：
  - 每个请求带 request_id（contextvars），跨函数打日志时自动带上；
  - 结构化 EVENT 行（单行 k=v），问题/命中/重试/降级/耗时都可复现；
  - console + 可选滚动文件（EDU_LOG_FILE）；EDU_LOG_LEVEL 控制级别；
  - 纯标准库，测试/离线环境零副作用（默认 WARNING 静音，惰性初始化）。

用法：
    from edu_agent import logsetup
    logsetup.setup()                      # api/CLI 入口调用一次（幂等）
    log = logsetup.get_logger("generate")
    with logsetup.request(question=q) as ctx:
        logsetup.event(log, "retry", attempt=2, error="bad json")
"""
from __future__ import annotations

import contextvars
import logging
import os
import time
import uuid
from pathlib import Path

# ---- 请求上下文（每请求一个） ----
_REQ = contextvars.ContextVar("edu_request", default={})


def _rid() -> str:
    return uuid.uuid4().hex[:12]


class _CtxFilter(logging.Filter):
    """把当前请求上下文（request_id/kind/turn）拼到每行日志。"""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = _REQ.get()
        rid = ctx.get("request_id", "-")
        kind = ctx.get("kind", "-")
        record.reqctx = f"rid={rid} kind={kind}"
        return True


_configured = False


def setup(level: str | None = None, log_file: str | None = None) -> None:
    """配置 edu_agent 日志（幂等）。

    level: DEBUG/INFO/WARNING/ERROR；缺省读 EDU_LOG_LEVEL，默认 WARNING。
    log_file: 缺省读 EDU_LOG_FILE；None 且未配置 -> 只打 console。
    """
    global _configured
    lvl = (level or os.getenv("EDU_LOG_LEVEL", "") or "WARNING").upper()
    if lvl not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        lvl = "WARNING"
    root = logging.getLogger("edu_agent")
    root.setLevel(getattr(logging, lvl))
    if not _configured:
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s %(reqctx)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.addFilter(_CtxFilter())
        root.addHandler(sh)
        f = log_file if log_file is not None else os.getenv("EDU_LOG_FILE", "")
        if f:
            p = Path(f)
            p.parent.mkdir(parents=True, exist_ok=True)
            from logging.handlers import RotatingFileHandler

            fh = RotatingFileHandler(p, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
            fh.setFormatter(fmt)
            fh.addFilter(_CtxFilter())
            root.addHandler(fh)
        _configured = True
    # 允许重复调用改级别
    root.setLevel(getattr(logging, lvl))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger("edu_agent" + (f".{name}" if name else ""))


class request:
    """with logsetup.request(question=...) as ctx：为一段处理建立请求上下文。

    限制：只用于"同一调用栈内同步执行"的代码（CLI、普通请求处理）。
    不要把 with 跨生成器 yield 使用——生成器被线程池逐段恢复时，
    每次恢复可能发生在不同的 Context 副本，reset(token) 会抛 ValueError；
    已做防御捕获，但那样会丢失上下文，属降级而非正常用法。
    """

    def __init__(self, **fields):
        self._base = dict(fields)
        self._token = None
        self.ctx: dict = {}

    def __enter__(self) -> dict:
        ctx = {"request_id": _rid(), "start": time.time()}
        ctx.update(self._base)
        self._token = _REQ.set(ctx)
        self.ctx = ctx
        return ctx

    def __exit__(self, *exc):
        if self._token is not None:
            try:
                _REQ.reset(self._token)
            except ValueError:
                # 跨 Context 恢复（如生成器被线程池逐段 next）：静默放弃复位，
                # 每个 Context 副本是隔离的，悬空的 set 不会泄漏到其它请求
                pass


def event(logger: logging.Logger, event_kind: str, **fields) -> None:
    """结构化事件日志：单行 EVENT kind k=v k=v ...（自动带请求上下文）。

    event_kind=事件类型名；业务字段（含 kind=xxx）一律走 **fields，
    参数名刻意避开 kind 防撞（2026-09-07 修复）。"""
    parts = [f"{k}={v}" for k, v in fields.items()]
    logger.info("EVENT %s %s", event_kind, " ".join(parts))


def latency(logger: logging.Logger, event_kind: str, start: float, **fields) -> None:
    """耗时事件日志。event_kind=事件名；业务字段（如 kind=降级类型）走 **fields，
    避免与 event() 的 kind 参数撞名（2026-09-07 修复：曾致 TypeError）。"""
    ms = (time.time() - start) * 1000
    event(logger, event_kind, ms_ms=f"{ms:.0f}", **fields)
