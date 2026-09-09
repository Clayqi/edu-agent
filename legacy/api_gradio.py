# -*- coding: utf-8 -*-
"""Harness 风格界面（左侧会话栏 + 顶部窄栏 + 聊天气泡）双独立 Agent。

布局：
  [左侧会话栏] 新建会话 / 历史会话列表（点击切换，各自线程记忆）
  [顶部窄栏]   标题 | 当前 Agent（A 答疑多轮/B 教案/自动）| 教案模板 | 
  [主区]      聊天气泡（用户右·主蓝；Agent 左·深面板）
  [底部]      输入框 + 发送；折叠区 Word .docx 模板认定
会话存储于进程内（SESSIONS），重启即清；A 多轮经 chat.py 线程记忆。
"""
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import gradio as gr

from edu_agent import planner, plan_html
from edu_agent.generate import ask_stream
from edu_agent.template_spec import (
    get_template, list_templates, recognize_docx, save_template, set_current,
    template_sketch,
)

QA_EXAMPLES = [
    "函数的单调性怎么判断？",
    "用定义作差判断时最需要注意什么？",
    "帮我用作差法证明 y=1/x 在 (0,+∞) 单调递减",
]

# ---------------- 会话存储（持久化到磁盘，刷新/重启可恢复） ----------------
SESSIONS_FILE = ROOT / "data" / "sessions.json"


def _load_sessions() -> None:
    if SESSIONS_FILE.exists():
        try:
            raw = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
            SESSIONS.update(raw)
        except Exception:
            pass


