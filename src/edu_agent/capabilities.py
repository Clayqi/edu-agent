"""能力注册表：MCP 服务与 Skill 的统一开关 + 运行状态（2026-09-10 WPS 集成）。

设计（对齐项目既有兜底哲学，见 mcp_tools.py / retrieve.py）：
- 能力定义（spec）写在代码里；运行态开关落 data/capabilities.json，**默认全开**
- 状态探测全部吞异常：探测失败只影响「状态」显示，绝不阻断业务链路
- 探测结果带 TTL 缓存：右栏面板轮询不会反复起子进程

用法：
    from edu_agent import capabilities
    capabilities.snapshot()                      # -> {"mcp": [...], "skills": [...]}
    capabilities.is_enabled("mcp", "wps-office") # -> True / False
    capabilities.set_enabled("mcp", "wps-office", False)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from edu_agent.config import load_settings

ROOT = Path(__file__).resolve().parents[2]

_MCP_CACHE_TTL = 45.0     # 快探测（桥接 ping / 进程 / 产物）缓存
_TOOLS_CACHE_TTL = 300.0  # MCP 工具清单缓存（要起子进程，慢）


# ---------- 第三方 WPS MCP（wps-skills）安装位置解析 ----------
# 交接约定（docs/09-WPS接入交接要求.md）：第三方源码/node_modules **不入库**，
# 由 deploy/setup_wps_mcp.cmd 克隆到仓库外的固定位置。解析优先级：
#   1) 环境变量 WPS_MCP_ENTRY（直接指向 dist/index.js）
#   2) 环境变量 WPS_MCP_DIR（wps-skills 克隆目录）
#   3) data/wps_mcp.json（安装脚本写的运行时配置）
#   4) 默认 %LOCALAPPDATA%\edu-agent\deps\wps-skills
def _default_wps_root() -> Path:
    import os

    base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(base) / "edu-agent" / "deps" / "wps-skills"


def _runtime_wps_root() -> Path | None:
    """读安装脚本写的 data/wps_mcp.json。"""
    import json

    try:
        p = load_settings().data_dir / "wps_mcp.json"
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        d = str(data.get("dir") or "").strip()
        return Path(d) if d else None
    except Exception:
        return None


def wps_root() -> Path:
    """wps-skills 的克隆目录（仓库外）。"""
    s = load_settings()
    if s.wps_mcp_entry:
        return Path(s.wps_mcp_entry).parent.parent
    if s.wps_mcp_dir:
        return Path(s.wps_mcp_dir)
    return _runtime_wps_root() or _default_wps_root()


def wps_entry() -> Path:
    """wps-office MCP 服务入口（dist/index.js）。"""
    s = load_settings()
    if s.wps_mcp_entry:
        return Path(s.wps_mcp_entry)
    return wps_root() / "wps-office-mcp" / "dist" / "index.js"


def wps_skills_dir() -> Path:
    """第三方 Skills 目录（随 wps-skills 一起克隆，同样不入库）。"""
    return wps_root() / "skills"


@dataclass(frozen=True)
class McpSpec:
    id: str
    name: str
    desc: str
    kind: str                 # python | node
    resolve: Callable[[], Path]   # 入口文件解析器（惰性：第三方可换位置/未安装）
    probe: str = "stdio"      # stdio | wps-bridge
    default_on: bool = True
    note: str = ""
    requires: tuple[str, ...] = ()   # 该服务额外需要的 python 模块（客户端 mcp 包另行统一检查）

    def entry(self) -> Path:
        try:
            return self.resolve()
        except Exception:
            return Path("")


@dataclass(frozen=True)
class SkillSpec:
    id: str
    name: str
    desc: str
    category: str
    icon: str
    mcp: str = ""             # 绑定的 MCP 服务 id
    default_on: bool = True


MCP_SPECS: tuple[McpSpec, ...] = (
    McpSpec(
        id="math",
        name="edu-math 计算服务",
        desc="符号计算 / 求导 / 单调区间 / 解方程（teaching 计算校验）",
        kind="python",
        resolve=lambda: ROOT / "mcp_servers" / "math_server.py",
        probe="stdio",
        requires=("sympy",),
    ),
    McpSpec(
        id="wps-office",
        name="WPS Office 服务",
        desc="经 PowerShell COM 操控 WPS 文字 / 表格 / 演示（教案导出 Word 等）",
        kind="node",
        resolve=wps_entry,
        probe="wps-bridge",
        note="第三方（wps-skills）装在仓库外，由 deploy/setup_wps_mcp.cmd 安装；调用时会自动拉起 WPS",
    ),
)

SKILL_SPECS: tuple[SkillSpec, ...] = (
    SkillSpec(id="wps-word", name="WPS 文字", icon="W",
              desc="通过自然语言操控 Word 文档：排版、格式、内容编辑",
              category="WPS Office", mcp="wps-office"),
    SkillSpec(id="wps-excel", name="WPS 表格", icon="X",
              desc="通过自然语言操控 Excel：公式编写、数据清洗、图表创建",
              category="WPS Office", mcp="wps-office"),
    SkillSpec(id="wps-ppt", name="WPS 演示", icon="P",
              desc="通过自然语言操控 PPT：排版美化、内容生成、动画设置",
              category="WPS Office", mcp="wps-office"),
    SkillSpec(id="wps-office", name="WPS 跨应用助手", icon="O",
              desc="统一管理 Excel / Word / PPT，处理跨应用操作与通用功能",
              category="WPS Office", mcp="wps-office"),
)

_KIND_SPECS: dict[str, dict[str, McpSpec | SkillSpec]] = {
    "mcp": {s.id: s for s in MCP_SPECS},
    "skill": {s.id: s for s in SKILL_SPECS},
}

_CACHE: dict[str, tuple[float, dict]] = {}


# ---------- 开关持久化 ----------
def mcp_spec(cid: str) -> McpSpec | None:
    """按 id 取 MCP 服务定义（mcp_tools 启动子进程时用）。"""
    return _KIND_SPECS["mcp"].get(cid)


def skill_spec(cid: str) -> SkillSpec | None:
    return _KIND_SPECS["skill"].get(cid)


def state_path() -> Path:
    return load_settings().data_dir / "capabilities.json"


def _load_state() -> dict:
    p = state_path()
    if not p.exists():
        return {"version": 1, "mcp": {}, "skill": {}}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return {"version": 1,
                "mcp": dict(raw.get("mcp") or {}),
                "skill": dict(raw.get("skill") or {})}
    except Exception:
        return {"version": 1, "mcp": {}, "skill": {}}


def _save_state(st: dict) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_on(kind: str, cid: str) -> bool:
    spec = _KIND_SPECS.get(kind, {}).get(cid)
    return bool(spec.default_on) if spec else False


def is_enabled(kind: str, cid: str) -> bool:
    """能力是否开启（未显式设置过 -> 取 spec 默认，即默认全开）。"""
    st = _load_state()
    bucket = st.get(kind) or {}
    if cid in bucket:
        return bool(bucket[cid])
    return _default_on(kind, cid)


def set_enabled(kind: str, cid: str, enabled: bool) -> dict:
    if cid not in _KIND_SPECS.get(kind, {}):
        return {"ok": False, "error": f"未知能力：{kind}/{cid}"}
    st = _load_state()
    st.setdefault(kind, {})[cid] = bool(enabled)
    _save_state(st)
    _CACHE.pop(kind + ":" + cid, None)   # 开关变化 -> 状态缓存失效
    return {"ok": True, "kind": kind, "id": cid, "enabled": bool(enabled)}


# ---------- 依赖探测 ----------
def _node_exe() -> str | None:
    return shutil.which("node")


def _powershell_exe() -> str | None:
    return shutil.which("powershell") or shutil.which("pwsh")


def _bridge_ping(timeout: float = 20.0) -> tuple[bool, str]:
    """跑 wps-com.ps1 的 ping（纯 no-op，不碰 COM、不会拉起 WPS）。"""
    ps = _powershell_exe()
    script = wps_root() / "wps-office-mcp" / "scripts" / "wps-com.ps1"
    if not ps or not script.exists():
        return False, "桥接脚本缺失"
    try:
        r = subprocess.run(
            [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
             "-Action", "ping", "-Params", "{}"],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        if r.returncode == 0 and '"success": true' in (r.stdout or "").replace('"success":true', '"success": true'):
            return True, "COM 桥接就绪"
        return False, (r.stdout or r.stderr or "无输出").strip()[:120]
    except subprocess.TimeoutExpired:
        return False, f"桥接探测超时（{timeout:.0f}s）"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _wps_running() -> list[str]:
    """tasklist 一次拿到 WPS 三件套运行状态（wps/et/wpp）。"""
    try:
        r = subprocess.run(["tasklist", "/NH", "/FO", "CSV"],
                           capture_output=True, text=True, timeout=15,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or "").lower()
        return [n for n in ("wps.exe", "et.exe", "wpp.exe") if '"' + n + '"' in out]
    except Exception:
        return []


def _mods_ok(mods: tuple[str, ...]) -> tuple[bool, str]:
    """检查一批 python 模块是否可导入（失败返回第一个缺的名字）。"""
    import importlib.util

    for m in mods:
        try:
            if importlib.util.find_spec(m) is None:
                return False, m
        except Exception:
            return False, m
    return True, ""


def _mcp_tools(spec: McpSpec) -> list[str]:
    """真做一次 MCP 握手拿工具清单（慢，长缓存；失败返回 []）。"""
    key = "tools:" + spec.id
    hit = _CACHE.get(key)
    now = time.time()
    if hit and now - hit[0] < _TOOLS_CACHE_TTL:
        return hit[1].get("tools", [])
    try:
        from edu_agent import mcp_tools
        tools = mcp_tools.list_tools(spec.id, timeout=25.0)
    except Exception:
        tools = []
    _CACHE[key] = (now, {"tools": tools})
    return tools


def _probe_mcp(spec: McpSpec, deep: bool = False) -> dict:
    """探测单个 MCP 服务：产物/运行时/桥接/进程；deep=True 时附带工具清单。"""
    key = "mcp:" + spec.id
    now = time.time()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < _MCP_CACHE_TTL and not deep:
        base = dict(hit[1])
    else:
        base = {"running": False, "detail": "", "tools": None}
        ok_client, miss = _mods_ok(("mcp",) + tuple(spec.requires))
        if not ok_client:
            base["detail"] = f"缺依赖 {miss}（.venv 里 pip install {miss}）"
        elif not spec.entry().exists():
            where = ("deploy\\setup_wps_mcp.cmd" if spec.id == "wps-office"
                     else str(spec.entry()))
            base["detail"] = "未安装（先跑 " + where + "）"
        elif spec.kind == "node" and not _node_exe():
            base["detail"] = "未检测到 Node.js"
        elif spec.probe == "wps-bridge":
            ok, msg = _bridge_ping()
            apps = _wps_running()
            base["running"] = ok
            base["wps_apps"] = apps
            if ok:
                base["detail"] = ("WPS 运行中（" + "/".join(a.replace('.exe', '') for a in apps) + "）"
                                  if apps else "桥接就绪 · WPS 未启动（导出时自动拉起）")
            else:
                base["detail"] = msg
        else:
            base["running"] = True
            base["detail"] = "入口就绪"
        _CACHE[key] = (now, dict(base))
    out = dict(base)
    out["tools"] = len(_mcp_tools(spec)) if deep else None
    return out


def _skill_files(spec: SkillSpec) -> dict:
    """读 skills/<id>/SKILL.md 的 front-matter（name/description）。"""
    p = wps_skills_dir() / spec.id / "SKILL.md"
    info = {"path": str(p), "exists": p.exists(), "size": 0}
    if p.exists():
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
            info["size"] = len(txt)
            for line in txt.splitlines()[:12]:
                if line.startswith("name:"):
                    info["name"] = line.split(":", 1)[1].strip()
                elif line.startswith("description:"):
                    info["desc"] = line.split(":", 1)[1].strip()
        except Exception:
            pass
    return info


# ---------- 对外快照 ----------
def snapshot(deep: bool = False) -> dict:
    """全部能力 + 开关 + 状态（右栏面板 / MCP 服务视图 / Skill 市场共用）。"""
    mcp_rows = []
    for spec in MCP_SPECS:
        en = is_enabled("mcp", spec.id)
        st = _probe_mcp(spec, deep=deep) if en else {"running": False, "detail": "已关闭", "tools": None}
        mcp_rows.append({
            "id": spec.id, "name": spec.name, "desc": spec.desc, "note": spec.note,
            "kind": spec.kind, "probe": spec.probe,
            "enabled": en, "running": bool(st.get("running")), "detail": st.get("detail", ""),
            "tools": st.get("tools"), "wps_apps": st.get("wps_apps", []),
            "entry": str(spec.entry()), "entry_exists": spec.entry().exists(),
        })
    skill_rows = []
    for spec in SKILL_SPECS:
        en = is_enabled("skill", spec.id)
        files = _skill_files(spec)
        bound = spec.mcp
        bound_en = is_enabled("mcp", bound) if bound else True
        skill_rows.append({
            "id": spec.id, "name": spec.name, "desc": spec.desc or files.get("desc", ""),
            "category": spec.category, "icon": spec.icon, "mcp": bound,
            "enabled": en, "active": en and bound_en,
            "installed": files["exists"], "size": files["size"], "path": files["path"],
        })
    return {"mcp": mcp_rows, "skills": skill_rows,
            "wps_export_ready": wps_available()[0],
            "state_file": str(state_path())}


def wps_available() -> tuple[bool, str]:
    """WPS 导出可用性：开关开着 + 入口构建好 + 桥接通。"""
    if not is_enabled("mcp", "wps-office"):
        return False, "WPS Office 服务已在「MCP 服务」中关闭"
    spec = _KIND_SPECS["mcp"]["wps-office"]
    st = _probe_mcp(spec)
    if not st.get("running"):
        return False, str(st.get("detail") or "WPS 桥接不可用")
    return True, "就绪"
