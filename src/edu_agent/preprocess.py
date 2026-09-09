"""工程补强(2026-09-07)：查询预处理 —— 编号/术语/结构问法识别。

目标（缺失项 #4 -> 影响「结构问法系统性失败」）：
  学生常按"课本坐标"提问："4.2 例 2 怎么做"、"第三章 第 3 题"、"p45 的练习"、
  "课本 3.2.1 单调性"。这类问法若整句丢进 embedding 检索，常因冗词/编号噪音
  匹配不到对应节块而系统性失败。本模块负责把坐标识别出来：
    1) 章节/页码/题号 坐标解析（arabic + 中文数字）；
    2) 教材术语归一（口语/别名 -> 课本用词），用于改写检索 query；
    3) 输出结构化提示语（hints），让生成阶段知道学生在问哪节/哪题。

设计原则：不改动 AnswerRecord 契约；识别结果只用于 *检索增强* 与 *提示增强*；
检索为空时回退到原文整句检索（安全兜底，见 generate.ask）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------- 中文数字 ----------
_CN = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
       "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_CN10 = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


def cn_to_int(s: str) -> int | None:
    """中文数字(1~99) -> int；非数字串返回 None。"""
    s = s.strip()
    if not s or not all(ch in _CN for ch in s):
        return None
    if "十" in s:
        parts = s.split("十")
        tens = _CN[parts[0]] if parts[0] else 1
        ones = _CN[parts[1]] if len(parts) > 1 and parts[1] else 0
        return tens * 10 + ones
    return _CN[s[-1]]


def int_to_cn_chapter(n: int) -> str:
    """阿拉伯数字章节号 -> 元数据里的章名形式（第三章/第十一章/第二十章）。"""
    if n <= 10:
        return "第" + _CN10[n - 1] + "章"
    if n < 20:
        return "第十" + _CN10[n - 11] + "章"
    t, o = divmod(n, 10)
    return "第" + _CN10[t - 1] + "十" + (_CN10[o - 1] if o else "") + "章"


# ---------- 教材术语归一表（口语/别名 -> 课本用词） ----------
# 只做"同义改写"以贴近教材用语；不影响"答案以检索片段为准"的诚实性。
TERM_MAP = [
    # 集合与逻辑
    (r"充分必要条件", "充分条件与必要条件"),
    (r"充要条件", "充要条件"),
    (r"子集|包含关系", "集合间的基本关系"),
    (r"并起来|并在一块", "并集"),
    (r"交起来|公共部分", "交集"),
    (r"补集|全集", "补集"),
    # 函数
    (r"单调(?!性)|增减性|上升|下降的", "单调性"),
    (r"增函数", "增函数"),
    (r"减函数", "减函数"),
    (r"奇偶(?!性)", "奇偶性"),
    (r"最大(值)?|最小(值)?|最值", "函数的最值"),
    (r"反函数", "反函数"),
    (r"指数函数与对数函数的关系", "指数函数与对数函数"),
    (r"幂函数", "幂函数"),
    (r"零点(?!存在性定理)", "函数的零点"),
    (r"二分法", "用二分法求方程的近似解"),
    # 三角函数
    (r"任意角", "任意角"),
    (r"弧度(?!制)", "弧度制"),
    (r"三角函数线|单位圆定义", "任意角的三角函数"),
    (r"诱导公式", "诱导公式"),
    (r"周期函数|周期性", "正弦函数、余弦函数的性质"),
    (r"对称轴|对称中心", "正弦函数、余弦函数的图象"),
    (r"正切(?!函数)", "正切函数的性质与图象"),
    (r"函数y=Asin", "函数y=Asin(ωx+φ)"),
    # 基本不等式
    (r"基本不等式|均值不等式", "基本不等式"),
    (r"ab≤|小于等于.*二分之", "基本不等式"),
]

_TERM_RULES = [(re.compile(p), r) for p, r in TERM_MAP]


def normalize_terms(q: str) -> str:
    """把口语/别名替换为教材用词（用于检索 query）。找不到就不动。"""
    out = q
    for pat, repl in _TERM_RULES:
        out = pat.sub(repl, out)
    return out


# ---------- 坐标解析 ----------
@dataclass
class Ref:
    chapter: str | None = None       # "第三章"（元数据同形）
    section: str | None = None       # "3.2" / "3.2.1"（元数据同形）
    page: int | None = None          # 第 45 页
    item: str | None = None          # "例 2" / "练习 3" / "习题 1" / "第 5 题"
    label: str | None = None         # 提示语（给 LLM/学生看的坐标描述）


@dataclass
class Processed:
    original: str
    query: str                       # 供检索：术语归一 + 去噪音 + 坐标词保留
    ref: Ref
    hints: list[str] = field(default_factory=list)  # 追加给生成阶段的结构提示
    qtype: str = "general"

    def __post_init__(self):
        if self.ref and (self.ref.chapter or self.ref.section or self.ref.item or self.ref.page):
            parts = []
            if self.ref.chapter:
                parts.append(self.ref.chapter)
            if self.ref.section:
                parts.append(self.ref.section + " 节")
            if self.ref.item:
                parts.append(self.ref.item)
            if self.ref.page:
                parts.append("第 " + str(self.ref.page) + " 页")
            self.hints.append("学生问题指向：" + "，".join(parts) + "，优先按该坐标定位教材内容。")


_CH_RE = re.compile(r"第\s*([一二三四五六七八九十0-9]+)\s*章")
_SEC_RE = re.compile(r"(?<!\d)(\d{1,2})\.(\d{1,2})(?:\.(\d{1,2}))?\s*(节)?")
_PAGE_RE = re.compile(r"[Pp]\s*(\d{1,3})|第\s*(\d{1,3})\s*页")
_ITEM_RE = re.compile(r"(例|练习|习题|例题)\s*(\d{1,2}(?:\.\d{1,2})?)|第\s*(\d{1,2})\s*题")


def parse_refs(q: str) -> Ref:
    """解析坐标：章/节/页码/题号。全部可选；解析不到即 None。"""
    ref = Ref()
    m = _CH_RE.search(q)
    if m:
        raw = m.group(1)
        n = int(raw) if raw.isdigit() else cn_to_int(raw)
        if n is not None:
            ref.chapter = int_to_cn_chapter(n)
    m = _SEC_RE.search(q)
    if m:
        a, b, c = m.group(1), m.group(2), m.group(3)
        ref.section = f"{a}.{b}" if not c else f"{a}.{b}.{c}"
    m = _PAGE_RE.search(q)
    if m:
        v = m.group(1) or m.group(2)
        ref.page = int(v)
    m = _ITEM_RE.search(q)
    if m:
        it = m.group(1)
        v = m.group(2) or m.group(3)
        if it:
            ref.item = f"{it} {v}"
        else:
            ref.item = f"第 {v} 题"
    return ref


def preprocess(question: str, qtype: str | None = None) -> Processed:
    """主入口：解析坐标 + 术语归一 + 生成检索 query。

    检索 query 策略：
      - 若识别到坐标(节/章/题号)或术语可归一 -> query 用 归一化正文 + 坐标片段；
      - 否则原样返回（普通问法交给 embedding 语义检索即可）。
    """
    q = question.strip()
    ref = parse_refs(q)
    norm = normalize_terms(q)
    if ref.section:
        norm = norm.replace(ref.section, ref.section + " ", 1)
    query = re.sub(r"\s+", " ", norm).strip()
    qtype = qtype or classify_question(question)
    p = Processed(original=question, query=query or question, ref=ref, qtype=qtype)
    return p


def classify_question(question: str) -> str:
    """结构问法分类（轻量启发式，供检索 kind 过滤使用）。"""
    q = question
    if re.search(r"(怎么解|求解|计算|已知|求证|证明|若|则|等于|求值|变式|原题|例\s*\d|练习\s*\d|习题\s*\d|第\s*\d+\s*题)", q):
        return "problem"
    if re.search(r"(是什么|什么是|啥是|何为|定义|性质|概念|区别|关系|怎么判断|为什么|如何|图象|图像)", q):
        return "concept"
    return "general"


def kind_filter_for(qtype: str) -> list[str] | None:
    """与 classify 配对：当前库主为 kind=section 整节块，先放宽过滤。"""
    if qtype == "problem":
        return ["example", "exercise", "section"]
    if qtype == "concept":
        return ["concept", "section"]
    return None
