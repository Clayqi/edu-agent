# 变更记录（CHANGELOG）

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)；版本号跟界面显示对齐。

## [v1.6.0] - 2026-09-10

### 新增
- **教案中心改为「教案 × PPT 可视化编排台」**（不再是聊天窗口）：左侧编排这节课的教学环节（名称 / 分钟 / 要点，支持上移下移、增删），右侧即时生成对应的 PPT 页面（每页 = 一个环节，缩略图显示标题与要点）；改左边右边立刻变，点右侧卡片跳回左侧对应环节。
  顶部：课题、学情/课时、生成骨架、添加环节、保存、导出 HTML、预览 PPT。
  数据存浏览器本地（`localStorage: edu_design_v1`），自动保存；「导出 HTML」产出含完整教案 + PPT 大纲的独立文件；「预览 PPT」按 16:9 全屏逐页展示。
- 侧栏「教育能力」分组可伸缩：点分组标题或右侧箭头收起/展开（带 0.18s 过渡），状态记 `localStorage: edu_cap_open`，刷新后保持。

### 变更
- 「教案中心」入口按角色分开：**教师** → 教案 × PPT 编排台；**学生** → AI 答疑（对话）。同一按钮双角色，不再共用对话视图。

## [v1.5.0] - 2026-09-10

### 新增
- **看原页**：`GET /api/page_image?page=N[&source=&dpi=]`，把教材原页渲染成 PNG（印刷页 `+6` = 物理页，150dpi，缓存 `data/page_cache/`）。
  前端引用卡与正文绿色引用 pill 都可点开「原页浏览器」：上一页/下一页、跳任意页、本节首/本章首、回到引用页、键盘 `←/→` 翻页、`Esc` 关闭。
- **目录页码范围**：`scripts/build_toc_ranges.py` → `content/toc_ranges.json`；`GET /api/textbook/toc` 返回每章每节页码范围（实测：第三章 p59–p102、3.3 幂函数 p89–p92、全书 p1–p260）。
- **图片/公式防幻觉机制**：`src/edu_agent/figdetect.py` 给片段判 `has_figure` / `fig_nums` / `fidelity`；`scripts/backfill_chunk_meta.py` 回填向量库 151 个片段（有图号 64、低保真 33）；`prompts.FIGURE_GUARD` + `generate._snippet_block()` 对含图片段加 ⚠ 硬约束——片段文字里没出现的公式一律当"书上只有图"，禁止写出/推导/用常识补全，只给页码+图号并提示看原页。
- 左侧栏可收起/展开（对齐 DeepSeek Harness，状态记 localStorage）。

### 变更
- 左上角面包屑显示**当前对话名称**（首问后自动命名），不再是写死的"新对话"。
- 会话消息支持附带数据（`host/store.SessionStore.append(..., meta=)`）：**引用随消息持久化**，刷新/重开会话后绿色引用 pill 与「复制/重新生成」仍在（此前刷新即丢）。

### 修复
- 右侧面板 2×2 圆钮的文字标签被下一行圆遮挡（行距不足）。
- `--ink-800` 变量在 `:root` 未定义 → 激活态圆钮标签变成白底白字看不见；已补 `#27272a`。

### 仓库
- `static/*.bak-*` 移出版本控制并写入 `.gitignore`；`content/toc_ranges.json` 随仓库走（`data/` 不入库）。

## [v1.4.0] - 2026-09-10
- 首次交付：Agent A（课本教练答疑）/ B（教案）/ S（总指挥派单）× LangChain 1.x + Chroma 151 块 + bge-m3 + DeepSeek v4-flash；UI 收口到 `web_server.py` @ 5174；`tests/` 112 例全绿。

[v1.5.0]: https://github.com/Clayqi/edu-agent/compare/v1.4.0...v1.5.0
