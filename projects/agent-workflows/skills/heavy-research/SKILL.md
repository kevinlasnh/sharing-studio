---
name: heavy-research
description: Deep research skill for planning deployments, investigating technical topics, or preparing structured deployment plans. Use this skill whenever the user says "调研", "研究", "调查", "准备方案", "开始调研", "我想了解", "帮我查一下", or asks to investigate a technical topic before taking action. Also triggers on "heavy-research", "deep research", or any request to research something before writing a plan. This skill runs parallel subagents across web, local source code, and memory dimensions, then synthesizes findings into a deployment plan.
---

# heavy-research

深度调研 skill。从需求澄清到输出 deployment-plan，全程结构化执行。

## 触发后立即做

1. 进入阶段 A（需求澄清）
2. SKILL_DIR 固定为：`~/.agents/skills/heavy-research`

---

## 阶段 A：需求澄清

与用户多轮讨论，明确以下内容后才能进入阶段 B：

- **调研主题**：要解决什么问题 / 要部署什么
- **本地仓库范围**：是否有相关源码需要分析（有 → 源码 subagent 激活；无 → 跳过）
- **调研边界**：哪些方向不需要查
- **输出期望**：deployment-plan 的侧重点
- **关键约束**：环境、版本、已有限制等

澄清完毕后，等用户说"开始调研"再进入阶段 B。

---

## 阶段 B：执行调研

### B0：创建本次调研目录

运行 `scripts/new-session-dir.ps1`，获取本次会话目录路径（格式：`.workflows/YYYY-MM-DD-HHmm/`）。

后续所有文件都放在此目录下：
```
.workflows/YYYY-MM-DD-HHmm/
├── research/
│   ├── web.md
│   ├── source.md
│   └── memory.md
└── deployment-plan.md
```

### B1：生成调研提纲

在派出 subagent 之前，main agent 先生成统一的**调研提纲**：

- 把调研主题分解为 5-15 个子问题
- 每个子问题标注编号（#1, #2, ...）
- 用树形结构展示（父子问题缩进，标注叶节点）

### B2：派出并行 subagent

将调研提纲分发给 subagent，同时启动（`run_in_background: true`）。

每个 subagent 的 prompt 使用以下五段式模板：

---

**联网 subagent prompt：**

```
【1. 调研背景】
主题：<X>
用户场景：<阶段 A 讨论的原始问题，尽量保留用户原话>
边界：<不查的方向>
侧重：<deployment-plan 的关注重点>
关键约束：<环境、版本、已有限制>

【2. 调研提纲】
<树形子问题清单，含编号和层级>

【3. 维度任务边界】
本 subagent 维度：联网
工具范围：WebSearch、WebFetch
不要做：读本地文件、查 ByteRover

【4. 执行指令】
先依次读取以下文件，读完再开始执行：
1. ~/.agents/skills/heavy-research/references/research-loop-core.md
2. ~/.agents/skills/heavy-research/references/subagent-web.md
按文件中的 6+3+3 流程执行调研。

【5. 输出契约】
完成后：
1. 把完整调研结果写入：<SESSION_DIR>/research/web.md
   文件格式见下方"结果文件格式"
2. 你的整个对话回复只能是一行："Done: web"
   不许在对话里返回摘要、解释或任何其他文字。
```

---

**源码 subagent prompt：**（仅当阶段 A 确认有相关源码时派出）

```
【1-3 同联网，但维度改为"源码"，工具范围改为 Grep、Read、Glob，不要做改为"不联网、不查记忆"】

【4. 执行指令】
先依次读取以下文件：
1. ~/.agents/skills/heavy-research/references/research-loop-core.md
2. ~/.agents/skills/heavy-research/references/subagent-source.md

【5. 输出契约】
结果写入：<SESSION_DIR>/research/source.md
回复只能是："Done: source"
```

---

**记忆 subagent prompt：**

```
【1-3 同联网，但维度改为"记忆"，工具范围改为 brv query 和 Read（findings.md），不要做改为"不联网、不读源码"】

【4. 执行指令】
先依次读取以下文件：
1. ~/.agents/skills/heavy-research/references/research-loop-core.md
2. ~/.agents/skills/heavy-research/references/subagent-memory.md

【5. 输出契约】
结果写入：<SESSION_DIR>/research/memory.md
回复只能是："Done: memory"
```

---

**结果文件格式**（每个 subagent 写入自己的 md 文件）：

```markdown
# <维度> 调研报告 — YYYY-MM-DD-HHmm

## 子问题 #1：<提纲中的原文>
### 已确认结论
- <结论>
  - 来源：<URL 或文件路径或 brv 节点>
  - 置信度：confirmed / unverified
  - 推理：<为什么这个结论成立，1-2 句>

### 已尝试但未覆盖
- 尝试：<查询或路径>
- 原因：<无结果 / 结果矛盾 / 超出范围>

## 子问题 #2：...

## 元数据
- tool call 总次数：N
- 树形覆盖率：X/Y 叶节点
- 调研轨迹摘要：<3-5 行 reasoning trace 摘要>
```

### B3：等待所有 subagent 完成

收到所有 "Done: <dimension>" 回复后，读取 `<SESSION_DIR>/research/` 下的 md 文件，进入 B4。

### B4：综合摘要

按 `references/synthesis-prompt.md` 的模板，将各份报告综合为统一摘要：
- 按子问题编号对齐 3 份文件
- 每条信息标注来源维度
- 冲突显式标注 `⚠️ CONFLICT`

---

## 阶段 C：与用户讨论调研结果

在 terminal 输出综合摘要后，询问用户：

> 以上是本轮调研摘要。请问：
> 1. **方案合理** → 我将基于此摘要写 deployment-plan
> 2. **方案不合理** → 请告诉我哪里有问题，回到阶段 A 重新澄清

**用户选 1** → 进入阶段 D

**用户选 2** → 回到阶段 A，继续讨论，再次等用户说"开始调研"后重新执行阶段 B（复用同一 SESSION_DIR，覆盖 research/ 下的文件）

---

## 阶段 D：写 deployment-plan

按 `references/deployment-plan-template.md` 的模板，将内容写入：

```
<SESSION_DIR>/deployment-plan.md
```

写完后告知用户文件路径，任务结束。

---

## 约束

- 所有调研必须在 context compaction 触发之前完成（单 session 内完成）
- 阶段 B 期间不中途暂停问用户，澄清在阶段 A 一次性完成
- 调研摘要确认前不写 deployment-plan
