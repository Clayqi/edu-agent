# -*- coding: utf-8 -*-
"""edu-math MCP 客户端：把 mcp_servers/math_server.py 的计算工具挂进教育agent。

设计（路线 B「能力挂载」，与 retrieve.py 同一兜底哲学）：
- 工具调用走真 MCP 协议（stdio 子进程：mcp.client.stdio + ClientSession）
- 每次调用短连接（asyncio.run 内 起进程->握手->call_tool->退出）：实现最简单、
  失败隔离最彻底（server 进程崩了下一次自动重起），代价是每次 ~2-4s 启动开销
- 全部异常吞掉返回 None：工具挂了主链路不受影响
- 工具名白名单校验，杜绝任意调用

用法：
    from edu_agent.mcp_tools import mcp_call, mcp_available
    mcp_available()            # -> ["derivative", ...] 或 []（server 没起来）
    mcp_call("derivative", expr="x^2-4x+3")   # -> "2*x - 4" 或 None
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# 项目根 = src/edu_agent/mcp_tools.py 上溯 3 级
_PROJ_ROOT = Path(__file__).resolve().parents[2]
_SERVER = str(_PROJ_ROOT / "mcp_servers" / "math_server.py")

# 白名单：只允许调这 5 个教学计算工具
ALLOWED = frozenset(
    {"derivative", "monotonic_intervals", "solve_equation", "evaluate", "simplify"}
)

_tools_cache: list[str] | None = None


def _server_params():
    from mcp import StdioServerParameters

    # command 用当前解释器（venv python，带 sympy + mcp）；env=None = 继承父进程环境
    return StdioServerParameters(command=sys.executable, args=[_SERVER], env=None)


async def _list_once() -> list[str]:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    async with stdio_client(_server_params()) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            return [t.name for t in tools.tools]


async def _call_once(name: str, args: dict) -> str:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    async with stdio_client(_server_params()) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(name, arguments=args)
            texts = [b.text for b in res.content if getattr(b, "type", "") == "text"]
            return "\n".join(texts) if texts else str(res)


def mcp_available(timeout: float = 15.0) -> list[str]:
    """发现 MCP server 工具清单（首次真查，结果模块级缓存；失败返回 []）。"""
    global _tools_cache
    if _tools_cache is not None:
        return _tools_cache
    try:
        _tools_cache = asyncio.run(asyncio.wait_for(_list_once(), timeout))
    except Exception:
        _tools_cache = []
    return _tools_cache


def mcp_call(name: str, timeout: float = 30.0, **kwargs) -> str | None:
    """调一个白名单 MCP 工具。任何失败（进程起不来/超时/工具报错）都返回 None。"""
    if name not in ALLOWED:
        return None
    try:
        return asyncio.run(asyncio.wait_for(_call_once(name, kwargs), timeout))
    except Exception:
        return None
