# 源码 Review Subagent 专项强化

加载此文件前，先加载 `review-loop-core.md`。本文件是源码取证路线的 3 个专项强化，叠加在 6+3 基础上。

## 工具

Grep + Read + Glob + 只读 Shell（Test-Path / Get-Item / PowerShell Parser ParseFile / ParseInput / bash -n / 支持 -WhatIf 的命令演练）+ Write（仅限输出契约指定的 review 报告文件）

---

## 源码路线证据级别

- `confirmed`：直接本地证据已验证，例如文件内容、路径状态、调用引用、语法解析结果或 `-WhatIf` 输出。
- `unverified`：只有间接推断，或尚未完成该 item 必需的读取、解析、Glob / Test-Path、dry-run / `-WhatIf`。
- `CONFLICT`：本地证据与 plan 声明冲突，例如 create 目标已存在、move 目标已存在、备份输出与回滚输入不一致。
- `MISSING`：plan 声明必须存在的本地路径、备份产物或引用对象不存在。
- `STALE`：源码路线通常不用；只有当本地文件内引用过期版本 / 旧日期声明且会影响 plan 时才使用。

---

## 专项强化 4：plan 路径优先（入口点倒置）

不从项目入口（package.json / main.*）出发，而是直接以 **plan 中每条修改对象**为入口点：

**执行流程**：
1. 从 plan 全文提取所有出现的文件路径（绝对/相对）、命令、文件 glob 模式
2. 先为每个路径判定 plan 操作类型：create / modify / delete / move / backup / restore / unknown
3. 按操作类型验证路径状态：
   - create：目标不存在通常是预期；若已存在 = FAIL（证据级别：CONFLICT；风险依据：命名/路径冲突）
   - modify / delete / backup：目标必须存在；不存在 = FAIL（证据级别：MISSING；风险依据：目标缺失）
   - move：源必须存在；目标已存在 = FAIL（证据级别：CONFLICT；风险依据：命名/路径冲突）
   - restore：restore 输入必须是唯一且可追溯的备份产物路径；若 plan 未明确指定或无法从 backup 步骤产物唯一推出 → UNVERIFIABLE；若已明确指定但与 backup 输出不匹配 → FAIL（风险依据：回滚不可执行）
   - unknown：无法确定语义时列为 UNVERIFIABLE，不得直接 FAIL
4. Read 每个需要存在的目标文件了解当前内容（与 plan 描述的"目标状态"对比）
5. Grep 找该文件被其他文件引用的情况，评估改动的辐射面

**5 类检查**：
1. **路径存在性**：按操作类型判断当前存在 / 不存在是否合理，不得把 create 目标不存在直接判 FAIL
2. **调用链破坏**：plan 修改的函数/导出物是否被其他文件引用（引用未处理 = FAIL；风险依据：调用链破坏）
3. **回滚可行性**：plan 删除/重命名的资源是否有 git 历史或备份可恢复。若可确认无任何可用恢复来源 = FAIL（风险依据：无法回滚）；若只是 plan 没有给出可追溯恢复路径且无法确认外部恢复来源 = UNVERIFIABLE
4. **命名/路径冲突**：plan 新建的资源路径是否已存在（已存在 = FAIL；证据级别：CONFLICT）
5. **平台兼容性**：plan 中的 shell 命令是否符合 Windows + PowerShell（不兼容 = FAIL；风险依据：平台不兼容）

---

## 专项强化 5：依赖图差分追踪（双向 + plan 操作前提）

找到目标符号（函数 / 类 / 文件）后，带着"plan 操作 = 改/删/移动 X"的前提双向追踪：

**向上追踪（callers）**：
- Grep 搜索该符号名在其他文件中的引用
- 评估"plan 改了 X 的签名/路径，谁会被破坏"

**向下追踪（callees）**：
- 读取该符号的实现，找出它调用的其他符号
- 评估"plan 删了 X 依赖的 Y，X 还能跑吗"

追踪深度：最多 2 层。发现 HIGH 候选风险点时可选择性深入 1 层。

---

## 专项强化 6：3 类审查专属检查模式

**检查 A：静态语法预检**
plan 内出现的代码块 / PowerShell 命令必须通过语法检查。

若 plan 指向真实脚本文件，用 `ParseFile`：
```powershell
$null = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$null, [ref]$errors)
if ($errors.Count -gt 0) { # 标记 FAIL，并记录语法错误作为风险依据 }
```

若 plan 只有 inline PowerShell 片段，用 `ParseInput`，不要假设存在 `$scriptPath`：
```powershell
$tokens = $null
$errors = $null
$null = [System.Management.Automation.Language.Parser]::ParseInput($inlineScript, [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { # 标记 FAIL，并记录语法错误作为风险依据 }
```
Bash 命令预检：真实脚本文件用 `bash -n <script>`；inline Bash 片段用 `bash -n -c '<inlineScript>'`。语法错误直接标记 FAIL，并把解析错误写入证据。

**检查 B：dry-run / -WhatIf 验证**
plan 中调用支持 `-WhatIf` 的 cmdlet 时，必须先用 `-WhatIf` 演练并把输出贴回 finding：
```powershell
<cmdlet> -WhatIf
```
演练结果与 plan 预期不符 = FAIL（风险依据：dry-run 与预期不符）。

**检查 C：备份-回滚命令对账**
plan 中"backup → restore"对儿，比对产物文件名是否一致：
- backup 输出的实际文件名（含时间戳？覆盖？）
- restore 命令所需的输入文件名
- 不对应 = FAIL（风险依据：备份-回滚对账失败）

---

## 覆盖率跟踪（3 段式）

在 scratchpad 中维护 3 段式覆盖率清单：

```
已读文件：
- <文件路径>（Read 过）

已验证 plan 路径：
- <路径>：存在 / 不存在 / 未验证

已检测调用链：
- <符号名>：callers 已 Grep / 未 Grep
```

**覆盖率阈值**：
- plan 中提到的所有路径必须 100% 做过 Glob / Test-Path 等存在性验证；只有按操作类型“需要存在”的路径才必须 Read，create 目标不存在时不得强行要求 Read
- HIGH 候选风险点必须 Grep 过 callers
- 未达必须显式列为 UNVERIFIABLE，不得隐式 PASS

---

## 跨章节一致性检查（把 plan 自身当源码）

把 deployment-plan.md 自身当源码 Read + Grep 自检：
- 执行步骤的"影响范围"提到的文件 vs 风险清单覆盖的文件 → 找漂移
- 调研摘要中的 CONFLICT 标注 vs 执行步骤中的处理说明 → 找遗漏
- 不可逆步骤（⚠️ 标注）vs 回滚方案中的对应条目 → 找缺失

---

## 注意事项

- 审查时除输出契约指定的 review 报告文件外只读不写（不修改任何仓库文件，修复由父 agent 在 R4 阶段执行）
- 优先读文件的关键部分（函数签名、类定义、导出接口），大文件（>300 行）先读头部和导出部分
- Windows 路径注意大小写 + 正反斜杠（Glob/Read 工具已处理，但 plan 中的路径字面量需核对）
- 受保护路径（CLAUDE.md / AGENTS.md / GEMINI.md / task_plan.md / progress.md / findings.md / .workflows/ / .claude/ / .codex/ / .gemini/ / .agents/ / .brv/ / .brv 等）出现在 plan 的 push 步骤中 = FAIL（风险依据：受保护路径不得推送）