def _persist() -> None:
    try:
        SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        slim = {sid: {"thread": s["thread"], "title": s["title"], "messages": s["messages"][-40:],
                    "last_md": s.get("last_md", ""), "last_title": s.get("last_title", "")}
                for sid, s in list(SESSIONS.items())[-30:]}
        SESSIONS_FILE.write_text(json.dumps(slim, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


SESSIONS: dict = {}
_load_sessions()  # 启动时恢复上次会话


def _new_session() -> dict:
    sid = uuid.uuid4().hex[:12]
    SESSIONS[sid] = {"thread": uuid.uuid4().hex, "title": "新会话", "messages": []}
    return sid


def _first_sid() -> str:
    if not SESSIONS:
        return _new_session()
    return next(reversed(list(SESSIONS.keys())))


def _choices(value: str = "") -> list:
    out = []
    for sid, s in SESSIONS.items():
        out.append((s["title"], sid))
    if not any(sid == value for sid in SESSIONS):
        value = ""
    return out


def _tag(mode: str) -> str:
    return "Agent A · 课本教练（答疑）" if mode == "coach" else "Agent B · 教案 Agent"


def _agent_code(label: str) -> str:
    label = (label or "").strip()
    if label in ("A", "B", "auto"):
        return label
    if "B" in label:
        return "B"
    if "自动" in label:
        return "auto"
    return "A"


def _respond_once(sess: dict, text: str, agent: str, template_id: str):
    sess["messages"].append({"role": "user", "content": text})
    if sess["title"] == "新会话":
        sess["title"] = text.strip().splitlines()[0][:18]
    agent = _agent_code(agent)
    try:
        if agent == "A":
            from edu_agent.chat import ask_chat

            out = ask_chat(text, thread_id=sess["thread"])
            answer = out.get("answer", "")
            mode = "coach"
        elif agent == "B":
            if "|" in text:
                kp, goal = [p.strip() for p in text.split("|", 1)]
            else:
                kp, goal = text, ""
            rec = planner.make_plan(kp, goal or "", template=template_id or "")
            answer = planner.to_markdown(rec)
            mode = "plan"
        else:
            from edu_agent import graph

            res = graph.ask(text)
            mode = res.get("mode", "coach")
            answer = res.get("output_md", "")
        sess["messages"].append({"role": "assistant", "content": "**【" + _tag(mode) + "】**\n\n" + (answer or "(空)")})
    except Exception as e:
        sess["messages"].append({"role": "assistant", "content": "⚠️ 出错：" + type(e).__name__ + ": " + str(e)})
    return sess["messages"]


def on_load():
    """页面加载/刷新时恢复当前会话内容。"""
    sid = _first_sid()
    msgs = SESSIONS.get(sid, {}).get("messages", [])
    return msgs, sid, gr.update(choices=_choices(sid), value=sid)


def _assistant_tag(mode: str) -> str:
    return "**【Agent A · 课本教练（答疑）】**\n\n" if mode == "A" else "**【Agent B · 教案 Agent】**\n\n"


def on_send(messages, text, agent, template_id, active_sid,
            style="默认", length="标准"):
    """流式对话轮：A 分支边读边出（ask_stream），B 占位后整份教案。

    输出 5 元组：(chatbot, 输入框, 会话列表, active_sid, 状态监控条)
    状态条贯穿全程：检索中 -> 生成中 -> ✅ 完成(耗时/字数/估算token)。
    """
    text = (text or "").strip()
    sid = active_sid if active_sid in SESSIONS else _first_sid()
    sess = SESSIONS[sid]
    upd = gr.update(choices=_choices(sid), value=sid)
    t0 = time.time()
    if not text:
        yield (messages or []), "", upd, sid, ""
        return

    sess["messages"].append({"role": "user", "content": text})
    if sess["title"] == "新会话":
        sess["title"] = text.strip().splitlines()[0][:18]

    agent = _agent_code(agent)
    if agent == "auto":
        from edu_agent.graph import PLAN_HINTS

        agent = "B" if any(h in text for h in PLAN_HINTS) else "A"

    def view(cur: str) -> list:
        shown = list(sess["messages"])
        if cur:
            shown.append({"role": "assistant", "content": cur})
        return shown

    def stat(msg: str) -> str:
        return "%s · ⏱ %.0fs" % (msg, time.time() - t0)

    def est_tokens(in_chars: int, out_chars: int) -> int:
        # 估算：中文约 1 字≈0.8 token，英文词≈1.3 token；无 API usage 时的近似
        return max(1, int(in_chars * 0.8 + out_chars * 0.8))

    if agent == "A":
        from edu_agent.memory import profile_memory_prefix, record_sections

        history = sess["messages"][:-1][-4:]
        prefix = profile_memory_prefix("default")
        cur = "⏳ 检索教材中…"
        yield view(cur), "", upd, sid, stat("⏳ 检索中…")
        got_text = False
        acc = ""
        shown_len = 0
        try:
            for ev in ask_stream(text, history=history, memory_prefix=prefix):
                ty = ev.get("type")
                if ty == "status":
                    yield view(cur), "", upd, sid, stat("⏳ " + ev.get("text", ""))
                elif ty == "delta":
                    if not got_text:
                        acc = ""
                        got_text = True
                        cur = ""
                    acc += ev.get("text", "")
                    if len(acc) - shown_len >= 90:
                        shown_len = len(acc)
                        yield view(acc), "", upd, sid, stat("✍️ 生成中…")
                elif ty == "done":
                    answer = ev.get("answer_md") or ""
                    try:
                        record_sections("default", ev.get("citations") or [])
                    except Exception:
                        pass
                    if not answer:
                        answer = cur if cur else "（无内容）"
                    sess["messages"].append({
                        "role": "assistant",
                        "content": _assistant_tag("A") + answer,
                    })
                    toks = est_tokens(len(text) + 3000, len(answer))
                    yield view(None), "", upd, sid, (
                        "✅ 完成 · %.1fs · 正文 %d 字 · 估算 token ≈%d"
                        % (time.time() - t0, len(answer), toks))
                    _persist()
                    return
        except Exception as e:
            sess["messages"].append({"role": "assistant", "content": "⚠️ A 出错：" + type(e).__name__ + ": " + str(e)})
        _persist()
        yield view(None), "", upd, sid, "✅ 完成 · %.1fs" % (time.time() - t0)
        return

    # B（教案，JSON 结构化整份出）与 auto（同步路由）：占位 + 状态推进
    label = "教案" if agent == "B" else "路由"
    cur = "⏳ 正在检索并生成%s（约 1~4 分钟）…" % label
    yield view(cur), "", upd, sid, stat("⏳ 检索中…")
    done_stat = "✅ 完成 · %.1fs" % (time.time() - t0)
    try:
        if agent == "B":
            if "|" in text:
                kp, goal = [x.strip() for x in text.split("|", 1)]
            else:
                kp, goal = text, ""
            rec = planner.make_plan(
                kp, goal or "", template=template_id or "",
                style="" if style == "默认" else style,
                length="" if length == "标准" else length)
            md = planner.to_markdown(rec)
            sess["last_md"] = md
            sess["last_title"] = rec.title or (kp + "教案")
            sess["messages"].append({"role": "assistant", "content": _assistant_tag("B") + md})
            toks = est_tokens(len(kp) + len(goal) + 4000, len(md))
            done_stat = ("✅ 教案完成 · %.1fs · %d 字 · 估算 token ≈%d"
                         % (time.time() - t0, len(md), toks))
        else:
            from edu_agent import graph

            res = graph.ask(text)
            mode = res.get("mode", "coach")
            answer = res.get("output_md", "")
            sess["messages"].append({"role": "assistant", "content": "**【" + _tag(mode) + "】**\n\n" + (answer or "(空)")})
    except Exception as e:
        sess["messages"].append({"role": "assistant", "content": "⚠️ %s 出错：%s: %s" % (label, type(e).__name__, str(e))})
        done_stat = "⚠️ 出错：" + type(e).__name__
    _persist()
    yield view(None), "", upd, sid, done_stat


def on_feedback(messages, useful, active_sid):
    """记录最近一条回答的有用/无用反馈（存会话 meta + 提示）。"""
    sid = active_sid if active_sid in SESSIONS else _first_sid()
    sess = SESSIONS[sid]
    last = ""
    for m in reversed(sess.get("messages", [])):
        if m.get("role") == "assistant":
            last = (m.get("content") or "")[:80]
            break
    sess.setdefault("feedback", []).append({
        "useful": useful, "preview": last, "at": time.strftime("%H:%M:%S")})
    tag = "有用 👍" if useful else "无用 👎"
    return "已记录（%s）：%s…（反馈存会话内；攒够样本后可接入长期记忆做针对性改进）" % (tag, last)


def on_fix(messages, fix, agent, template_id, active_sid, style="默认", length="标准"):
    """按修正要求重做上一条回答。

    A：修正作为新一轮对话（带上下文，走完整流式）；
    B：取最近知识点，修正要求并入目标重新生成教案（JSON 整份出）。
    输出与 on_send 相同 5 元组。
    """
    fix = (fix or "").strip()
    sid = active_sid if active_sid in SESSIONS else _first_sid()
    sess = SESSIONS[sid]
    upd = gr.update(choices=_choices(sid), value=sid)
    if not fix:
        yield (messages or []), "", upd, sid, "⚠️ 请先输入修正要求"
        return
    if _agent_code(agent) == "B":
        last_user = next((m["content"] for m in reversed(sess.get("messages", []))
                          if m.get("role") == "user"), "")
        kp = last_user.split("|")[0].strip() if last_user else fix
        goal = "修正上一条教案：" + fix
        t0 = time.time()
        cur = "⏳ 按修正要求重新生成教案…"
        yield view_like(sess, cur), "", upd, sid, "⏳ 修正重做中…"
        try:
            rec = planner.make_plan(
                kp, goal, template=template_id or "",
                style="" if style == "默认" else style,
                length="" if length == "标准" else length)
            md = planner.to_markdown(rec)
            sess["last_md"] = md
            sess["last_title"] = rec.title or (kp + "教案")
            sess["messages"].append({"role": "assistant", "content": _assistant_tag("B") + md})
            stat = "✅ 修正完成 · %.1fs · %d 字" % (time.time() - t0, len(md))
        except Exception as e:
            sess["messages"].append({"role": "assistant", "content": "⚠️ 修正出错：" + type(e).__name__ + ": " + str(e)})
            stat = "⚠️ 修正出错"
        _persist()
        yield view_like(sess, None), "", upd, sid, stat
        return
    # A / auto：修正作为新对话轮走完整流式（history 自动带上下文）
    yield from on_send(messages, "【请修正你上一条回答】" + fix, "A",
                       template_id, sid, style, length)


def view_like(sess, cur):
    shown = list(sess["messages"])
    if cur:
        shown.append({"role": "assistant", "content": cur})
    return shown


def on_new():
    sid = _new_session()
    _persist()
    return [], "", gr.update(choices=_choices(sid), value=sid), sid, ""


def on_select(value):
    sid = value
    msgs = SESSIONS.get(sid, {}).get("messages", [])
    return msgs, sid, ""


def on_download_plan(sid):
    """把最近一份 B 教案导出为 HTML 文件（Word 可直接打开）。"""
    sess = SESSIONS.get(sid, {})
    md = sess.get("last_md") or ""
    title = sess.get("last_title") or "教案"
    if not md:
        return None
    try:
        path = plan_html.save_html(md, title)
        return str(path)
    except Exception as e:
        return None


def on_upload_template(file):
    if not file:
        return "请选择 Word .docx。", gr.update()
    try:
        spec = recognize_docx(file)
        save_template(spec, file)
        set_current(spec.template_id)
        return "✅ 已认定并设为当前模板：\n\n" + template_sketch(spec), gr.update(
            choices=_choices(), value=spec.template_id
        )
    except Exception as e:
        return "⚠️ 认定失败：" + type(e).__name__ + ": " + str(e), gr.update()


def on_show_template(template_id: str):
    t = get_template(template_id or "default")
    return "当前模板：" + t.name + "（" + str(len(t.blocks)) + " 板块）\n\n" + template_sketch(t)


_LOG_FILE = ROOT / "logs" / "ui.log"


def on_logs():
    """读运行日志尾部（logsetup 滚动文件，EDU_LOG_FILE=logs/ui.log）。"""
    try:
        if not _LOG_FILE.exists():
            return "（暂无日志——启动时未配置 log_file）"
        lines = _LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-40:])
    except Exception as e:
        return "读取日志失败：" + str(e)


