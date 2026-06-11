---
name: heavy-review
description: Deep deployment-plan review skill for safety-checking deployment plans before execution. Use this skill whenever the user says "审查", "审查方案", "检查方案", "安全审查", "开始审查", "review plan", or asks to review/audit a deployment plan before deploying. This skill reads the latest deployment-plan.md, runs parallel subagents across web and local source dimensions to check the plan, then synthesizes findings and lets the user approve fixes that get edited directly into the same plan file.
---

# heavy-review

部署方案安全审查 skill。从定位 plan 到把修复 inline 改回 plan，全程结构化执行。

## 触发后立即做

1. 进入阶段 R0（定位审查目标）
2. SKILL_DIR 固定为：`~/.agents/skills/heavy-review`

---

## 阶段 R0：定位审查目标

运行 `scripts/find-latest-plan.ps1`，自动找到 `.workflows/` 下**最新时间戳目录**中的 `deployment-plan.md`：

- 输出 `SESSION_DIR`（如 `.workflows/2026-05-16-1430/`）
- 输出 `PLAN_PATH`（即 `<SESSION_DIR>/deployment-plan.md`）
- 若找不到任何 plan 文件，告知用户并终止

定位到后告知用户："已定位到最新 deployment-plan：<PLAN_PATH>，开始审查。"

---

## 阶段 R1：读取 plan

完整读取 `<PLAN_PATH>` 的内容，理解：
- 部署目标
- 调研摘要（含 CONFLICT 标注）
- 前置检查 / 执行步骤 / 回滚方案 / 风险清单

读完直接进入 R2，不再问用户。

---

## 阶段 R2：派 2 个并行 subagent

### R2.1：生成审查清单

main agent 基于 plan 内容生成**审查清单**：
- 按审查框架（见 `references/review-framework.md`）展开为审查项 #1, #2, ...
- 每个审查项标注哪个维度更适合审查（联网 / 源码 / 都需要）

### R2.2：创建 check 目录

运行 `scripts/ensure-review-dir.ps1`，在 `<SESSION_DIR>/review/` 下准备好目录。

### R2.3：派出 subagent

将审查清单分发给 2 个 subagent，同时启动（`run_in_background: true`）。

**联网 subagent prompt**（五段式，复用 heavy-research 信息传导）：

```
【1. 审查背景】
plan 路径：<PLAN_PATH>
plan 内容（完整复制 deployment-plan.md 全文）：
<...>
用户当前关注点：<阶段 R3 不合理回流时由用户补充；首轮为空>

【2. 审查清单】
<树形审查项清单，含编号和维度建议>

【3. 维度任务边界】
本 subagent 维度：联网
工具范围：WebSearch、WebFetch
不要做：读本地源码

【4. 执行指令】
先依次读取以下文件，读完再开始执行：
1. ~/.agents/skills/heavy-review/references/review-loop-core.md
2. ~/.agents/skills/heavy-review/references/subagent-web.md
按文件中的审查流程对每个审查项执行联网验证。

【5. 输出契约】
完成后：
1. 把完整审查报告写入：<SESSION_DIR>/review/web.md
   文件格式见下方"结果文件格式"
2. 你的整个对话回复只能是一行："Done: web"
   不许在对话里返回摘要、解释或任何其他文字。
```

**源码 subagent prompt**（同上，但维度改为"源码"，工具改为 Grep/Read/Glob，读文件改为 `subagent-source.md`，写入 `<SESSION_DIR>/review/source.md`，回复 `Done: source`）。

---

**结果文件格式**（每个 subagent 写入自己的 md 文件）：

```markdown
# <维度> 审查报告 — YYYY-MM-DD-HHmm

## 审查项 #1：<审查清单中的原文>
### 发现
- <问题描述>
  - 严重度：HIGH / MED / LOW
  - 证据：<URL / 文件路径 / 行号>
  - 建议修复：<具体修改建议>

### 通过项
- <通过的检查点描述>

## 审查项 #2：...

## 元数据
- tool call 总次数：N
- 审查项覆盖率：X/Y
```

### R2.4：等待全部 Done

收到 "Done: web" 和 "Done: source" 后，读取 `<SESSION_DIR>/review/` 下的两份 md 文件。

---

## 阶段 R3：综合审查报告 + 用户讨论

按 `references/synthesis-prompt.md` 模板综合 2 份报告：
- 按审查项编号对齐
- 每条发现标注来源维度
- 严重度排序：HIGH → MED → LOW

在 terminal 输出综合审查报告 + 修复建议清单后，询问用户：

> 以上是审查结果与修复方案。请问：
> 1. **修复方案合理** → 我将把修复 inline 改进 deployment-plan.md
> 2. **修复方案不合理** → 请告诉我哪里有问题或想着重审查哪个方向，我们重新派 subagent 审查（覆盖 check/ 下的文件）

**用户选 1** → 进入阶段 R4

**用户选 2** → 与用户讨论新的审查重点，把用户关注点写进新一轮 prompt 的"用户当前关注点"段，回到 R2 重新派 subagent

---

## 阶段 R4：把修复 inline 改进 plan

按 `references/fix-edit-pattern.md` 的方式，用 Edit 工具直接修改 `<PLAN_PATH>`：
- 不新建文件，直接改原 deployment-plan.md
- 在对应执行步骤 / 回滚方案 / 风险清单处插入修复
- 修改后告知用户："修复已 inline 进 <PLAN_PATH>，可以基于此版本部署。"

任务结束。后续部署由 agent 按 plan 自由执行，不在本 skill 内。

---

## 约束

- 全程在 context compaction 触发之前完成
- 阶段 R2 期间不中途暂停问用户
- 修复未经用户确认前不得 Edit deployment-plan.md
