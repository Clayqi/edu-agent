# -*- coding: utf-8 -*-
"""操作权限（动作级授权）—— 2026-09-12，对齐 DeepSeek / Claude Code 那类「动手之前先问你一声」。

和 capabilities.py 的区别（两者别混）：
- capabilities.py：**服务/能力**级开关（WPS MCP、edu-math…）——粒度是"整套能力开不开"
- permissions.py：**动作**级策略（导出 Word/PPT、新建项目、删模板、写向量库…）
  ——每个动作三态：allow（直接做）/ ask（弹一次确认再做）/ deny（禁止）

为什么需要它：agent 现在能落盘、建目录、删模板、写本地向量库 —— 这些是**有副作用**的动作。
默认策略是：只读动作 allow，有副作用的动作 ask（第一次让你看见它到底要动什么），
用户可在界面里逐条改成 allow/deny，落盘 data/permissions.json（与代码分离、可回滚）。

调用方（web_server）用法：
    blocked = permissions.guard("export_pptx", confirm=bool(body.get("confirm")))
    if blocked:
        return blocked          # {"ok": False, "gate": "permission", ...} → 前端确认后带 confirm=true 重试
"""
from __future__ import annotations

import json
import threading
import time

from edu_agent.config import load_settings

POLICY_FILE = load_settings().data_dir / "permissions.json"
VALID = ("allow", "ask", "deny")

# 动作登记表：id 一旦上线别改（前端/日志/权限文件都用它）；default 只影响"用户没表过态"的动作
ACTIONS: list[dict] = [
    {"id": "export_docx", "label": "导出教案为 Word（.docx）", "risk": "write", "default": "ask"},
    {"id": "export_pptx", "label": "导出教案为 PPT（.pptx）", "risk": "write", "default": "ask"},
    {"id": "project_new", "label": "新建项目（在本地建目录）", "risk": "write", "default": "ask"},
    {"id": "template_save", "label": "保存 / 覆盖教案模板", "risk": "write", "default": "ask"},
    {"id": "template_delete", "label": "删除教案模板", "risk": "destructive", "default": "ask"},
    {"id": "pdf_ingest", "label": "上传 PDF 并写入本地向量库", "risk": "write", "default": "ask"},
    {"id": "file_open", "label": "用本机 WPS / 默认程序打开文件", "risk": "local", "default": "allow"},
]

_BY_ID = {a["id"]: a for a in ACTIONS}
_lock = threading.Lock()


def _load() -> dict:
    try:
        data = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
        return {k: v for k, v in (data.get("actions") or {}).items()
                if k in _BY_ID and v in VALID}
    except Exception:  # noqa: BLE001  文件缺失/损坏 → 回默认策略，绝不让权限层把应用卡死
        return {}


def _save(overrides: dict) -> None:
    POLICY_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = POLICY_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"updated": time.time(), "actions": overrides},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(POLICY_FILE)


def list_policies() -> list[dict]:
    """所有动作 + 当前生效策略（含未表态时用的默认值）。"""
    with _lock:
        over = _load()
    out = []
    for a in ACTIONS:
        cur = over.get(a["id"], a["default"])
        out.append({**a, "policy": cur, "explicit": a["id"] in over})
    return out


def policy(action_id: str) -> str:
    """某动作当前策略；未知动作按 deny 处理（白名单式，避免新动作默认放开）。"""
    if action_id not in _BY_ID:
        return "deny"
    with _lock:
        over = _load()
    return over.get(action_id, _BY_ID[action_id]["default"])


def set_policy(action_id: str, value: str) -> dict:
    if action_id not in _BY_ID:
        return {"ok": False, "error": f"未知动作：{action_id}"}
    if value not in VALID:
        return {"ok": False, "error": f"策略只能是 {VALID} 之一"}
    with _lock:
        over = _load()
        over[action_id] = value
        _save(over)
    return {"ok": True, "action": action_id, "policy": value}


def reset() -> None:
    """清空用户表态，回到登记表默认值（调试/恢复用）。"""
    with _lock:
        _save({})


def guard(action_id: str, confirm: bool = False) -> dict | None:
    """执行前检查：返回 None 表示放行；否则返回要回给前端/调用方的闸门信息。

    confirm=True 表示"用户已经确认过这一次"（由前端在弹窗后重试时带上）。
    """
    p = policy(action_id)
    a = _BY_ID.get(action_id) or {"label": action_id, "risk": "unknown"}
    if p == "allow":
        return None
    if p == "deny":
        return {"ok": False, "gate": "permission", "action": action_id, "policy": "deny",
                "label": a["label"], "error": f"该操作已被禁用：{a['label']}（可在「权限」里改回）"}
    if confirm:
        return None
    return {"ok": False, "gate": "permission", "action": action_id, "policy": "ask",
            "label": a["label"], "need": "confirm",
            "hint": f"这一步会：{a['label']}。确认后我会照做（下次可在「权限」里改成总是允许）。"}