# ---------- 语音输入（本地 faster-whisper，无网络；模型已缓存 ~/.cache/huggingface） ----------
_whisper = None


def _get_whisper():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel

        _whisper = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper


def _resample16k(data, sr: int):
    """线性插值重采样到 16kHz（faster-whisper 输入要求）。"""
    import numpy as np

    if sr == 16000:
        return data
    x = np.arange(len(data))
    n = max(1, int(len(data) * 16000.0 / sr))
    xi = np.linspace(0, len(data) - 1, n)
    return np.interp(xi, x, data).astype(np.float32)


def on_audio(audio):
    """浏览器录音 -> 中文文本（填入输入框）。audio=(sr, np.float32 mono)。"""
    try:
        if audio is None:
            return gr.update()
        import numpy as np

        sr, data = audio
        if data is None or len(data) == 0:
            return gr.update()
        if data.ndim > 1:
            data = data.mean(axis=1)
        wav = _resample16k(np.asarray(data, dtype=np.float32), int(sr))
        segs, _info = _get_whisper().transcribe(wav, language="zh")
        text = "".join(s.text for s in segs).strip()
        return gr.update(value=text) if text else gr.update()
    except Exception:
        # 语音失败静默（用户可打字）；不打断主链路
        return gr.update()


UI_CSS = """
:root {
  --h-bg: #f4f6f9; --h-panel: #ffffff; --h-panel2: #f8fafc;
  --h-border: #e2e8f0; --h-border2: #cbd5e1;
  --h-fg: #1e293b; --h-muted: #64748b; --h-accent: #2563eb;
}
body, .gradio-container { background: var(--h-bg) !important; color: var(--h-fg); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif !important; }
.gradio-container { max-width: 1200px !important; margin: 0 auto !important; }
.sidebar { background: var(--h-panel) !important; border-right: 1px solid var(--h-border) !important; height: calc(100vh - 8px); overflow-y: auto; border-radius: 0 !important; }
.topbar { background: var(--h-panel) !important; border-bottom: 1px solid var(--h-border) !important; border-radius: 0 !important; }
.topbar h3 { font-weight: 700 !important; letter-spacing: .3px; }
#chatbot, .chatbot { background: transparent !important; border: none !important; }
.statusbar { font-size: 12px !important; color: var(--h-muted) !important; min-height: 18px !important; margin: 2px 0 6px 0 !important; }
.message-row.user .message, .user-message, .message.user { background: var(--h-accent) !important; color: #fff !important; border-radius: 14px 14px 4px 14px !important; border: none !important; box-shadow: 0 1px 2px rgba(37,99,235,.25) !important; }
.message-row.bot .message, .bot-message, .message.bot { background: var(--h-panel) !important; color: var(--h-fg) !important; border: 1px solid var(--h-border) !important; border-radius: 14px 14px 14px 4px !important; box-shadow: 0 1px 2px rgba(15,23,42,.05) !important; }
.gradio-container .prose pre, pre { background: #f1f5f9 !important; border: 1px solid var(--h-border) !important; border-radius: 8px !important; color: var(--h-fg) !important; }
.gradio-container a { color: var(--h-accent) !important; }
button.primary { background: var(--h-accent) !important; border: none !important; color: #fff !important; }
textarea, input { background: var(--h-panel) !important; color: var(--h-fg) !important; border: 1px solid var(--h-border2) !important; border-radius: 10px !important; }
.block { border-radius: 12px !important; }
footer { display: none !important; }
"""

