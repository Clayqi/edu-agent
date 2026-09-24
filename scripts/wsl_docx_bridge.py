# -*- coding: utf-8 -*-
"""WSL 侧桥接：把「读 .docx / 写 .docx / 写 .pptx」在 Linux 里跑完。

为什么要它：George 这台机器的 Windows「智能应用控制」(SAC) 会拦 lxml 的 etree.pyd
（`DLL load failed: 应用程序控制策略已阻止此文件`），而 python-docx / python-pptx 都依赖 lxml，
于是 Windows 侧生成 Word/PPT 直接失败。SAC 管不到 WSL，所以这几步丢到 WSL 里跑，
Windows 侧只做编排（拼 payload / 传参 / 收结果）。

协议（stdio，一行一个 JSON）：
  请求  {"op": "docx_to_rich"|"export", "repo": "/mnt/d/<仓库>", "args": {...}}
  响应  {"ok": true, "value": {...}}  |  {"ok": false, "error": "TypeError: ..."}

路径约定：Windows 侧负责转换（`D:\\a\\b` ↔ `/mnt/d/a/b`），本脚本只认 POSIX 路径。
被调用方：src/edu_agent/wsl_docx.py（Windows 侧转发器）。

自测（在 WSL 里）：
  echo '{"op":"docx_to_rich","args":{"path":"/tmp/x.docx"}}' | \
    /home/h1582/.venvs/edu-agent/bin/python /mnt/d/教育agent/scripts/wsl_docx_bridge.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path


def _dispatch(op: str, args: dict, repo: Path):
    """在 WSL 里调用仓库自己的实现（不重复实现渲染逻辑，避免两边行为漂移）。"""
    sys.path.insert(0, str(repo / "src"))
    if op == "docx_to_rich":
        from edu_agent import template_rich

        return template_rich.docx_to_rich(
            str(args["path"]),
            template_id=args.get("template_id"),
            name=args.get("name"),
        )
    if op == "export":
        from edu_agent import wps_export

        return wps_export.export(
            args.get("payload") or {},
            markdown=args.get("markdown") or "",
            kind=args.get("kind") or "docx",
            out_dir=args.get("out_dir") or None,
            template=args.get("template") or None,
        )
    if op == "ping":
        from edu_agent import template_rich, wps_export  # noqa: F401

        import docx  # noqa: F401
        import pptx  # noqa: F401

        return {"ready": True, "python": sys.version.split()[0]}
    raise ValueError("未知 op: " + str(op))


def main() -> int:
    raw = sys.stdin.read()
    try:
        req = json.loads(raw or "{}")
    except json.JSONDecodeError as e:
        print(json.dumps({"ok": False, "error": f"请求不是合法 JSON: {e}"}, ensure_ascii=False))
        return 2
    repo = Path(req.get("repo") or "/mnt/d/教育agent")
    op = str(req.get("op") or "")
    args = req.get("args") or {}
    # 标记：本进程是「WSL 渲染后端」，让 wps_export.export() 跳过 WPS 桥接闸门
    # （这条路上是 python-docx/pptx 本地生成，不需要 WPS COM/MCP；见 src/edu_agent/wsl_docx.py）
    os.environ["EDU_WSL_RENDER"] = "1"
    # 仓库里的代码可能往 stdout 打日志 → 先截住，别污染我们的 JSON 协议
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            value = _dispatch(op, args, repo)
        print(json.dumps({"ok": True, "value": value}, ensure_ascii=False, default=str))
        return 0
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
