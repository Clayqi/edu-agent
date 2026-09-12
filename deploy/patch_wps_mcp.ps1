# 给第三方 wps-skills 的 COM 桥打本地补丁（幂等；由 deploy/setup_wps_mcp.cmd 调用）
#
# 为什么不把补丁后的文件放仓库：交接约定（docs/09-WPS接入交接要求.md）要求第三方源码不入库。
# 所以补丁以「脚本 + 可核对替换」的形式留在仓库里，安装时自动施加，换台机器结果一致。
#
# 打完后 scripts/wps-com.ps1 必须仍是 **UTF-8 带 BOM**（PowerShell 5.1 无 BOM 时按 GBK 解析中文注释会语法报错）。
param(
    [Parameter(Mandatory = $true)][string]$Root,   # wps-skills 克隆目录
    [switch]$Quiet
)
$ErrorActionPreference = "Stop"

$target = Join-Path $Root "wps-office-mcp\scripts\wps-com.ps1"
if (-not (Test-Path $target)) { Write-Output "[补丁] 找不到 $target"; exit 1 }

$raw = [System.IO.File]::ReadAllText($target, [System.Text.Encoding]::UTF8)
# 统一成 CRLF 再按行匹配（上游文件可能是 LF，git 检出又可能转 CRLF，两种都要能打）
$orig = ($raw -replace "`r`n", "`n") -replace "`n", "`r`n"
$text = $orig
$report = @()

function Apply([string]$name, [string]$find, [string]$repl) {
    $script:text = $script:text
    if ($script:text.Contains($repl)) { $script:report += "  跳过（已打过） $name"; return }
    if (-not $script:text.Contains($find)) { $script:report += "  [警告] 锚点未命中 $name （上游可能改过，请人工核对）"; return }
    $script:text = $script:text.Replace($find, $repl)
    $script:report += "  已打补丁 $name"
}

# ---- P1: Writer/Excel 取实例后设 Visible（否则 WPS 隐形启动，导出后看不到窗口）----
Apply "P1a Show-WpsApp 助手函数" `
    "# ==================== COM Object Getters ====================" `
    @"
# ==================== COM Object Getters ====================

# 本地补丁（deploy/patch_wps_mcp.ps1）：Writer(文字)/Excel(表格) 原先从不设 Visible，
# 经 MCP 建文档时 WPS 是「隐形启动」的 —— 用户看不到窗口，以为导出失败。
function Show-WpsApp(`$app) {
    if (`$null -ne `$app) { try { `$app.Visible = `$true } catch {} }
    return `$app
}
"@

Apply "P1b 已运行实例 Excel" `
    "try { return [System.Runtime.InteropServices.Marshal]::GetActiveObject('Ket.Application') }" `
    "try { return (Show-WpsApp ([System.Runtime.InteropServices.Marshal]::GetActiveObject('Ket.Application'))) }"
Apply "P1c 已运行实例 Word" `
    "try { return [System.Runtime.InteropServices.Marshal]::GetActiveObject('Kwps.Application') }" `
    "try { return (Show-WpsApp ([System.Runtime.InteropServices.Marshal]::GetActiveObject('Kwps.Application'))) }"
Apply "P1d 新建实例 Excel" `
    "            `$app = New-Object -ComObject 'Ket.Application'`r`n            if (`$app) { return `$app }" `
    "            `$app = New-Object -ComObject 'Ket.Application'`r`n            if (`$app) { return (Show-WpsApp `$app) }"
Apply "P1e 新建实例 Word" `
    "            `$app = New-Object -ComObject 'Kwps.Application'`r`n            if (`$app) { return `$app }" `
    "            `$app = New-Object -ComObject 'Kwps.Application'`r`n            if (`$app) { return (Show-WpsApp `$app) }"