HAR_THEME = gr.themes.Soft(primary_hue="blue", neutral_hue="gray").set(
    body_background_fill="#f4f6f9",
    block_background_fill="#ffffff",
    block_border_color="#e2e8f0",
    body_text_color="#1e293b",
    body_text_color_subdued="#64748b",
    border_color_primary="#cbd5e1",
    color_accent_soft="#eff6ff",
    code_background_fill="#f1f5f9",
)

with gr.Blocks(title="课本教练 × 教案 Agent") as demo:
    with gr.Row(elem_classes="topbar"):
        gr.Markdown("### 📖 课本教练 × 教案 Agent", scale=2)
        agent = gr.Dropdown(
    choices=[("A · 课本教练（答疑）", "A"), ("B · 教案 Agent", "B"), ("自动路由", "auto")],
    value="A", label="Preset", interactive=True, scale=1,
)
        tpl = gr.Dropdown(choices=[(t["name"] + "（" + str(t["blocks"]) + "板块）", t["template_id"]) for t in list_templates()], value="default", label="教案模板", scale=1)
    with gr.Row():
        with gr.Column(scale=1, min_width=210, elem_classes="sidebar"):
            btn_new = gr.Button("＋ 新建会话", variant="primary")
            sess_list = gr.Radio(choices=_choices(), value=_first_sid(), label="会话", interactive=True)
        with gr.Column(scale=6):
            chatbot = gr.Chatbot(height=540, label="对话")
            with gr.Row():
                msg_text = gr.Textbox(placeholder="输入后回车；B 模式可写：知识点 | 教学问题/目标", scale=8, show_label=False)
                send = gr.Button("发送", variant="primary", scale=1)
                stop = gr.Button("⏹ 停止", scale=1)
            mic_audio = gr.Audio(sources=["microphone"], type="numpy",
                                 label="🎤 语音输入（说完自动填入，本地识别无网络）")
            with gr.Row():
                style_sel = gr.Dropdown(["默认", "传统", "探究式", "项目式"], value="默认",
                                        label="教案风格（B）", scale=1)
                length_sel = gr.Dropdown(["简短", "标准", "详细"], value="标准",
                                         label="教案篇幅（B）", scale=1)
            with gr.Row():
                btn_useful = gr.Button("👍 有用", size="sm", scale=1)
                btn_useless = gr.Button("👎 无用", size="sm", scale=1)
                fix_text = gr.Textbox(placeholder="反馈/修正：如「目标太宽泛，改成行为动词描述」", scale=6, show_label=False)
                btn_fix = gr.Button("↩ 按修正重做", size="sm", scale=1)
            status_bar = gr.Markdown("", elem_classes="statusbar")
            gr.Examples(examples=QA_EXAMPLES, inputs=msg_text, label="追问示例")
            dplan = gr.DownloadButton("⬇ 下载教案(HTML·Word可开)", variant="secondary", size="sm")
            with gr.Accordion("🛠 运行日志（debug，检索/生成事件）", open=False):
                with gr.Row():
                    log_refresh = gr.Button("🔄 刷新", size="sm")
                    log_text = gr.Textbox(lines=8, max_lines=14, show_label=False, interactive=False)
            with gr.Accordion("教案模板管理（Word .docx 认定）", open=False):
                with gr.Row():
                    tpl_file = gr.File(file_types=[".docx"], label="上传模板 .docx")
                    btn_up = gr.Button("认定并设为当前", variant="primary")
                tpl_preview = gr.Markdown()
                with gr.Row():
                    btn_show = gr.Button("查看当前模板板块")

    active_sid = gr.State(value=_first_sid())

    demo.load(fn=on_load, outputs=[chatbot, active_sid, sess_list])
    dplan.click(on_download_plan, inputs=active_sid, outputs=dplan)

    send_inputs = [chatbot, msg_text, agent, tpl, active_sid, style_sel, length_sel]
    send_outputs = [chatbot, msg_text, sess_list, active_sid, status_bar]
    send_ev = send.click(on_send, inputs=send_inputs, outputs=send_outputs)
    submit_ev = msg_text.submit(on_send, inputs=send_inputs, outputs=send_outputs)
    # 停止：cancel 掉正在跑的 send/submit 生成器，状态条提示
    stop.click(lambda: "⏹ 已停止（本次回答中断）", inputs=None, outputs=status_bar,
               cancels=[send_ev, submit_ev])
    btn_useful.click(lambda m, s: on_feedback(m, True, s),
                     inputs=[chatbot, active_sid], outputs=status_bar)
    btn_useless.click(lambda m, s: on_feedback(m, False, s),
                      inputs=[chatbot, active_sid], outputs=status_bar)
    btn_fix.click(on_fix,
                  inputs=[chatbot, fix_text, agent, tpl, active_sid, style_sel, length_sel],
                  outputs=[chatbot, fix_text, sess_list, active_sid, status_bar])
    btn_new.click(on_new, outputs=[chatbot, msg_text, sess_list, active_sid, status_bar])
    sess_list.select(on_select, inputs=sess_list, outputs=[chatbot, active_sid, status_bar])
    btn_up.click(on_upload_template, inputs=tpl_file, outputs=[tpl_preview, tpl])
    btn_show.click(on_show_template, inputs=tpl, outputs=tpl_preview)
    log_refresh.click(on_logs, outputs=log_text)
    mic_audio.stop(on_audio, inputs=mic_audio, outputs=msg_text)


def _warmup():
    """启动后台预热：ollama bge-m3 + local rerank 模型一次性加载常驻。

    把冷启动（embedding ~3s / CrossEncoder 2.2GB 10-30s）从"用户首问"挪到
    "服务启动期"，闲置后首问不再卡。任何失败静默（预热只是优化，不是依赖）。
    """
    import os
    import threading

    def _run():
        try:
            from edu_agent.config import get_embeddings
            get_embeddings().embed_query("课本教练预热")
        except Exception:
            pass
        if os.environ.get("RERANK_ON") == "1":
            try:
                from sentence_transformers import CrossEncoder
                d = os.environ.get("RERANK_MODEL_DIR") or str(ROOT / "model_cache" / "bge-reranker-v2-m3")
                CrossEncoder(d)
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()


if __name__ == "__main__":
    try:
        from edu_agent import logsetup

        logsetup.setup(level="INFO", log_file=str(_LOG_FILE))
    except Exception:
        pass
    _warmup()
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=False, show_error=True, css=UI_CSS, theme=HAR_THEME)
