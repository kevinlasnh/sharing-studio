# Review Loop Core — 6步骨架 + 3通用强化

所有 review subagent 都加载此文件。本文件定义审查的底层流程，独立于具体维度。

加载此文件后，再加载对应维度的专项文件（subagent-web.md 或 subagent-source.md）。

---

## 6步骨架

每个 subagent 针对自己的维度，围绕 main agent 分发的**审查清单**（checklist item 列表）执行：

```
1. 分解   → 把清单中属于本维度的 item 用 Depth×Breadth 树形展开（见下方强化 2）
2. 检索   → 对每个叶节点 item 执行验证（见各维度专项文件）
3. 提取   → 从结果中提取证据，写入 scratchpad（标注 item 编号 + 来源 + 证据级别）
4. 差距   → 对比 checklist，标记哪些 item 已 PASS/FAIL/UNVERIFIABLE，哪些仍有缺口
5. 循环   → 有缺口则生成 follow-up 继续（见强化 3），直到触发终止条件
6. 输出   → 把完整审查报告写入文件（格式见下方），对话回复只能是 Done: <dimension>
```

---

## 强化 1：Reasoning Trace（每次验证前必做）

每次发出验证动作前，先在 scratchpad 写一段 reasoning trace，包含：
1. 当前 item 的**真实风险面**（plan 字面写的 vs 真实可能踩的坑）
2. 前几轮已确认的发现（缩小验证空间）
3. 基于已知知识的**假设性失败模式**（如"步骤 X 可能没有备份步骤"）

验证时把 trace + query 一起作为检索上下文。

---

## 强化 2：Depth × Breadth 树形分解

把 checklist item 做成树形，而不是平铺列表：

- **Breadth**：清单本身已定宽度，不额外展开；仅在某 item 被怀疑后向 depth 方向递归 1 层
- **Depth**：最多递归 2 层（叶节点才真正执行验证）
- 每深入一层，breadth 自动减 2（浅层广泛，深层聚焦）
- 去重：若新子 item 与已验证 item 语义等价，跳过

---

## 强化 3：差距驱动 Follow-up

每轮验证后评估结果：
- 信息充足 → 标记该 item 为 PASS / FAIL / UNVERIFIABLE
- 信息不足 → 生成针对缺口的 follow-up query，继续验证
- **额外规则**：哪怕信息已足够，发现了 HIGH 严重度问题，必须再追一层证据锁定证据链

---

## 终止条件（双判据，任一触发即停）

1. **质量判据**：checklist 所有 item 均已标记 PASS / FAIL / UNVERIFIABLE，且每条 FAIL 都有 severity + 证据 + 修复建议
2. **预算判据**：tool call 次数达到上限（联网 subagent 上限 30 次，源码 subagent 上限 20 次）

---

## 输出格式

调研完成后，将完整审查报告**写入文件**（路径由父 agent 在 prompt 中指定，通常是 `<SESSION_DIR>/review/<dimension>.md`）。

文件结构：

```markdown
# <维度> 审查报告 — YYYY-MM-DD-HHmm

## 审查项 #1：<checklist item 原文>
### 发现
- <问题描述>
  - 严重度：HIGH / MED / LOW
  - 证据：<URL / 文件路径 / 行号>（证据级别：confirmed / unverified / CONFLICT / STALE / MISSING）
  - 建议修复：<具体修改建议，落点到 plan 的哪个章节哪行>

### 通过项
- <通过的检查点描述>

### 无法验证项
- <item 描述>：原因（工具不可用 / 超出维度范围 / 信息不足）

## 审查项 #2：...

## 元数据
- tool call 总次数：N
- 审查项覆盖率：X/Y（必须 100%，未达必须显式列 UNVERIFIABLE）
- 调研轨迹摘要：<3-5 行 reasoning trace 摘要>
```

**关键约束**：
- 写完文件后，整个对话回复**只能是一行** `Done: <dimension>`
- 不许在对话里返回摘要、解释或任何其他文字
- 覆盖率必须 100%，未验证的 item 必须显式列为 UNVERIFIABLE，不得隐式 PASS
