"""用户上传 PDF：本地解析 -> 独立向量库（user_pdfs），支持按来源问答。"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "data" / "pdfs"          # 原件
VDB_DIR = ROOT / "data" / "user_pdf_db"   # 独立向量库
META = ROOT / "data" / "pdf_sources.json"
COLLECTION = "user_pdfs"


def list_sources() -> list[dict]:
    if META.exists():
        try:
            return json.loads(META.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_meta(items: list[dict]):
    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def _clean(text: str) -> str:
    text = re.sub(r"[\ue000-\uf8ff]", "", text)
    return text


def ingest_pdf(file_bytes: bytes, filename: str) -> dict:
    """保存原件 -> pymupdf 抽文本 -> 按行切块(<=1000) -> 入 user_pdfs 库。"""
    import pymupdf

    from langchain_chroma import Chroma

    from edu_agent.config import get_embeddings

    stem = Path(filename).stem
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    VDB_DIR.mkdir(parents=True, exist_ok=True)
    orig = PDF_DIR / filename
    orig.write_bytes(file_bytes)

    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    n_pages = doc.page_count

    chunks: list[dict] = []
    cur = ""
    cur_page = 1
    def push(page_no: int):
        nonlocal cur
        if cur.strip():
            chunks.append({"page": page_no, "text": cur.strip()})
            cur = ""
    for i in range(n_pages):
        txt = _clean(doc[i].get_text())
        for line in txt.splitlines():
            s = line.strip()
            if not s:
                continue
            if len(cur) + len(s) + 1 > 1000:
                push(cur_page)
                cur_page = i + 1
            cur = (cur + "\n" + s) if cur else s
    push(cur_page)

    from langchain_core.documents import Document

    docs, ids = [], []
    for k, c in enumerate(chunks, 1):
        md = {"source": stem, "kind": "pdf", "subject": "user-pdf", "book": filename,
              "chapter": "", "section": "", "heading": "", "page": c["page"], "anchor": ""}
        docs.append(Document(page_content=c["text"], metadata=md))
        ids.append(hashlib.md5((stem + str(k)).encode("utf-8")).hexdigest()[:16])

    emb = get_embeddings()
    if VDB_DIR.exists() and (VDB_DIR / "chroma.sqlite3").exists():
        store = Chroma(persist_directory=str(VDB_DIR), embedding_function=emb, collection_name=COLLECTION)
        store.add_documents(documents=docs, ids=ids)
        count = store._collection.count()
    else:
        store = Chroma.from_documents(documents=docs, embedding=emb, ids=ids,
                                      persist_directory=str(VDB_DIR), collection_name=COLLECTION)
        count = store._collection.count()

    meta = [m for m in list_sources() if m.get("source") != stem]
    meta.append({"source": stem, "file": filename, "pages": n_pages, "chunks": len(chunks), "total": count})
    _save_meta(meta)
    return {"source": stem, "file": filename, "pages": n_pages, "chunks": len(chunks), "total": count}


def ask_pdf_summary():
    return list_sources()
