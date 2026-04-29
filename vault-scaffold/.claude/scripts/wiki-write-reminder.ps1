$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()

$inputText = [Console]::In.ReadToEnd()

try {
    $hook = $inputText | ConvertFrom-Json -ErrorAction Stop
} catch {
    exit 0
}

function Get-HookFilePath {
    param($Hook)

    if ($null -eq $Hook.tool_input) {
        return ""
    }

    $toolInput = $Hook.tool_input
    if ($toolInput.PSObject.Properties.Name -contains "file_path") {
        return [string]$toolInput.file_path
    }
    if ($toolInput.PSObject.Properties.Name -contains "path") {
        return [string]$toolInput.path
    }
    return ""
}

function Test-WikiMarkdownPath {
    param([string]$PathText)

    if ([string]::IsNullOrWhiteSpace($PathText)) {
        return $false
    }

    $normalized = $PathText -replace "\\", "/"
    return $normalized -match '(^|/)wiki/.+\.md$'
}

$filePath = Get-HookFilePath -Hook $hook
if (-not (Test-WikiMarkdownPath -PathText $filePath)) {
    exit 0
}

$message = @"
[wiki-write-reminder] 正在写入 wiki/ 路径 .md 文件
===============================================================
必须遵守 Obsidian Flavored Markdown 语法（详见 vault CLAUDE.md 的
「Skill Stack」章节）：

写之前激活：
  1. obsidian-markdown skill
  2. 若本次写入来自 ingest / lint fix pass，同时遵守对应 second-brain skill
  3. 若本次写入来自 ingest，必须已完成 domain-routing preflight 并得到用户确认

核心必须：
  ✓ [[wikilinks]]，不是 [text](x.md)
  ✓ 非 raw 附件 embed 用 ![[file.ext]]，不是 ![alt](x.png)
  ✓ raw 非图片/证据素材用 [[raw/file.ext]]；教学图片可在语义位置用 ![[raw/image.png|600]]
  ✓ 图片居中由全局 CSS snippet 处理，不在正文写 HTML / <style> / inline CSS
  ✓ ==highlights==，不是 <mark>
  ✓ %%comments%%，不是 <!-- -->
  ✓ 多行 YAML 数组（tags:\n  - x），不是 [x, y]
  ✓ 首行 frontmatter ---，闭合 --- 后空一行
  ✓ Callout 格式：> [!type]，连续行都带 >
  ✓ checklist 空格：- [ ] / - [x]

核心禁止：
  ✗ 编造不存在的 wikilink 目标或 ^block-id
  ✗ 非 Obsidian 官方 callout/别名，或 vault 自定义 contradiction 之外的类型
  ✗ orphan footnote（引用无定义）
===============================================================
"@

$payload = @{
    hookSpecificOutput = @{
        hookEventName = "PreToolUse"
        additionalContext = $message
    }
} | ConvertTo-Json -Compress

Write-Output $payload

exit 0
