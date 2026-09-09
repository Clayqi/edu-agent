"""Agent B · 教案 HTML 输出（可直接在 Word 打开/打印）。

plan_to_html(markdown, title) -> 自包含 HTML（UTF-8 + A4 打印 CSS + 原生表格）。
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown as md_lib

ROOT = Path(__file__).resolve().parents[2]

_CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "Songti SC","SimSun","STSong","Microsoft YaHei",serif; color:#1a1a1a; font-size:14px; line-height:1.8; max-width:820px; margin:0 auto; padding:24px; background:#fff; }
h1 { font-size:20px; text-align:center; margin:6px 0 2px; letter-spacing:1px; }
h2 { font-size:16px; border-bottom:1.5px solid #333; padding-bottom:4px; margin:22px 0 10px; }
h3 { font-size:15px; margin:16px 0 6px; }
table { border-collapse: collapse; width:100%; margin:8px 0; font-size:13.5px; }
th, td { border:1px solid #444; padding:5px 8px; text-align:left; vertical-align:top; }
th { background:#f0f0f0; }
blockquote { border-left:3px solid #999; margin:8px 0; padding:2px 12px; color:#555; background:#fafafa; }
strong { color:#000; }
pre { background:#f5f5f5; border:1px solid #ddd; padding:8px; font-family:Consolas,monospace; font-size:12.5px; white-space:pre-wrap; }
.meta { text-align:center; color:#666; font-size:12.5px; margin:2px 0 18px; }
.cite { color:#666; font-size:12.5px; }
hr { border:none; border-top:1px dashed #bbb; margin:18px 0; }
"""


def plan_to_html(markdown_text: str, title: str = "教案", subtitle: str = "依据教材生成") -> str:
    body = md_lib.markdown(markdown_text or "", extensions=["tables", "fenced_code", "sane_lists"])
    body = re.sub(r"<h1[^>]*>(.*?)</h1>", lambda m: f"<h1>{m.group(1)}</h1>", body)
    html = (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<title>" + _esc(title) + "</title>\n<style>" + _CSS + "</style>\n</head>\n<body>\n"
        "<h1>" + _esc(title) + "</h1>\n"
        "<div class=\"meta\">" + _esc(subtitle) + "</div>\n"
        + body +
        "\n</body>\n</html>\n"
    )
    return html


def save_html(markdown_text: str, title: str, out_dir: Path | None = None, subtitle: str = "依据人教A版教材生成") -> Path:
    out_dir = out_dir or (ROOT / "content" / "plans")
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[\\/:*?\"<>|\s]+", "_", title)[:50] or "教案"
    path = out_dir / f"{safe}.html"
    path.write_text(plan_to_html(markdown_text, title, subtitle), encoding="utf-8")
    return path


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
