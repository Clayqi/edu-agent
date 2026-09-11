"""Agent Web 网关（唯一 UI 后端，端口 5174，同源免 CORS）。

第一阶段收口后的定位（对照 DSH：host 与网关分工）：
  - 会话状态：host.store.SessionStore（SQLite 持久化），不再有模块级全局
    SESSIONS dict / JSON 全量覆写；旧 web_sessions.json 首次启动自动迁移。
  - 意图路由：routing.decide 单一来源；本文件不再自带关键词表。
  - 本文件只做：静态托管 + 参数校验 + 把请求分派给 Agent 层
    （generate/planner/supervisor），业务逻辑不在路由函数里长住。

路由面（与旧版完全一致，前端零改动）：
  GET  /                静态前端（static/index.html）
  /api/session/*         会话 CRUD（数据落 data/edu_sessions.db）
  /api/templates|upload|set  模板管理（复用 template_spec）
  /api/chat              流式（A 逐字 / S 总指挥派单 / B 整份教案 + HTML 落盘）
  另：/api/textbook、/api/pdfs、/api/pdf/ingest、/files、/static、/uploads、/textbook

运行：.venv\\Scripts\\python.exe src/edu_agent/web_server.py（或 deploy/start_web.cmd）
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
STATIC = ROOT / "static"

from fastapi import FastAPI, UploadFile, File, Query  # noqa: E402
from fastapi.responses import StreamingResponse, HTMLResponse, Response, JSONResponse, FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from edu_agent import logsetup, pdf_upload, plan_html, planner, routing  # noqa: E402
from edu_agent import capabilities, wps_export  # noqa: E402  能力开关 + WPS 导出
from edu_agent.config import load_settings  # noqa: E402
from edu_agent.host.store import SessionStore  # noqa: E402
from edu_agent.template_spec import (  # noqa: E402
    get_template, list_templates, recognize_docx, save_template, set_current, template_sketch,
)

log = logsetup.get_logger("web_server")

app = FastAPI(title="课本教练 x 教案 Agent")

# ---------- host：会话存储（进程内只保留这一个持久化入口） ----------
_settings = load_settings()
_store = SessionStore(path=_settings.sessions_db,
                      migrate_legacy=ROOT / "data" / "web_sessions.json")


# ---------- 静态 ----------
app.mount("/files", StaticFiles(directory=str(ROOT / "content" / "plans")), name="plans")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

# PDF 源：教材原文（hermes 目录，只读挂载）+ 用户上传
_txt = load_settings().textbook_pdf
_TXT_DIR = _txt.parent if _txt and _txt.exists() else None
if _TXT_DIR is not None:
    app.mount("/textbook", StaticFiles(directory=str(_TXT_DIR)), name="textbook")
_TXT_NAME = _txt.name if _txt else ""
_TXT_OFF = 6  # 印刷页码 -> PDF 物理页(+1) 的偏移
pdf_upload.PDF_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(pdf_upload.PDF_DIR)), name="uploads")


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


# ---------- 模板 ----------
@app.get("/api/templates")
def api_templates():
    cur = get_template("").template_id
    return {"templates": list_templates(), "current": cur}


class TplSet(BaseModel):
    template_id: str = "default"


@app.post("/api/template/set")
def api_tpl_set(body: TplSet):
    set_current(body.template_id)
    return {"ok": True, "current": body.template_id}


@app.post("/api/template/upload")
async def api_tpl_upload(file: UploadFile = File(...)):
    tmp = ROOT / "data" / ("upload_" + uuid.uuid4().hex + ".docx")
    tmp.write_bytes(await file.read())
    try:
        spec = recognize_docx(tmp)
        save_template(spec, tmp)
        set_current(spec.template_id)
        return {"ok": True, "current": spec.template_id, "name": spec.name, "preview": template_sketch(spec)}
    finally:
        tmp.unlink(missing_ok=True)


# ---------- 会话 ----------
@app.post("/api/session/new")
def api_sess_new():
    sid = _store.new()
    return {"id": sid, "title": "新会话"}


@app.post("/api/session/branch")
def api_sess_branch(body: dict):
    """分支：以现有会话的消息副本新建会话（原会话不动）。"""
    sid = body.get("id", "")
    src = _store.get(sid)
    if src is None:
        return {"ok": False, "error": "会话不存在"}
    nsid = _store.new()
    for m in (src.get("messages") or []):
        _store.append(nsid, m.get("role", "user") if m.get("role") in ("user", "assistant") else "user",
                      m.get("content") or "")
    title = (src.get("title") or "").strip()
    if title and title != "新会话":
        _store.rename(nsid, (title + "（分支）")[:18])
    return {"ok": True, "id": nsid}


@app.post("/api/project/new")
def api_project_new(body: dict):
    """新建项目文件夹（防路径穿越）。name=目录名, base=父目录（默认取 settings.fs_root）"""
    name = (body.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "项目名不能为空"}
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    base = _fs_safe((body.get("base") or _FS_ROOT))
    if base is None:
        return {"ok": False, "error": "位置不在允许范围（仅本机 C/D/E 盘）"}
    target = (base / name).resolve()
    if base not in target.parents:
        return {"ok": False, "error": "非法路径"}
    if target.exists():
        if not target.is_dir():
            return {"ok": False, "error": "同名文件已存在"}
        return {"ok": True, "path": str(target), "exists": True}
    target.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "path": str(target), "exists": False}


def _drives() -> list[Path]:
    """探测本机存在的盘（C-Z），作为可浏览根。

    2026-09-10 修正：原写死 "CDEF"，项目迁到 F: 之后其它盘（如移动硬盘 / 网络盘）
    在选择器里根本看不到；改为全盘探测。
    """
    out = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        try:
            p = Path(f"{letter}:/")
            if p.exists():
                out.append(p.resolve())
        except Exception:
            continue
    return out


_FS_BAD = ("$RECYCLE", "System Volume", "Windows", "$WinRE", "Recovery",
           "Program Files", "Program Files (x86)", "ProgramData")

# 「新建项目 / 文件浏览」的默认根目录：来自 settings.fs_root（.env 的 EDU_FS_ROOT 可覆盖）
# 原先写死 "D:/hermes"，团队每人机器目录不同 → 现在默认 = 用户主目录；
# 若显式配置的目录不存在，退回用户主目录，保证前端一定能拿到一个可读的位置
_cfg_fs_root = _settings.fs_root
_FS_ROOT = str(_cfg_fs_root if _cfg_fs_root.exists() else Path.home())


def _fs_safe(p: str) -> Path | None:
    """解析路径并校验在已探测盘根内；过滤系统目录；非法返回 None。"""
    try:
        t = Path(p).resolve()
    except Exception:
        return None
    if not any(str(t).upper().startswith(str(d).upper()) for d in _drives()):
        return None
    if any(t.name.startswith(b) or t.name == b for b in _FS_BAD):
        return None
    return t


@app.get("/api/fs/drives")
def api_fs_drives():
    return {"ok": True, "drives": [str(d) for d in _drives()]}






@app.get("/api/fs/list")
def api_fs_list(path: str = ""):
    """列出目录（只读；限本机盘，系统目录过滤）。path 为空回落到 settings.fs_root。"""
    cur = _fs_safe(path or _FS_ROOT)
    if cur is None:
        return {"ok": False, "error": "路径不在允许范围"}
    try:
        dirs = sorted([d.name for d in cur.iterdir()
                       if d.is_dir() and not d.name.startswith((".", "$"))
                       and not any(d.name.startswith(b) or d.name == b for b in _FS_BAD)],
                      key=str.lower)
    except Exception:
        return {"ok": False, "error": "无法读取目录"}
    parent = None
    if cur != Path(cur.anchor):
        pp = cur.parent.resolve()
        if _fs_safe(str(pp)) is not None:
            parent = str(pp)
    return {"ok": True, "path": str(cur), "parent": parent,
            "dirs": dirs, "roots": [str(d) for d in _drives()]}


@app.post("/api/fs/mkdir")
def api_fs_mkdir(body: dict):
    """在指定目录下新建子文件夹。"""
    base = _fs_safe((body.get("path") or _FS_ROOT))
    name = (body.get("name") or "").strip()
    if base is None:
        return {"ok": False, "error": "路径不在允许范围"}
    if not name:
        return {"ok": False, "error": "名称不能为空"}
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    t = (base / name).resolve()
    if base not in t.parents:
        return {"ok": False, "error": "非法路径"}
    try:
        t.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(t)}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__ + ": " + str(e)}


@app.get("/api/sessions")
def api_sessions():
    return {"list": _store.list_sessions(), "current": _store.current_id()}


@app.post("/api/session/rename")
def api_sess_rename(body: dict):
    sid = body.get("id", "")
    title = (body.get("title") or "新会话")[:18]
    if _store.get(sid) is not None:
        _store.rename(sid, title)
    return {"ok": True}


# ---------- 对话 ----------
class ChatReq(BaseModel):
    text: str
    session_id: str | None = None
    preset: str = "A"          # S | A | B | auto
    template_id: str = "default"
    corpus: str = "textbook"   # textbook | pdf:<source>


def _code(preset: str) -> str:
    if "S" in (preset or "") or "总指挥" in (preset or "") or "监督" in (preset or ""):
        return "S"
    if "B" in (preset or ""):
        return "B"
    if "自动" in (preset or "") or preset == "auto":
        return "auto"
    return "A"


def _tag(mode: str) -> str:
    if mode == "S":
        return "**【总指挥 · 监督 Agent】**\n\n"
    return "**【Agent A · 课本教练（答疑）】**" if mode == "A" else "**【Agent B · 教案 Agent】**"


def _sse(gen):
    def stream():
        for ev in gen:
            yield "data: " + json.dumps(ev, ensure_ascii=False) + "\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")


def _pick_session(req: ChatReq) -> str:
    """选中或新建一个会话（沿用旧语义：缺省取最早会话，无则新建）。"""
    sid = req.session_id or _store.current_id()
    if sid is None or _store.get(sid) is None:
        sid = _store.new()
    return sid


def _chat_gen(req: ChatReq):
    # 注意：这里不能用 logsetup.request（contextvars）包裹整个生成器——
    # SSE 经 Starlette 线程池逐段恢复，每次 next() 在不同 context 副本，
    # __exit__ 的 reset(token) 会抛 "created in a different Context"。
    # 请求级事件改由各 _stream_* 在生成器内直接 logsetup.event 记录（rid 缺省 "-"）。
    text = (req.text or "").strip()
    if not text:
        yield {"t": "error", "text": "输入为空"}
        return

    code = _code(req.preset)
    sid = _pick_session(req)
    _store.append(sid, "user", text)
    _store.set_title_if_new(sid, text.splitlines()[0][:18])
    yield {"t": "session", "id": sid,
           "title": (_store.get(sid) or {}).get("title", "新会话")}

    if code == "auto":
        code = routing.decide(text)

    if code == "A":
        yield from _stream_coach(sid, req, text)
        return
    if code == "S":
        yield from _stream_supervisor(sid, req, text)
        return
    yield from _stream_planner(sid, req, text)


def _stream_coach(sid: str, req: ChatReq, text: str):
    """Agent A（课本教练）：检索 -> 流式逐字（event 面与旧版一致）。"""
    from edu_agent.generate import ask_stream
    from edu_agent.memory import profile_memory_prefix, record_sections

    sess = _store.get(sid) or {"messages": []}
    history = sess["messages"][:-1][-4:]
    prefix = profile_memory_prefix("default") if req.corpus == "textbook" else ""
    src = None
    pdir = None
    pcol = None
    if req.corpus != "textbook" and req.corpus.startswith("pdf:"):
        src = req.corpus.split(":", 1)[1]
        pdir = pdf_upload.VDB_DIR
        pcol = pdf_upload.COLLECTION
        yield {"t": "status", "text": "正在检索 PDF《" + src + "》并作答…"}
    else:
        yield {"t": "status", "text": "正在检索教材并作答…"}
    acc = ""
    final_answer = ""
    citations = []
    try:
        for ev in ask_stream(text, history=history, memory_prefix=prefix, source=src,
                             persist_dir=pdir, collection=pcol):
            ty = ev.get("type")
            if ty == "delta":
                acc += ev.get("text", "")
                yield {"t": "d", "text": ev.get("text", "")}
            elif ty == "done":
                final_answer = ev.get("answer_md") or acc
                citations = ev.get("citations") or []
                record_sections("default", citations)
    except Exception as e:
        yield {"t": "error", "text": "A 出错：" + type(e).__name__ + ": " + str(e)}
        return
    _store.append(sid, "assistant", _tag("A") + final_answer,
                  meta={"mode": "A", "citations": citations,
                        "pages": sorted({c.get("page") for c in citations if c.get("page")})})
    yield {"t": "done", "mode": "A", "text": final_answer, "citations": citations}


def _stream_supervisor(sid: str, req: ChatReq, text: str):
    """总指挥（监督 Agent S）：先出任务计划，再派单 A 或 B（event 面同旧版）。"""
    from edu_agent.supervisor import supervise_stream

    sess_buf = []
    final_text = ""
    citations = []
    html_name = ""
    for ev in supervise_stream(text, template_id=req.template_id or ""):
        ty = ev.get("t")
        if ty == "plan":
            plan_lines = ["[总指挥] 任务计划："]
            for pp in ev.get("plan", []):
                plan_lines.append("- " + pp.get("step", "") + " → " + pp.get("assignee", ""))
            yield {"t": "status", "text": "\n".join(plan_lines)}
        elif ty == "d":
            sess_buf.append(ev.get("text", ""))
            yield {"t": "d", "text": ev.get("text", "")}
        elif ty == "done":
            final_text = ev.get("text") or "".join(sess_buf)
            citations = ev.get("citations") or []
            html_name = ev.get("html") or ""
            _store.set_last_html(sid, html_name)
        elif ty == "error":
            yield ev
            return
    _store.append(sid, "assistant", _tag("S") + final_text,
                  meta={"mode": "S", "citations": citations,
                        "pages": sorted({c.get("page") for c in citations if c.get("page")})})
    yield {"t": "done", "mode": "S", "agent": "A" if not html_name else "B",
           "text": final_text, "citations": citations, "html": html_name}


def _stream_planner(sid: str, req: ChatReq, text: str):
    """Agent B（教案）：整份生成 + HTML 落盘（event 面同旧版）。"""
    yield {"t": "status", "text": "正在检索并生成教案（约 1~4 分钟）…"}
    try:
        if "|" in text:
            kp, goal = [x.strip() for x in text.split("|", 1)]
        else:
            kp, goal = text, ""
        rec = planner.make_plan(kp, goal or "", template=req.template_id or "")
        md = planner.to_markdown(rec)
        html_path = plan_html.save_html(md, rec.title)
        html_name = html_path.name
        _store.set_last_html(sid, html_name)
        _store.append(sid, "assistant", _tag("B") + md,
                      meta={"mode": "B", "citations": [c.model_dump() for c in rec.citations],
                            "pages": sorted({c.page for c in rec.citations if c.page})})
        yield {"t": "done", "mode": "B", "text": md, "html": html_name,
               "title": rec.title, "citations": [c.model_dump() for c in rec.citations]}
    except Exception as e:
        yield {"t": "error", "text": "B 出错：" + type(e).__name__ + ": " + str(e)}


@app.post("/api/chat")
def api_chat(req: ChatReq):
    return _sse(_chat_gen(req))


@app.post("/api/session/last_html")
def api_last_html(body: dict):
    sess = _store.get(body.get("session_id", "")) or {}
    return {"html": sess.get("last_html", "")}


@app.post("/api/session/get")
def api_sess_get(body: dict):
    sess = _store.get(body.get("id", ""))
    if sess is None:
        return {"id": body.get("id", ""), "title": "新会话", "messages": [], "last_html": ""}
    return {"id": sess["id"], "title": sess["title"],
            "messages": sess["messages"], "last_html": sess["last_html"]}


@app.post("/api/session/del")
def api_sess_del(body: dict):
    sid = body.get("id", "")
    if _store.get(sid) is not None:
        _store.delete(sid)
    return {"ok": True, "list": _store.list_sessions(), "current": _store.current_id()}


@app.get("/api/textbook")
def api_textbook():
    return {"file": _TXT_NAME, "offset": _TXT_OFF, "exists": _TXT_DIR is not None}


@app.get("/api/page_image")
def api_page_image(page: int = Query(..., ge=1, le=999), source: str = "", dpi: int = 150):
    """教材/上传 PDF 的某一页渲染成 PNG（引用卡「看原页」，2026-09-10 P0）。

    page   教材 = 引用里的**印刷页码**（内部 +_TXT_OFF 换算物理页）；
           上传件 = **物理页**（pdf_upload 入库记的就是物理页，offset=0）。
    source 上传资料标识（source 或文件名）；空 = 教材原文。
    只读：渲染产物写 data/page_cache/，不动 PDF 与向量库。
    """
    from edu_agent import page_image

    dpi = max(72, min(int(dpi or 150), 300))
    if source:
        hit = next((s for s in pdf_upload.list_sources()
                    if source in (str(s.get("source") or ""), str(s.get("file") or ""))), None)
        if hit is None:
            return JSONResponse({"ok": False, "error": "上传资料不存在"}, status_code=404)
        pdf, off, prefix = pdf_upload.PDF_DIR / str(hit.get("file") or ""), 0, "up"
    else:
        s = load_settings()
        pdf = s.textbook_pdf if (s.textbook_pdf and s.textbook_pdf.exists()) else None
        off, prefix = _TXT_OFF, "tb"
    try:
        data, cache_file, phys = page_image.get_page_image(pdf, page, offset=off, dpi=dpi, prefix=prefix)
    except FileNotFoundError as e:
        return JSONResponse({"ok": False, "error": f"PDF 不可用：{e}"}, status_code=404)
    except IndexError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=404)
    except Exception as e:  # noqa: BLE001 —— 渲染失败不该把网关带崩
        log.warning("page_image failed page=%s: %s", page, e)
        return JSONResponse({"ok": False, "error": f"{type(e).__name__}: {e}"}, status_code=500)
    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400",
                 "X-Physical-Page": str(phys), "X-Cache-File": cache_file.name},
    )


_AUTO_DIR = ROOT / "content" / "structured_auto"
_TOC_FILE = ROOT / "content" / "toc_ranges.json"        # 现行位置（随仓库走）
_TOC_FILE_LEGACY = ROOT / "data" / "toc_ranges.json"    # 旧位置（data/ 不入库，仅本地兼容）


@app.get("/api/textbook/toc")
def api_textbook_toc():
    """教材目录页码范围（由 scripts/build_toc_ranges.py 生成）。

    给「看原页」浏览器用：知道某个知识点在哪一节、这一章从第几页到第几页、全书多少页。
    数据源 = 向量库片段的 chapter/section/page 聚合 + PDF 章首页探测。
    """
    if not _TOC_FILE.exists() and _TOC_FILE_LEGACY.exists():
        return json.loads(_TOC_FILE_LEGACY.read_text(encoding="utf-8"))
    if not _TOC_FILE.exists():
        return JSONResponse({"ok": False, "error": "toc 未生成：请跑 scripts/build_toc_ranges.py"}, status_code=404)
    try:
        return json.loads(_TOC_FILE.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": f"toc 解析失败：{e}"}, status_code=500)


@app.get("/api/textbook/chapters")
def api_textbook_chapters():
    """解析整节教材 md -> 章/节结构（教材库章节浏览）。"""
    out = []
    if not _AUTO_DIR.exists():
        return {"ok": True, "chapters": out}
    for f in sorted(_AUTO_DIR.glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        ch = re.search(r"^chapter:\s*(.+)$", text, re.M)
        ct = re.search(r"^chapter_title:\s*(.+)$", text, re.M)
        bk = re.search(r"^book:\s*(.+)$", text, re.M)
        sections = []
        for line in text.splitlines():
            m = re.match(r"^【整节】([^|\r\n]*)\|([^|]*)\|([^|]*)\|p?([0-9]+)?", line)
            if m:
                sections.append({"id": m.group(1), "no": m.group(2),
                                 "name": m.group(3), "page": int(m.group(4)) if m.group(4) else None})
        out.append({"file": f.name,
                    "chapter": ch.group(1).strip() if ch else "",
                    "title": ct.group(1).strip() if ct else "",
                    "book": bk.group(1).strip() if bk else "",
                    "sections": sections})
    return {"ok": True, "chapters": out}


@app.get("/api/textbook/stats")
def api_textbook_stats():
    """教材知识库统计（块数取自向量库计数）。"""
    blocks = None
    try:
        from langchain_chroma import Chroma
        from edu_agent.config import get_embeddings
        db = Chroma(collection_name="edu_textbook",
                    embedding_function=get_embeddings(),
                    persist_directory=str(ROOT / "chroma_db"))
        blocks = db._collection.count()
    except Exception:
        blocks = None
    n_ch = 0
    if _AUTO_DIR.exists():
        n_ch = len(list(_AUTO_DIR.glob("*.md")))
    return {"ok": True, "book": "数学 · 必修第一册（人教A版2019课标版）",
            "chapters": n_ch, "blocks": blocks,
            "source_pdf": str(ROOT / "content" / "raw") if (ROOT / "content" / "raw").exists() else None}


@app.get("/api/pdfs")
def api_pdfs():
    return {"sources": pdf_upload.list_sources()}


@app.post("/api/pdf/del")
def api_pdf_del(body: dict):
    """删除上传的 PDF 资料（原件 + meta + 向量）。"""
    source = (body.get("source") or "").strip()
    if not source:
        return {"ok": False, "error": "缺少 source"}
    meta = pdf_upload.list_sources()
    hit = next((s for s in meta if s.get("source") == source), None)
    keep = [s for s in meta if s.get("source") != source]
    if hit is None:
        return {"ok": False, "error": "资料不存在"}
    pdf_upload._save_meta(keep)
    try:
        f = pdf_upload.PDF_DIR / (hit.get("file") or "")
        if f.exists():
            f.unlink()
    except Exception:
        pass
    try:
        from langchain_chroma import Chroma
        from edu_agent.config import get_embeddings
        db = Chroma(collection_name=pdf_upload.COLLECTION,
                    embedding_function=get_embeddings(),
                    persist_directory=str(pdf_upload.VDB_DIR))
        db.delete(where={"source": source})
    except Exception:
        pass
    return {"ok": True}


@app.post("/api/pdf/ingest")
async def api_pdf_ingest(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        return {"ok": False, "error": "仅支持 .pdf"}
    data = await file.read()
    try:
        info = pdf_upload.ingest_pdf(data, file.filename or "doc.pdf")
        return {"ok": True, **info}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__ + ": " + str(e)}


# ---------- 能力（MCP 服务 / Skill）：开关 + 运行状态 ----------
@app.get("/api/capabilities")
def api_capabilities(deep: int = 0):
    """能力清单：enabled=开关（默认全开），running/detail=运行状态，tools=工具数（deep=1）。"""
    return capabilities.snapshot(deep=bool(deep))


@app.post("/api/capabilities/toggle")
def api_capabilities_toggle(body: dict):
    """开 / 关一个 MCP 服务或 Skill（落 data/capabilities.json 持久化）。"""
    return capabilities.set_enabled(str(body.get("kind") or ""),
                                    str(body.get("id") or ""),
                                    bool(body.get("enabled")))


@app.get("/api/mcp/status")
def api_mcp_status():
    """右栏「运行状态」面板用的轻量快照（不做工具握手）。"""
    snap = capabilities.snapshot(deep=False)
    return {"mcp": snap["mcp"], "skills": snap["skills"],
            "wps_export_ready": capabilities.wps_available()[0]}


# ---------- WPS 导出（教案中心 -> .docx / .pptx） ----------
@app.post("/api/wps/export")
def api_wps_export(body: dict):
    """教案 -> WPS 文件。payload=教案中心 DZ 模型；markdown=Agent B 教案时改用。

    body: {"payload": {...}, "markdown": "...", "kind": "docx"|"pptx", "outDir": "F:\\导出目录"}
    能力关闭时返回 {ok:false, gate:'capability'}，与 MCP/skill 开关状态一致。
    """
    try:
        return wps_export.export(body.get("payload") or {},
                                 markdown=str(body.get("markdown") or ""),
                                 kind=str(body.get("kind") or "docx").lower(),
                                 out_dir=(body.get("outDir") or "").strip() or None)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": type(e).__name__ + ": " + str(e)}


@app.get("/api/wps/download")
def api_wps_download(path: str = ""):
    """把导出的 Office 文件回传浏览器（前端「下载到本机」按钮用）。"""
    try:
        p = Path(path).resolve()
    except Exception:
        return JSONResponse({"ok": False, "error": "非法路径"}, status_code=400)
    if not p.is_file() or p.suffix.lower() not in (".docx", ".pptx", ".doc", ".ppt", ".pdf"):
        return JSONResponse({"ok": False, "error": "仅支持回传导出的 Office 文件"}, status_code=404)
    return FileResponse(str(p), filename=p.name)


# ---------- 启动预热（自 api.py 移植：embedding + rerank 常驻） ----------
def _warmup() -> None:
    """后台预热 ollama bge-m3 + local rerank 模型（冷启动不卡首问；失败静默）。"""

    def _run():
        try:
            from edu_agent.config import get_embeddings

            get_embeddings().embed_query("课本教练预热")
        except Exception:
            pass
        s = load_settings()
        if s.rerank_on and s.rerank_provider == "local":
            try:
                from sentence_transformers import CrossEncoder

                CrossEncoder(str(s.rerank_model_dir))
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()


if __name__ == "__main__":
    import uvicorn

    # 日志收口：默认 data/logs/edu_agent.log（EDU_LOG_LEVEL / EDU_LOG_FILE 可覆盖）
    s = load_settings()
    logsetup.setup(level=os.getenv("EDU_LOG_LEVEL", "INFO"),
                   log_file=str(s.log_file))
    _warmup()
    uvicorn.run(app, host="127.0.0.1", port=5174, log_level="warning")