Apply "P1f CLSID 回落分支" `
    "                        if (`$app) { return `$app }" `
    "                        if (`$app) { return (Show-WpsApp `$app) }"

# ---- P2: Get-TargetPres 回落到最后一个文稿（无活动窗口时 ActivePresentation 为 $null）----
Apply "P2 Get-TargetPres 回落" @"
function Get-TargetPres(`$ppt, `$p) {
    if (`$null -eq `$ppt) { return `$null }
    if (`$p.presentationName) {
        try { return `$ppt.Presentations.Item([string]`$p.presentationName) } catch { return `$null }
    }
    return `$ppt.ActivePresentation
}
"@ @"
function Get-TargetPres(`$ppt, `$p) {
    if (`$null -eq `$ppt) { return `$null }
    if (`$p.presentationName) {
        try { return `$ppt.Presentations.Item([string]`$p.presentationName) } catch { return `$null }
    }
    # 本地补丁：MCP 后台建演示文稿时没有活动窗口，`$ppt.ActivePresentation 为 `$null，
    # 会让 saveAs / getSlideCount 一律报 "No active presentation"；回落到最后一个（通常是新建的）文稿。
    `$pres = `$null
    try { `$pres = `$ppt.ActivePresentation } catch {}
    if (`$null -eq `$pres) {
        try {
            if (`$ppt.Presentations.Count -ge 1) { `$pres = `$ppt.Presentations.Item(`$ppt.Presentations.Count) }
        } catch {}
    }
    return `$pres
}
"@

# ---- P3: PPT 的 save / saveAs 改用 Get-TargetPres ----
Apply "P3a save 分支" @"
        `$ppt = Get-WpsPpt
        if (`$null -ne `$ppt -and `$null -ne `$ppt.ActivePresentation) {
            `$ppt.ActivePresentation.Save()
"@ @"
        `$ppt = Get-WpsPpt
        # 本地补丁：改用 Get-TargetPres（无活动窗口时 ActivePresentation 为 `$null）
        `$pres = Get-TargetPres `$ppt `$p
        if (`$null -ne `$ppt -and `$null -ne `$pres) {
            `$pres.Save()
"@
Apply "P3b saveAs 分支" @"
            `$ppt = Get-WpsPpt
            if (`$null -eq `$ppt -or `$null -eq `$ppt.ActivePresentation) { Output-Json @{ success = `$false; error = "No active presentation" }; exit }
            `$format = Get-PptSaveFormat `$p.format
            if (`$null -ne `$format) { `$ppt.ActivePresentation.SaveAs(`$path, `$format) }
            else { `$ppt.ActivePresentation.SaveAs(`$path) }
"@ @"
            `$ppt = Get-WpsPpt
            # 本地补丁：改用 Get-TargetPres（无活动窗口时 ActivePresentation 为 `$null，另存为恒失败）
            `$pres = Get-TargetPres `$ppt `$p
            if (`$null -eq `$ppt -or `$null -eq `$pres) { Output-Json @{ success = `$false; error = "No active presentation" }; exit }
            `$format = Get-PptSaveFormat `$p.format
            if (`$null -ne `$format) { `$pres.SaveAs(`$path, `$format) }
            else { `$pres.SaveAs(`$path) }
"@

# ---- P4: Word 存盘格式码 16 -> 12（WPS 把 16 落成二进制 .doc，却顶着 .docx 扩展名）----
Apply "P4a 格式映射表" `
    "    `$map = @{ doc = 0; docx = 16; pdf = 17; rtf = 6; xps = 18; html = 8; htm = 8; txt = 2; xml = 11 }" `
    "    # 本地补丁：WPS 把 16(wdFormatDocumentDefault) 落成二进制 .doc（头 D0CF11E0，与 .docx 扩展名不符），`r`n    # 12(wdFormatXMLDocument) 才是真 OOXML；docx16 保留旧行为别名。`r`n    `$map = @{ doc = 0; docx = 12; docx16 = 16; pdf = 17; rtf = 6; xps = 18; html = 8; htm = 8; txt = 2; xml = 11 }"
Apply "P4b 映射表注释" `
    "    # Word WdSaveFormat: doc=0, docx=16, pdf=17, rtf=6, xps=18, html=8, txt=2, xml=11" `
    "    # Word WdSaveFormat: doc=0, docx=12/16, pdf=17, rtf=6, xps=18, html=8, txt=2, xml=11"

if ($text -ne $orig) {
    # 必须写回 UTF-8 **带 BOM**
    [System.IO.File]::WriteAllText($target, $text, (New-Object System.Text.UTF8Encoding($true)))
}
$bytes = [System.IO.File]::ReadAllBytes($target)[0..2]
$bom = (($bytes | ForEach-Object { $_.ToString('X2') }) -join ' ')

if (-not $Quiet) { $report | ForEach-Object { Write-Output $_ } }
Write-Output ("[补丁] 目标: " + $target)
Write-Output ("[补丁] 文件头: " + $bom + "  (EF BB BF = UTF-8 BOM，必须)")
Write-Output ("[补丁] 结果: " + $(if ($text -ne $orig) { "已更新" } else { "无变化（已是最新）" }))

# 语法自检
$err = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($target, [ref]$null, [ref]$err)
if ($err -and $err.Count -gt 0) {
    Write-Output ("[补丁] [错误] 语法检查未通过: " + $err[0].Message)
    exit 2
}
Write-Output "[补丁] 语法检查: OK"
exit 0
