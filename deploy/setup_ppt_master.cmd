@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
rem ============================================================
rem  ppt-master 安装脚本（「边框里的 PPT 优化」一期依赖）
rem  为什么装在仓库外：第三方代码不进仓库（与 wps-skills 同策略）
rem  为什么用 gh-proxy：本机 hosts 把 github.com 指到 127.0.0.1（加速器），直连不可用
rem  用法：deploy\setup_ppt_master.cmd        （双击或命令行都行）
rem ============================================================

set "DEST=%LOCALAPPDATA%\edu-agent\deps\ppt-master"
set "VENV_PY=%~dp0..\.venv\Scripts\python.exe"
set "REPO=https://gh-proxy.com/https://github.com/hugohe3/ppt-master.git"

echo [1/5] 目标目录：%DEST%
if exist "%DEST%\.git" (
  echo       已存在，跳过克隆（升级请跑：python "%DEST%\skills\ppt-master\scripts\update_repo.py"）
) else (
  if not exist "%LOCALAPPDATA%\edu-agent\deps" mkdir "%LOCALAPPDATA%\edu-agent\deps"
  echo       克隆中（gh-proxy，depth=1）...
  git clone --depth 1 --single-branch "%REPO%" "%DEST%"
  if errorlevel 1 (
    echo       [X] 克隆失败：检查网络 / 加速器；也可手动下载 Releases 里的 ppt-master-skill-*.zip
    goto :end
  )
)

echo [2/5] 检查 Python 环境
if not exist "%VENV_PY%" (
  echo       [X] 找不到虚拟环境：%VENV_PY%
  echo           先按 docs/04 建好 .venv，再重跑本脚本
  goto :end
)

echo [3/5] 装一期需要的依赖（避开 AGPL 的 PyMuPDF 与旁白/图片生成）
"%VENV_PY%" -m pip install --disable-pip-version-check -q ^
  PyYAML XlsxWriter Pillow numpy -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 echo       [!] 依赖安装有失败项，自检会报出来（见第 5 步）

echo [4/5] 写安装记录
> "%LOCALAPPDATA%\edu-agent\ppt_master.json" echo {"home": "%DEST:\=\\%"}
"%VENV_PY%" -c "import json,os,subprocess;p=os.path.join(os.environ['LOCALAPPDATA'],'edu-agent','ppt_master.json');d=json.load(open(p,encoding='utf-8'));d['commit']=subprocess.run(['git','-C',d['home'],'rev-parse','--short','HEAD'],capture_output=True,text=True).stdout.strip();json.dump(d,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=1);print('      commit',d['commit'])"

echo [5/5] 自检
pushd "%~dp0.."
set PYTHONPATH=src
"%VENV_PY%" -c "import json;from edu_agent import ppt_polish as p;s=p.status();print(json.dumps({k:s[k] for k in ('ok','installed','commit','intake_ready','missing_required_scripts','missing_python_deps')},ensure_ascii=False,indent=1))"
popd

echo.
echo 完成。可选依赖说明（缺了只影响二期）：
echo   skia-pathops / uharfbuzz —— 合并形状与文字轮廓（Python 3.13 无轮子，一期不需要）
echo   PyMuPDF —— PDF 转 Markdown，AGPL，一期明确不装
:end
endlocal
pause
