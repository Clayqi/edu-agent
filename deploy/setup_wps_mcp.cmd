@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo  WPS Office MCP 依赖安装（第三方 wps-skills，装在仓库外）
echo ============================================================
echo  仓库里只放本项目的适配层；第三方源码与 node_modules 一律不入库。
echo.

set "REPO=%~dp0.."
for %%I in ("%REPO%") do set "REPO=%%~fI"

set "DEPS=%EDU_DEPS_DIR%"
if "%DEPS%"=="" set "DEPS=%LOCALAPPDATA%\edu-agent\deps"
if not "%~1"=="" set "DEPS=%~1"
set "DIR=%DEPS%\wps-skills"

echo  仓库      : %REPO%
echo  安装位置  : %DIR%
echo.

where git >nul 2>nul || (echo [错误] 未找到 git & pause & exit /b 1)
where node >nul 2>nul || (echo [错误] 未找到 node（需 Node 18+） & pause & exit /b 1)
where npm >nul 2>nul || (echo [错误] 未找到 npm & pause & exit /b 1)
where powershell >nul 2>nul || (echo [错误] 未找到 powershell（COM 桥需要） & pause & exit /b 1)

if exist "%DIR%\wps-office-mcp\package.json" (
  echo [1/5] 已存在，跳过克隆
) else (
  echo [1/5] 克隆 wps-skills 到仓库外 ...
  if not exist "%DEPS%" mkdir "%DEPS%"
  git clone --depth 1 https://github.com/lc2panda/wps-skills "%DIR%"
  if errorlevel 1 (echo [错误] 克隆失败：国内网络请先开 GitHub 加速器或设置代理 & pause & exit /b 1)
)

pushd "%DIR%\wps-office-mcp"
echo [2/5] 安装依赖 npm ci ...
call npm ci
if errorlevel 1 (echo [错误] npm ci 失败 & popd & pause & exit /b 1)

echo [3/5] 构建 npm run build ...
call npm run build
if errorlevel 1 (echo [错误] npm run build 失败 & popd & pause & exit /b 1)
popd

if not exist "%DIR%\wps-office-mcp\dist\index.js" (
  echo [错误] 构建完成但未产出 dist\index.js & pause & exit /b 1
)

echo [4/5] 打本地补丁（WPS 窗口可见性 / Word 存盘格式 / 活动文稿回落）...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0patch_wps_mcp.ps1" -Root "%DIR%"
if errorlevel 1 (echo [错误] 补丁失败：请人工核对 scripts\wps-com.ps1 & pause & exit /b 1)

echo [5/5] 写运行时配置 %REPO%\data\wps_mcp.json ...
if not exist "%REPO%\data" mkdir "%REPO%\data"
set "COMMIT="
for /f "delims=" %%C in ('git -C "%DIR%" rev-parse HEAD 2^>nul') do set "COMMIT=%%C"
powershell -NoProfile -Command "$j=[ordered]@{dir='%DIR%';entry='%DIR%\wps-office-mcp\dist\index.js';skills_dir='%DIR%\skills';commit='%COMMIT%';installed_at=(Get-Date).ToString('s')}; [IO.File]::WriteAllText('%REPO%\data\wps_mcp.json', ($j | ConvertTo-Json), (New-Object Text.UTF8Encoding($false)))"
if errorlevel 1 (
  echo [警告] 写 data\wps_mcp.json 失败：可改用环境变量 WPS_MCP_DIR 指向 %DIR%
) else (
  type "%REPO%\data\wps_mcp.json"
)

echo.
echo 完成。路径解析优先级：环境变量 WPS_MCP_DIR ^> data\wps_mcp.json ^> 默认 %LOCALAPPDATA%\edu-agent\deps\wps-skills
echo 注：Windows 走 PowerShell COM 桥（scripts\wps-com.ps1），**无需安装 WPS 加载项**（那是 macOS/Linux 轮询模式才要）。
echo 启动服务后到「MCP 服务」页可看到 WPS Office 服务的状态与工具数（正常约 250 个）。
pause
