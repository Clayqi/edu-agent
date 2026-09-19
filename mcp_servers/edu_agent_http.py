# -*- coding: utf-8 -*-
"""edu-agent HTTP MCP server：把 5174 Web 网关的完整多 Agent 能力挂载为 MCP 工具。

工具：
  ask_agent   调用 edu-agent 任意 Agent（A 课本答疑 / B 教案 / S 总指挥 / auto 自动）

说明：
  - 依赖运行中的 edu-agent Web 服务（http://127.0.0.1:5174，start_web.cmd 启动）
  - 依赖 requests（edu-agent 环境已有）
  - stdio transport，由 client（OpenCode）拉起
"""
from __future__ import annotations

import json

import requests
from mcp.server.fastmcp import FastMCP

BASE = "http://127.0.0.1:5174"

mcp = FastMCP("edu-agent")


@mcp.tool()
def ask_agent(text: str, preset: str = "auto", session_id: str = "") -> str:
    """调用 edu-agent 的 Agent 来回答高中数学问题或生成教案。

    preset: A=课本教练答疑、B=教案生成、S=总指挥派单、auto=自动识别（默认）。
    例：ask_agent('什么是函数的单调性？') 或 ask_agent('帮我写一份函数单调性的教案', 'B')
    返回 Agent 完整回复（含教材引用；B 模式返回教案正文与 HTML 链接）。
    """
    payload = {
        "text": text,
        "preset": preset or "auto",
        "session_id": session_id or None,
        "template_id": "default",
        "corpus": "textbook",
    }
    try:
        with requests.post(BASE + "/api/chat", json=payload, stream=True,
                           timeout=600) as r:
            r.raise_for_status()
            acc = []
            errors = []
            done = None
            for raw in r.iter_lines(decode_unicode=False):
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace")
                if not line.startswith("data:"):
                    continue
                try:
                    ev = json.loads(line[5:].strip())
                except Exception:
                    continue
                t = ev.get("t")
                if t == "d":
                    acc.append(ev.get("text", ""))
                elif t == "done":
                    done = ev
                elif t == "error":
                    errors.append(ev.get("text", ""))

            if done is not None:
                out = done.get("text") or "".join(acc)
                cits = done.get("citations") or []
                if cits:
                    lines = []
                    for c in cits[:10]:
                        if isinstance(c, dict):
                            lines.append("[%s] 页码 %s" % (c.get("id", "?"), c.get("page", "?")))
                        else:
                            lines.append(str(c))
                    out += "\n\n【引用】\n" + "\n".join(lines)
                html = done.get("html")
                title = done.get("title")
                if title:
                    out = "教案标题：%s\n\n%s" % (title, out)
                if html:
                    out += "\n\n教案 HTML：%s/files/%s" % (BASE, html)
                return out
            if errors:
                return "ERROR: " + " | ".join(errors)
            return "（无回复）" + ("".join(acc) if acc else "")
    except requests.exceptions.ConnectionError:
        return ("ERROR: 无法连接 edu-agent 服务（%s），"
                "请先运行 D:\\edu-agent\\start_web.cmd 启动 5174" % BASE)
    except Exception as e:
        return "ERROR: %s: %s" % (type(e).__name__, e)


if __name__ == "__main__":
    mcp.run(transport="stdio")