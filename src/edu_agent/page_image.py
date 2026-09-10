"""教材页图渲染（2026-09-10 P0：公式/图象抽不到时「直接引用图片」）。

设计（对齐 George 的要求：不要编，直接给原书那一页）：
  - 页码口径：教材用**引用里的印刷页码**（前端 citation 的 page），
    物理页 = 印刷页 + offset（ingest 实测 offset=5，1 基物理页即 +6，见 web_server._TXT_OFF）；
    上传 PDF 用**物理页**（pdf_upload 入库时记的就是 1 基物理页），offset=0。
  - 渲染：pymupdf，默认 150dpi PNG（够看清公式，单页 ~200-400KB）。
  - 缓存：data/page_cache/<key>.png；key 含 PDF 路径哈希+物理页+dpi；
    PDF 文件比缓存新则自动重渲染（防"换了教材还在贴旧图"）。
  - 只读：不改 PDF、不改向量库；渲染产物全部落在 data/ 下。

被 web_server 的 GET /api/page_image 调用。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "page_cache"


def cache_key(pdf_path: Path, physical_page: int, dpi: int, prefix: str = "tb") -> str:
    h = hashlib.sha1(str(pdf_path).encode("utf-8")).hexdigest()[:8]
    return f"{prefix}-{h}-p{physical_page}-{dpi}dpi"


def get_page_image(pdf_path: Path | str | None, page: int, offset: int = 0,
                   dpi: int = 150, prefix: str = "tb") -> tuple[bytes, Path, int]:
    """渲染一页为 PNG。返回 (png_bytes, 缓存文件, 实际物理页)。

    page   : 印刷页（教材，配合 offset）或物理页（上传件，offset=0）
    offset : page + offset = 物理页（1 基）
    异常   : FileNotFoundError（PDF 缺失）/ IndexError（页码越界）/ RuntimeError（渲染失败）
    """
    import pymupdf

    if not pdf_path:
        raise FileNotFoundError("PDF 未配置")
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(f"PDF 不存在: {pdf}")

    phys = int(page) + int(offset)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = CACHE_DIR / (cache_key(pdf, phys, dpi, prefix) + ".png")
    if out.exists() and out.stat().st_mtime >= pdf.stat().st_mtime:
        return out.read_bytes(), out, phys

    doc = pymupdf.open(str(pdf))
    try:
        if not (1 <= phys <= doc.page_count):
            raise IndexError(f"页码 {page}(物理页 {phys}) 超出范围 1..{doc.page_count}")
        pix = doc[phys - 1].get_pixmap(dpi=int(dpi))
        data = pix.tobytes("png")
    finally:
        doc.close()
    if not data:
        raise RuntimeError("渲染结果为空")
    out.write_bytes(data)
    return data, out, phys


def pdf_meta(pdf_path: Path | str) -> dict:
    """页数等元信息（自检/接口回显用）。"""
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    try:
        return {"pages": doc.page_count, "file": Path(pdf_path).name}
    finally:
        doc.close()
