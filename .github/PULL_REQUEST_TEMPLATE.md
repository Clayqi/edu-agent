## 改了什么

<!-- 一句话说清：哪个模块、改了什么、为什么 -->

## 怎么验证的

<!-- 例：tests/ 112 例全绿；或 手动步骤（点哪里、看到什么）；或 附日志/screenshot 路径 -->

- [ ] `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"` → Ran 112 tests, OK
- [ ] 改了 `prompts.py` / `generate.py` / `web_server.py` / `host/store.py` → 已重启 5174 并自测
- [ ] 只改 `static/` → 刷新浏览器自测过

## 影响面

- 动了哪些模块：
- 有没有改别人的模块（有的话，跟谁打过招呼）：
- 有没有动 `chroma_db/` / `content/`（教材库变更需单人负责）：
- 是否影响接口契约（`/api/*` 返回结构）/ 前端依赖：

## 截图或证据

<!-- 界面改动贴图；纯后端改动贴关键日志行 -->
