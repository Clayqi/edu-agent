# -*- coding: utf-8 -*-
"""语料乱码清洗 v2：修正 front-matter 误删；垃圾行剔除 + 字形映射。"""
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

# 仓库根 = 本脚本上溯一级（scripts/ → 仓库根）；不写死盘符，换机器/换目录都能跑
ROOT = Path(__file__).resolve().parents[1] / "content" / "structured_auto"

def fullwidth_map():
    m = {}
    for i in range(26):
        m[chr(ord("ａ") + i)] = chr(ord("a") + i)
        m[chr(ord("Ａ") + i)] = chr(ord("A") + i)
    for i in range(10):
        m[chr(ord("０") + i)] = chr(ord("0") + i)
    for f, t in [("（", "("), ("）", ")"), ("＝", "="), ("＋", "+"), ("－", "-"),
                 ("＜", "<"), ("＞", ">"), ("，", ","), ("。", "."), ("；", ";"),
                 ("：", ":"), ("？", "?"), ("！", "!"), ("×", "x")]:
        m[f] = t
    return m

FM = fullwidth_map()
GLYPH = {k: v for k, v in {
    "狓": "x", "狔": "y", "犃": "A", "犅": "B", "犆": "C", "犇": "D",
    "犈": "E", "犉": "F", "犌": "G", "犎": "H", "犐": "I", "犑": "J",
    "犓": "K", "犔": "L", "犕": "M", "犖": "N", "犗": "O", "犘": "P",
    "犙": "Q", "犚": "R", "犛": "S", "犜": "T", "犝": "U", "犞": "V",
    "犟": "W", "犠": "X", "犡": "Y", "犢": "Z",
    "犪": "a", "犫": "b", "犮": "c", "犱": "d", "犲": "e", "犳": "f",
    "犵": "g", "犺": "h", "犻": "i", "犼": "j", "犽": "k", "犾": "l",
    "犿": "m", "狅": "n", "狆": "o", "狇": "p", "狉": "q", "狊": "r",
    "狋": "s", "狌": "t", "狏": "u", "狑": "v", "狓": "x", "狔": "y", "狕": "z",
}.items()}

def clean_chars(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 0xE000 <= o <= 0xF8FF or 0x200B <= o <= 0x200F:
            continue
        if ch in FM:
            ch = FM[ch]
        elif ch in GLYPH:
            ch = GLYPH[ch]
        out.append(ch)
    return "".join(out)

GOOD = set("，。；：？！、（）《》【】.,;:?!()<>[]{}+-=*/%^_#@$~…→∈⊆∪∩≠≤≥√π°Δσρβαθφωλ")
def good_ratio(s):
    if not s:
        return 0.0
    good = 0
    for ch in s:
        o = ord(ch)
        if ch == " " or 0x4E00 <= o <= 0x9FFF or (ch.isascii() and (ch.isalnum() or ch in GOOD)):
            good += 1
    return good / len(s)

removed_lines = 0
removed_blocks = 0
total_blocks = 0
for f in sorted(ROOT.glob("*.md")):
    lines = f.read_text(encoding="utf-8").splitlines()
    # front matter
    fm = []
    rest = lines
    if lines and lines[0].strip() == "---":
        close = 1
        while close < len(lines) and lines[close].strip() != "---":
            close += 1
        fm = lines[: close + 1]
        rest = lines[close + 1 :]
    out = list(fm)
    header = None
    buf = []
    def flush(hdr, body_lines):
        global removed_lines, removed_blocks
        body = "\n".join(clean_chars(x) for x in body_lines)
        kept = [ln for ln in body.splitlines() if good_ratio(ln) >= 0.5]
        removed_lines += len(body_lines) - len(kept)
        if hdr and len("\n".join(kept).strip()) >= 40:
            out.append(hdr)
            out.extend(kept)
        else:
            removed_blocks += 1
    for line in rest:
        if line.startswith("【"):
            if header is not None or buf:
                flush(header, buf)
            header = line
            buf = []
            total_blocks += 1
        else:
            buf.append(line)
    if header is not None or buf:
        flush(header, buf)
    f.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("cleaned", f.name)

print(f"\nblocks={total_blocks} removed_blocks={removed_blocks} removed_lines={removed_lines}")
