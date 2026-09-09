# -*- coding: utf-8 -*-
"""为 structured_auto/*.md 补回 front-matter（文件名推导章信息）。"""
import re
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\教育agent\content\structured_auto")
SUBJECT_MAP = {"数学": "数学", "物理": "物理", "化学": "化学"}
for f in sorted(ROOT.glob("*.md")):
    text = f.read_text(encoding="utf-8")
    if text.lstrip().startswith("---"):
        print("skip(ok)", f.name)
        continue
    m = re.match(r"^(.+?)_(第[一二三四五六七八九十]+章)_(.+?)_auto\.md$", f.name)
    if not m:
        print("?? name not parseable:", f.name)
        continue
    bookish, chapter, title = m.group(1), m.group(2), m.group(3)
    subject = next((k for k in SUBJECT_MAP if k in bookish), bookish)
    fm = f"""---
subject: {subject}
book: 必修第一册
version: 人教A版2019课标版
chapter: {chapter}
chapter_title: {title}
---
"""
    f.write_text(fm + text, encoding="utf-8")
    print("fixed", f.name)
