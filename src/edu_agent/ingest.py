"""S5 实现：content/structured/*.md -> Document(metadata) -> Chroma 持久化。

产物格式契约见 content/README.md（v2）：
文件级 YAML front-matter + 逐条 \`【概念|例题|习题】chunk_id|section|heading|page|anchor\`。
结构化产物一段即一条 chunk，不做二次切分。

用法：
    python -m edu_agent.ingest            # 默认读 config 的 content_dir -> chroma_db_dir
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from edu_agent.config import load_settings  # noqa: E402

# kind 标记 -> metadata.kind
# 概念/例题/习题：人工精修细卡；整节：PDF 自动切节粗卡（content/structured_auto/）
KIND_MARKERS: dict[str, str] = {
    "概念": "concept",
    "例题": "example",
    "习题": "exercise",
    "整节": "section",
}

# 头行：^【概念|例题|习题|整节】chunk_id|section|heading|page|anchor
_HEADER_RE = re.compile(
    r"^【(?P<kind>概念|例题|习题|整节)】\s*(?P<cid>[^|]+)"
    r"\s*\|\s*(?P<section>[^|]*)"
    r"\s*\|\s*(?P<heading>[^|]*)"
    r"\s*\|\s*(?P<page>[^|]*)"
    r"\s*\|\s*(?P<anchor>[^|]*)\s*$"
)


@dataclass
class Chunk:
    chunk_id: str
    kind: str
    text: str
    subject: str
    book: str
    version: str
    chapter: str
    section: str = ""
    heading: str = ""
    page: int | None = None
    anchor: str = ""


def _parse_front_matter(block: str) -> dict[str, str]:
    """解析 YAML 子集 front-matter（key: value 行）。"""
    fm: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip()
    return fm


def _to_page(raw: str) -> int | None:
    s = raw.strip().lower().lstrip("p页:")
    if s.isdigit():
        return int(s)
    return None


def parse_file(path: Path) -> list[Chunk]:
    """解析单个结构化 md 文件 -> Chunk 列表（保持文件内顺序）。"""
    raw = Path(path).read_text(encoding="utf-8")
    # 拆 front-matter 与正文
    lines = raw.splitlines()
    fm: dict[str, str] = {}
    if lines and lines[0].strip() == "---":
        end = 1
        while end < len(lines) and lines[end].strip() != "---":
            end += 1
        fm = _parse_front_matter("\n".join(lines[1:end]))
        body = lines[end + 1:]
    else:
        body = lines

    chunks: list[Chunk] = []
    current: Chunk | None = None
    for line in body:
        m = _HEADER_RE.match(line.strip())
        if m:
            if current is not None:
                chunks.append(current)
            current = Chunk(
                chunk_id=m.group("cid").strip(),
                kind=KIND_MARKERS[m.group("kind")],
                text="",
                subject=fm.get("subject", ""),
                book=fm.get("book", ""),
                version=fm.get("version", ""),
                chapter=fm.get("chapter", ""),
                section=m.group("section").strip(),
                heading=m.group("heading").strip(),
                page=_to_page(m.group("page")),
                anchor=m.group("anchor").strip(),
            )
        else:
            if current is not None:
                current.text += line + "\n"
    if current is not None:
        chunks.append(current)
    for c in chunks:
        c.text = c.text.strip()
    return chunks


def to_documents(chunks: list[Chunk]):
    from langchain_core.documents import Document

    docs = []
    for c in chunks:
        docs.append(
            Document(
                page_content=c.text,
                metadata={
                    "chunk_id": c.chunk_id,
                    "kind": c.kind,
                    "subject": c.subject,
                    "book": c.book,
                    "version": c.version,
                    "chapter": c.chapter,
                    "section": c.section,
                    "heading": c.heading,
                    "page": c.page,
                    "anchor": c.anchor,
                },
            )
        )
    return docs


def _split_long_sections(chunks: list[Chunk], limit: int = 1400) -> list[Chunk]:
    """整节粗卡超长时按段落切块（<=limit 字/块），同一节各块共享元数据。

    参照计划：某节 >1500 字按段切 2~3 块；命中后检索可带上整节上下文。
    """
    from dataclasses import replace

    out: list[Chunk] = []
    for c in chunks:
        if c.kind != "section" or len(c.text) <= limit:
            out.append(c)
            continue
        # PDF 正文几乎无空行 -> 按行累积切块（含超长单行硬切兜底）
        blocks: list[str] = []
        cur = ""
        for line in c.text.split("\n"):
            piece = line.strip()
            if not piece:
                continue
            if cur and len(cur) + len(piece) + 1 > limit:
                blocks.append(cur)
                cur = piece
            else:
                cur = (cur + "\n" + piece) if cur else piece
            while len(cur) > limit:  # 超长单行兜底
                blocks.append(cur[:limit])
                cur = cur[limit:]
        if cur:
            blocks.append(cur)
        for i, b in enumerate(blocks, 1):
            out.append(replace(c, chunk_id=f"{c.chunk_id}-p{i}", text=b.strip()))
    return out


def ingest(content_dir: Path | None = None, chroma_dir: Path | None = None,
           auto_content_dir: Path | None = None) -> int:
    """入库全部结构化 chunk，返回入库条数。

    来源双轨：
      content/structured/        人工精修细卡（concept/example/exercise）
      content/structured_auto/   PDF 自动整节粗卡（section）
    幂等：每次全量重建 collection（先清空向量库目录），内容变了重跑即可。
    """
    from langchain_chroma import Chroma

    from edu_agent.config import get_embeddings

    s = load_settings()
    content_dir = Path(content_dir or s.content_dir)
    auto_dir = Path(auto_content_dir or s.auto_content_dir)
    chroma_dir = Path(chroma_dir or s.chroma_db_dir)

    md_files = sorted(content_dir.glob("*.md")) + sorted(auto_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"{content_dir} 与 {auto_dir} 下都没有 *.md 结构化产物")

    all_chunks: list[Chunk] = []
    for f in md_files:
        parsed = parse_file(f)
        if parsed:
            print(f"  {f.name}: {len(parsed)} chunks")
            all_chunks.extend(parsed)
    all_chunks = _split_long_sections(all_chunks)

    ids = [c.chunk_id for c in all_chunks]
    if len(set(ids)) != len(ids):
        dup = [i for i in ids if ids.count(i) > 1]
        raise ValueError(f"chunk_id 重复: {sorted(set(dup))}")

    import shutil

    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)  # 全量重建，避免重复/脏数据
    docs = to_documents(all_chunks)
    _ = Chroma.from_documents(
        documents=docs,
        embedding=get_embeddings(),
        ids=ids,
        persist_directory=str(chroma_dir),
        collection_name="edu_textbook",
        collection_metadata={"hnsw:space": "cosine"},
    )
    return len(docs)


def main() -> None:
    s = load_settings()
    print(f"ingest: {s.content_dir} -> {s.chroma_db_dir}")
    n = ingest()
    print(f"入库完成：{n} 条 (ids 去重后 {n})")
    # S5 验收：抽查 3 条 metadata
    from langchain_chroma import Chroma

    from edu_agent.config import get_embeddings

    db = Chroma(
        persist_directory=str(s.chroma_db_dir),
        embedding_function=get_embeddings(),
        collection_name="edu_textbook",
    )
    samples = db.get(include=["metadatas"], limit=3)["metadatas"]
    for md in samples:
        print("  抽查:", {k: md.get(k) for k in ("chunk_id", "kind", "chapter", "page", "anchor")})


if __name__ == "__main__":
    main()
