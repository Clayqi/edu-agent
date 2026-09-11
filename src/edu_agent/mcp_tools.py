# -*- coding: utf-8 -*-
"""MCP 客户端：把 mcp_servers/ 下的 MCP 服务挂进教育 agent（多服务版，2026-09-10）。

服务清单与开关统一由 edu_agent.capabilities 管（默认全开，可在「MCP 服务」里关）。

设计（路线 B「能力挂载」，与 retrieve.py 同一兜底哲学）：
- 工具调用走真 MCP 协议（stdio 子进程：mcp.client.stdio + ClientSession）
- 每次调用短连接（asyncio.run 内 起进程->握手->call_tool->退出）：实现最简单、
  失败隔离最彻底（server 进程崩了下一次自动重起），代价是每次 ~2-4s 启动开销
- 多步编排用 call_sequence：一次握手跑完一串调用（教案导出这类场景）
- 全部异常吞掉返回 None/[]：工具挂了主链路不受影响
- 服务被关掉（capabilities 开关）时直接短路，不起子进程
- 工具名白名单校验（仅 edu-math 这类给定白名单的服务），杜绝任意调用

兼容旧接口：
    from edu_agent.mcp_tools import mcp_call, mcp_available
    mcp_available()                            # -> ["derivative", ...] 或 []
    mcp_call("derivative", expr="x^2-4x+3")    # -> "2*x - 4" 或 None

新接口：
    list_tools("wps-office")                   # -> 工具名列表
    call_tool("wps-office", "wps_common_ping", {})
    call_sequence("wps-office", [("wps_common_ping", {}), ...])
"""
from __future__ import annotations

import asyncio
import shutil
import sys
from typing import Any, Iterable

from edu_agent import capabilities

# edu-math 白名单：只允许调这几个教学计算工具
_MATH_ALLOWED = frozenset(
    {"derivative", "monotonic_intervals", "solve_equation", "evaluate", "simplify"}
)

# 兼容旧名（重构前叫 ALLOWED；tests/test_math_verify.py 仍按此断言）
ALLOWED = _MATH_ALLOWED

# WPS Office 白名单：只放"教案导出"真正调用的 6 个工具。
# 第三方 wps-office-mcp 暴露 243 个工具（含万能方法调用 wps_execute_method），
# 全开 = 给 agent 无限制的 WPS/本机文档控制权 → 按用途收口（2026-09-11 合并评审补）。
# 以后要扩能力（如 Excel 题库），先往本表加工具名，再写调用代码。
_WPS_ALLOWED = frozenset({
    "wps_common_ping",            # 连通性探测
    "wps_common_save_as",         # 另存为（.docx/.pptx 落盘）
    "wps_execute_method",         # 万能方法调用：createDocument / addSlide / insertTable 走它
    "wps_word_open_document",     # 打开/新建 Word 文档
    "wps_word_insert_text",       # 逐段写入正文
    "wps_ppt_open_presentation",  # 打开/新建演示文稿
})

# 每个服务的工具白名单（缺省 = 不限制；新服务务必显式登记，别留空）
_WHITELIST: dict[str, frozenset[str]] = {
    "math": _MATH_ALLOWED,
    "wps-office": _WPS_ALLOWED,
}

# MCP 调用开销较大，默认超时
CALL_TIMEOUT = 45.0
LIST_TIMEOUT = 25.0

_tools_cache: list[str] | None = None


# ---------- 启动参数 ----------
def server_params(server_id: str):
    """按服务定义生成 stdio 启动参数（python 服务用当前解释器，node 服务用 node）。"""
    from mcp import StdioServerParameters

    spec = capabilities.mcp_spec(server_id)
    if spec is None:
        raise KeyError(server_id)
    if spec.kind == "node":
        exe = shutil.which("node")
        if not exe:
            raise RuntimeError("未检测到 Node.js")
        return StdioServerParameters(command=exe, args=[str(spec.entry())], env=None)
    return StdioServerParameters(command=sys.executable, args=[str(spec.entry())], env=None)


def _gate(server_id: str) -> bool:
    """开关关掉 / 入口不存在 -> False（不起子进程）。"""
    spec = capabilities.mcp_spec(server_id)
    if spec is None or not spec.entry().exists():
        return False
    return capabilities.is_enabled("mcp", server_id)


def _allowed(server_id: str, tool: str) -> bool:
    wl = _WHITELIST.get(server_id)
    return True if wl is None else (tool in wl)


# ---------- 协议调用 ----------
async def _list_once(server_id: str) -> list[str]:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    async with stdio_client(server_params(server_id)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            return [t.name for t in tools.tools]


async def _call_once(server_id: str, name: str, args: dict) -> str:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    async with stdio_client(server_params(server_id)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(name, arguments=args)
            texts = [b.text for b in res.content if getattr(b, "type", "") == "text"]
            return "\n".join(texts) if texts else str(res)


async def _sequence_once(server_id: str, calls: Iterable[tuple[str, dict]]) -> list[dict]:
    """一次 stdio 会话里跑完一串调用（失败不中断后续，逐条记录结果）。"""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    out: list[dict] = []
    async with stdio_client(server_params(server_id)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            for name, args in calls:
                try:
                    res = await s.call_tool(name, arguments=args or {})
                    texts = [b.text for b in res.content if getattr(b, "type", "") == "text"]
                    out.append({"tool": name, "ok": not bool(getattr(res, "isError", False)),
                                "text": "\n".join(texts) if texts else ""})
                except Exception as e:
                    out.append({"tool": name, "ok": False,
                                "text": "", "error": f"{type(e).__name__}: {e}"})
    return out


# ---------- 对外接口 ----------
def list_tools(server_id: str, timeout: float = LIST_TIMEOUT) -> list[str]:
    """发现某个 MCP 服务的工具清单（失败/被关闭返回 []）。"""
    if not _gate(server_id):
        return []
    try:
        return asyncio.run(asyncio.wait_for(_list_once(server_id), timeout))
    except Exception:
        return []


def call_tool(server_id: str, name: str, args: dict | None = None,
              timeout: float = CALL_TIMEOUT) -> str | None:
    """调一个 MCP 工具。被关闭 / 不在白名单 / 任何失败 -> None。"""
    if not _gate(server_id) or not _allowed(server_id, name):
        return None
    try:
        return asyncio.run(asyncio.wait_for(_call_once(server_id, name, args or {}), timeout))
    except Exception:
        return None


def call_sequence(server_id: str, calls: Iterable[tuple[str, dict]],
                  timeout: float = 300.0) -> list[dict]:
    """一串 MCP 调用共用一个 stdio 会话。被关闭 / 失败 -> []。"""
    calls = [(n, a) for n, a in calls if _allowed(server_id, n)]
    if not _gate(server_id) or not calls:
        return []
    try:
        return asyncio.run(asyncio.wait_for(_sequence_once(server_id, calls), timeout))
    except Exception:
        return []


# ---------- 兼容旧接口（edu-math） ----------
def mcp_available(timeout: float = 15.0) -> list[str]:
    """edu-math 工具清单（首次真查，结果模块级缓存；失败返回 []）。"""
    global _tools_cache
    if _tools_cache is not None:
        return _tools_cache
    _tools_cache = list_tools("math", timeout=timeout)
    return _tools_cache


def mcp_call(name: str, timeout: float = 30.0, **kwargs: Any) -> str | None:
    """调一个 edu-math 白名单工具（任何失败返回 None）。"""
    return call_tool("math", name, kwargs, timeout=timeout)
