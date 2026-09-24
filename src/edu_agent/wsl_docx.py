# -*- coding: utf-8 -*-
"""Word/PPT 生成的「WSL 后路」：Windows 侧跑不了 python-docx/pptx 时，转发到 WSL 里跑。

为什么要它（2026-09-12 本机实测）：Windows「智能应用控制」(SAC) 会拦 lxml 的 etree.pyd
（`DLL load failed while importing etree: 应用程序控制策略已阻止此文件`），而 python-docx /
python-pptx 都依赖 lxml → 本机生成 Word/PPT 一律 ImportError。SAC 管不到 WSL，
所以：**Windows 只做编排（拼 payload、传参、收结果），真正的 .docx/.pptx 渲染丢进 WSL**。

设计取舍：
- **默认 native 优先**：只有本机 `import docx/pptx` 真的失败时才走 WSL（队友机器/CI 不受影响）。
  可用环境变量 EDU_DOCX_BACKEND=native|wsl 强制指定。
- 桥接只做两个 op（`docx_to_rich` / `export`），因为全仓只有这两个函数碰 docx/pptx 渲染，
  且 WSL 侧直接调用**仓库里同一个实现**（scripts/wsl_docx_bridge.py），不重复实现、不漂移。
- 路径在两侧转换：`D:\\dir\\f.docx` ↔ `/mnt/d/dir/f.docx`。仓库禁止写死盘符，故一律由字符串换算。

依赖的环境（一次性准备，免 sudo，2026-09-12 实测可行）：
  # 注意：uv 的官方安装脚本(astral.sh)在本机网络会被 reset，改走 get-pip.py；
  # Ubuntu 24.04 的 PEP 668 限制用 --break-system-packages 绕过，装到 ~/.local（不碰系统目录）
  curl -sSL -o /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py
  python3 /tmp/get-pip.py --user --break-system-packages --index-url https://mirrors.aliyun.com/pypi/simple/
  python3 -m pip install --user --break-system-packages \
      --index-url https://mirrors.aliyun.com/pypi/simple/ python-docx python-pptx python-dotenv
  # 验证：python3 -c "import docx, pptx, lxml.etree, PIL; print('OK')"
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHIM = REPO / "scripts" / "wsl_docx_bridge.py"
DEFAULT_DISTRO = os.environ.get("EDU_WSL_DISTRO", "Ubuntu")
DEFAULT_PY = os.environ.get("EDU_WSL_PYTHON", "python3")   # 包装在 ~/.local，系统 python3 直接能 import
TIMEOUT = float(os.environ.get("EDU_WSL_TIMEOUT", "240"))

_MNT = re.compile(r"^/mnt/([a-zA-Z])/(.*)$")


def to_wsl(p: str | Path | None) -> str | None:
    """Windows 路径 → WSL 路径（`D:\\a\\b` → `/mnt/d/a/b`）；空值原样返回。"""
    if p is None or str(p).strip() == "":
        return None
    s = str(p).replace("\\", "/")
    m = re.match(r"^([a-zA-Z]):/(.*)$", s)
    if m:
        return f"/mnt/{m.group(1).lower()}/{m.group(2)}"
    return s


def to_win(p: str | Path | None) -> str | None:
    """WSL 路径 → Windows 路径（`/mnt/d/a/b` → `D:\\a\\b`）；非 /mnt 开头原样返回。"""
    if p is None:
        return None
    m = _MNT.match(str(p))
    if m:
        return f"{m.group(1).upper()}:\\" + m.group(2).replace("/", "\\")
    return str(p)


def _fix_paths(value):
    """把 WSL 返回结果里出现的 /mnt/x/... 一律换回 Windows 路径（递归）。"""
    if isinstance(value, str):
        return to_win(value) if value.startswith("/mnt/") else value
    if isinstance(value, list):
        return [_fix_paths(v) for v in value]
    if isinstance(value, dict):
        return {k: _fix_paths(v) for k, v in value.items()}
    return value


@lru_cache(maxsize=1)
def native_ok() -> bool:
    """本机能不能直接跑 python-docx/pptx（SAC 拦 lxml 时为 False）。"""
    try:
        import docx  # noqa: F401
        import pptx  # noqa: F401

        return True
    except Exception:  # noqa: BLE001  ImportError / OSError(DLL 被拦) 都算不可用
        return False


@lru_cache(maxsize=1)
def _decide() -> str:
    forced = (os.environ.get("EDU_DOCX_BACKEND") or "").strip().lower()
    if forced in ("native", "wsl"):
        return forced
    return "native" if native_ok() else "wsl"


def backend() -> str:
    """当前用哪个后端：'native' 或 'wsl'。"""
    return _decide()


def call(op: str, args: dict) -> dict:
    """在 WSL 里执行一个 op。返回 {"ok": True, "value": ...} 或 {"ok": False, "error": "..."}。"""
    if not shutil.which("wsl"):
        return {"ok": False, "error": "找不到 wsl.exe（本机没装 WSL？）"}
    req = {"op": op, "repo": to_wsl(REPO), "args": args}
    cmd = ["wsl.exe", "-d", DEFAULT_DISTRO, "--", DEFAULT_PY, str(to_wsl(SHIM))]
    try:
        r = subprocess.run(cmd, input=json.dumps(req, ensure_ascii=False), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"WSL 侧超过 {TIMEOUT:.0f}s 未返回"}
    out = (r.stdout or "").strip().splitlines()
    for line in reversed(out):                        # 只认最后一行 JSON，前面可能是 WSL 的杂音
        line = line.strip()
        if line.startswith("{"):
            try:
                resp = json.loads(line)
            except json.JSONDecodeError:
                continue
            if resp.get("ok"):
                return {"ok": True, "value": _fix_paths(resp.get("value"))}
            return {"ok": False, "error": resp.get("error") or "WSL 侧返回 ok=false"}
    err = (r.stderr or "").strip()[-400:] or (r.stdout or "").strip()[-400:]
    return {"ok": False, "error": f"WSL 侧无有效输出（exit={r.returncode}）: {err}"}


@lru_cache(maxsize=1)
def wsl_ready() -> tuple[bool, str]:
    """WSL 后路是否可用（探一次并缓存）：桥接脚本 + venv + docx/pptx 都能用才算就绪。"""
    if not SHIM.exists():
        return False, f"缺少桥接脚本 {SHIM}"
    if not shutil.which("wsl"):
        return False, "找不到 wsl.exe"
    resp = call("ping", {})
    if resp.get("ok"):
        return True, f"WSL 就绪（python {resp['value'].get('python')}）"
    return False, str(resp.get("error"))


def docx_to_rich(path: str | Path, template_id: str | None = None,
                 name: str | None = None) -> dict:
    """template_rich.docx_to_rich 的 WSL 版（读 .docx → 富模型）。"""
    resp = call("docx_to_rich", {"path": to_wsl(path), "template_id": template_id, "name": name})
    if not resp.get("ok"):
        raise RuntimeError("WSL 侧解析 .docx 失败：" + str(resp.get("error")))
    return resp["value"] or {}


def export(payload: dict, markdown: str = "", kind: str = "docx",
           out_dir: str | None = None, template: dict | None = None) -> dict:
    """wps_export.export 的 WSL 版（教案 → .docx/.pptx），返回结构与本地版一致。"""
    resp = call("export", {"payload": payload, "markdown": markdown, "kind": kind,
                           "out_dir": to_wsl(out_dir), "template": template})
    if not resp.get("ok"):
        return {"ok": False, "error": "WSL 侧生成失败：" + str(resp.get("error")), "backend": "wsl"}
    value = resp["value"] or {}
    if isinstance(value, dict):
        value.setdefault("backend", "wsl")
    return value


def export_best(payload: dict, markdown: str = "", kind: str = "docx",
                out_dir: str | None = None, template: dict | None = None) -> dict:
    """按「本机能渲染就本机渲染，渲染不了才走 WSL」的次序导出（供 web 层调用）。

    判据是 **native_ok()**（本机能不能 import python-docx/pptx），不是 capabilities.wps_available()：
    后者查的是「WPS MCP 桥接」，本机那套即使可用，PPT 这条路也是用 python-pptx 本地生成的
    （见 wps_export._export_pptx），照样会被 SAC 拦 lxml 打死。

    为什么改道判断放在这里、而不是塞进 wps_export.export()：
    `export()` 的契约是「WPS 能力被关/未装时明确失败」（tests/test_wps_tools.py::TestGate 锁着），
    在里面静默改道会破坏那个契约。改道属于「编排」，交给调用方；本机能渲染时行为完全不变。
    """
    from edu_agent import wps_export

    if not native_ok() and backend() == "wsl":
        ready, why = wsl_ready()
        if ready:
            return export(payload, markdown=markdown, kind=kind, out_dir=out_dir, template=template)
        return {"ok": False, "backend": "wsl", "gate": "backend",
                "error": f"本机 python-docx/pptx 不可用，WSL 后路也不可用：{why}"}
    return wps_export.export(payload, markdown=markdown, kind=kind, out_dir=out_dir, template=template)
