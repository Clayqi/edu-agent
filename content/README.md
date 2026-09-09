# content/ —— 教材结构化产物规范（v3，2026-09-06 择优修订）

> 依据《edu-agent-langchain-plan.md》§4.3 Schema 与 textbook-coach 实测经验。
> **一条知识点/例题/习题 = 一个独立 chunk**；PDF 自动切节的整节粗卡另走 kind=section。

## 首发教材（已定）
- 科目/册：**数学 · 人教A版2019课标版 · 必修第一册**（266 页文字层 PDF）
- 源文件：.env 的 TEXTBOOK_PDF → D:\hermes\textbook-coach\pdfs\数学人教A版必修第一册.pdf（第三方上传、仅本地学习研究，不分发不商用）

## 目录
- raw/：教材原始文件（当前 PDF 在 hermes 侧，仅引用路径）。
- structured/：**人工精修细卡**（kind=concept/example/exercise）——每章一个 md，如 \`数学必修一_第一章_集合与常用逻辑用语.md\`。
- structured_auto/：**PDF 自动切节粗卡**（kind=section）——由 pdf_import.py 产出（如 \`..._第一章_..._auto.md\`），**不要手改**，改源头脚本或重跑即可。

## 自动切节（S2.5，一条命令）
\`\`\`bash
.venv\Scripts\python.exe src\edu_agent\pdf_import.py    # 读 TEXTBOOK_PDF -> structured_auto/
\`\`\`
- 解析目录页（实测每条目跨三行：标题/页码/点线），按第X章分组，印刷页码→物理页偏移自动锚定（实测 +5）。
- 已产出：5 章 52 节。入库时 >1400 字的节自动按行切块（见 ingest._split_long_sections）。

## 文件结构：front-matter + 逐条 chunk
\`\`\`markdown
---
subject: 数学
book: 必修第一册
version: 人教A版2019课标版
chapter: 第一章
chapter_title: 集合与常用逻辑用语
---

【概念】math-m1-c1-s1-k1|1.1|集合的概念|p2|正文
（概念讲解……公式内联 $\\subseteq$）

【例题】math-m1-c1-s2-ex1|1.2|集合间的基本关系|p8|例1
（题干……）解答：（……）

【习题】math-m1-c1-s1-x1|1.1|集合的概念|p6|练习与应用1
（习题题干……）

【整节】math-m1-c1-1_1|1.1|集合的概念|p2|整节正文
（pdf_import 自动产出：整节原文，含例题/练习/小结等，不分 kind）
\`\`\`

## 逐条 chunk 头行格式（正则：^【(概念|例题|习题|整节)】…）
\`\`\`text
【概念】<chunk_id>|<section>|<heading>|<page>|<anchor>
【例题】<chunk_id>|<section>|<heading>|<page>|<anchor>
【习题】<chunk_id>|<section>|<heading>|<page>|<anchor>
【整节】<chunk_id>|<section>|<heading>|<page>|整节正文
\`\`\`
- 五列均以半角 \`|\` 分隔；列内不要出现裸 \`|\`（需要则用全角 ｜）。
- kind 映射：概念→concept、例题→example、习题→exercise、整节→section。
- chunk_id：细卡 \`math-m1-c1-s1-k1\`（概念k/例题ex/习题x+序号）；整节 \`math-m1-c1-1_1\`（入库切块后加 -p1/-p2）。
- page 记印刷页码整数（可带 p 前缀）；anchor 如 例1/正文/练习与应用1/整节正文。
- **正文** = 头行后连续文本直到下一个 \`【\` 行或文件尾；正文内可含空行与 LaTeX。

## 入库后的 Document.metadata（ingest.py 生成）
\`\`\`json
{ "chunk_id": "math-m1-c3-s2-k1", "kind": "concept",
  "subject": "数学", "book": "必修第一册", "version": "人教A版2019课标版",
  "chapter": "第三章", "section": "3.2",
  "heading": "函数的基本性质", "page": 76, "anchor": "正文" }
\`\`\`

## 已知边界（重要，演示预期管理）
- **公式是图片/字形替换**：PDF 抽出的文字里数学符号为替换字形（如 狓 犃 犖）或缺失——叙述文字完整可读；
  公式类讲解靠"页码翻书"兜底（答案明确给 册/章/节/页码，公式以教材原图为准），不做公式 OCR。
- **小结/复习题等页图形密集处**抽出的文字可能混入排版杂字——入库层按需清洗或剔除（如第一章"小结"页已见杂字，可后续在 md 里删该 chunk 行）。

## 入库（S5）
\`\`\`bash
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from edu_agent.ingest import ingest; print(ingest())"
\`\`\`
自动扫 structured/ + structured_auto/ 两个目录，全量重建 chroma_db（幂等）。
