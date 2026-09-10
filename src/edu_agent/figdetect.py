"""片段「图形/公式图片 + 文字层保真度」体检（2026-09-10 P0）。

背景（George 2026-09-10 报的问题）：教材里公式/图象是图片，PDF 文字层抽不到；
更糟的是文字层本身有损（度符号抽成字母 c、艺术字小节号变 "511!"），
模型读到半截乱码后会"顺手补全" -> 幻觉。

本模块提供两个能力：
  1) figure_info(text)：给一个片段打标
       has_figure  是否涉及教材图形/公式图片（正文引用图X.Y，或该页含位图）
       fig_nums    引用到的图号（"5.11,5.13"）—— 给模型"只指路不复述"
       fidelity    文字层保真度 high|low（low = 照抄必错）
       low_reasons 低保真的具体指纹（日志/调试用）
  2) 供入库回填（scripts/backfill_chunk_meta.py）与运行时兜底（generate.py）共用，
     避免"入库一个口径、生成另一个口径"。

低保真指纹全部来自 2026-09-10 实测（D:\\教育agent\\data\\logs\\hermes-verify-formula-audit-*.log）。
"""
from __future__ import annotations

import re

# 全角 -> 半角（原书图号是 图５．１１ 这种全角写法）
_FW = str.maketrans("０１２３４５６７８９．", "0123456789.")

# 图号：图5.11 / 图 5.11 / 图５．１１
FIG_RE = re.compile(r"图\s?([0-9０-９]{1,2})\s?[.．]\s?([0-9０-９]{1,2})")

# 文字层损坏指纹（低保真）：pattern -> 人话原因
_LOW_FID: list[tuple[re.Pattern, str]] = [
    (re.compile(r"[0-9]\s?c\b"), "度符号被抽成字母 c（原书 750° 在库里是 “750c”）"),
    (re.compile(r"[0-9]{3,4}!"), "艺术字小节号乱码（原书 5.1.1 在库里是 “511!”）"),
    (re.compile(r"[\ue000-\uf8ff\ufffd]"), "私用区/替换字符"),
    (re.compile(r"[\u0000-\u0008\u000b-\u001f]"), "控制字符"),
    (re.compile(r"[#\$]{2,}"), "装饰符乱码（原书小节标题在库里是 “\"#$” 之类）"),
]


def fig_nums(text: str) -> list[str]:
    """抽出片段里引用的图号（去重、保序、最多 6 个）。"""
    out: list[str] = []
    for m in FIG_RE.finditer(text or ""):
        num = (m.group(1) + "." + m.group(2)).translate(_FW)
        if num not in out:
            out.append(num)
    return out[:6]


def low_fidelity_reasons(text: str) -> list[str]:
    """返回低保真原因列表（空 = 文字层看起来干净）。"""
    t = text or ""
    return [why for pat, why in _LOW_FID if pat.search(t)]


def figure_info(text: str, page_has_images: bool = False) -> dict:
    """片段打标。page_has_images：该片段起始页在 PDF 里是否含位图（入库时可由 pymupdf 给出）。"""
    figs = fig_nums(text)
    reasons = low_fidelity_reasons(text)
    return {
        "has_figure": bool(figs) or bool(page_has_images),
        "fig_nums": ",".join(figs),
        "fidelity": "low" if reasons else "high",
        "low_reasons": reasons,
        "page_has_images": bool(page_has_images),
    }
