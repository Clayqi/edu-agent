#!/usr/bin/env bash
# 全量单测（canonical 入口）
#
# 为什么有这条：仓库以前没有任何「Hermes / CI / 人都认」的测试入口，导致每轮改动后
# 工具链都报 "No canonical test/lint/build command was detected → unverified"，
# 追踪器还会把「为验证而写的脚本」本身记成待验证改动（自指循环）。
# 这条脚本是 Hermes 认得的标准位置之一（scripts/run_tests.sh），加完就不再空转。
#
# 用法：scripts/run_tests.sh            # 跑全部
#       scripts/run_tests.sh -v         # 详细
#       scripts/run_tests.sh -k memory  # 只跑名字含 memory 的用例
#
# 约定：仓库禁盘符绝对路径 → 一律相对路径；unittest 的结果写 stderr，
# 这里把 stderr 合并到 stdout，调用方只读 stdout 也能拿到完整结论。
set -uo pipefail

cd "$(dirname "$0")/.." || exit 2

PY=".venv/Scripts/python.exe"          # Windows（git-bash / PowerShell）
[ -x "$PY" ] || PY=".venv/bin/python"   # Linux / macOS
if [ ! -x "$PY" ]; then
  echo "[run_tests] 找不到虚拟环境里的 python。先建环境：" >&2
  echo "  uv venv .venv && uv pip install -r requirements.txt --python .venv/Scripts/python.exe" >&2
  echo "（本仓库的 .venv 是 uv 建的，没有 pip，必须用 uv pip install）" >&2
  exit 127
fi

"$PY" -m unittest discover -s tests -p "test_*.py" "$@" 2>&1
code=$?
echo "[run_tests] exit=$code（suite 全绿即 0）"
exit $code
