# 源码 Review Subagent 专项强化

加载此文件前，先加载 `review-loop-core.md`。本文件是源码维度的 3 个专项强化，叠加在 6+3 基础上。

## 工具

Grep + Read + Glob

---

## 专项强化 4：plan 路径优先（入口点倒置）

不从项目入口（package.json / main.*）出发，而是直接以 **plan 中每条修改对象**为入口点：

**执行流程**：
1. 从 plan 全文提取所有出现的文件路径（绝对/相对）、命令、文件 glob 模式
2. Glob 验证每个路径在仓库中是否存在（不存在 = HIGH FAIL）
3. Read 每个目标文件了解当前内容（与 plan 描述的"目标状态"对比）
4. Grep 找该文件被其他文件引用的情况，评估改动的辐射面

**5 类检查**：
1. **路径存在性**：plan 引用的文件/目录是否真实存在（不存在 = HIGH MISSING）
2. **调用链破坏**：plan 修改的函数/导出物是否被其他文件引用（引用未处理 = HIGH FAIL）
3. **回滚可行性**：plan 删除/重命名的资源是否有 git 历史或备份可恢复（无 = HIGH FAIL）
4. **命名/路径冲突**：plan 新建的资源路径是否已存在（已存在 = MED CONFLICT）
5. **平台兼容性**：plan 中的 shell 命令是否符合 Windows + PowerShell（不兼容 = HIGH FAIL）

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
plan 内出现的代码块 / PowerShell 命令必须通过语法检查：
```powershell
$null = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$null, [ref]$errors)
if ($errors.Count -gt 0) { # 标记 HIGH FAIL }
```
Bash 命令用 `bash -n <script>` 预检。语法错误直接 HIGH FAIL。

**检查 B：dry-run / -WhatIf 验证**
plan 中调用支持 `-WhatIf` 的 cmdlet 时，必须先用 `-WhatIf` 演练并把输出贴回 finding：
```powershell
<cmdlet> -WhatIf
```
演练结果与 plan 预期不符 = MED FAIL。

**检查 C：备份-回滚命令对账**
plan 中"backup → restore"对儿，比对产物文件名是否一致：
- backup 输出的实际文件名（含时间戳？覆盖？）
- restore 命令所需的输入文件名
- 不对应 = HIGH FAIL

---

## 覆盖率跟踪（3 段式）

在 scratchpad 中维护 3 段式覆盖率清单：

```
已读文件：
- <文件路径>（Read 过）

已验证 plan 路径：
- <路径>：存在 ✅ / 不存在 ❌ / 未验证 ⏳

已检测调用链：
- <符号名>：callers 已 Grep ✅ / 未 Grep ⏳
```

**覆盖率阈值**：
- plan 中提到的所有路径必须 100% Glob/Read 过
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

- 审查时只读不写（不修改任何仓库文件，修复由父 agent 在 R4 阶段执行）
- 优先读文件的关键部分（函数签名、类定义、导出接口），大文件（>300 行）先读头部和导出部分
- Windows 路径注意大小写 + 正反斜杠（Glob/Read 工具已处理，但 plan 中的路径字面量需核对）
- 受保护路径（CLAUDE.md / AGENTS.md / .claude/ / .agents/ / .brv/ 等）出现在 plan 的 push 步骤中 = HIGH FAIL
