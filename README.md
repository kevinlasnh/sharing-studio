# Agent 三层记忆架构

> 一套给 AI coding agent（Claude Code / Codex / Gemini CLI）用的**长期记忆系统**。核心是两份 `CLAUDE.md` 配置，直接可复制粘贴使用。

## 这是什么

如果你在用 Claude Code / Codex / Gemini CLI 做复杂项目，大概率踩过以下坑：

- Session 一 clear 就忘光，每次都要重新解释项目背景
- 十个仓库里的决策和踩坑散落各处，下次又重新踩一遍
- 个人知识库（笔记、日记、资料）和 AI 工作记忆混在一起，越用越乱

这套方案把 agent 记忆**分成三层**，每层用独立工具栈、独立触发词，互不污染：

| 层 | 作用域 | 核心工具 | 回答什么问题 |
|---|---|---|---|
| **L1** | 单个 git 仓库内 | PWF 三件套 + ByteRover | 当前任务做到哪了？这个 bug 之前怎么修的？ |
| **L2** | 个人跨项目知识库 | Obsidian + Basic Memory MCP | AI 注意力机制是什么？我学过的 NBA 战术？ |
| **L3** | 家庭多成员共享 | 未落地 | 家庭决策、共享知识 |

本仓库只放**规则文件原文**：

- **[`L1-global-CLAUDE.md`](./L1-global-CLAUDE.md)** — 全局配置，放在 `~/.claude/CLAUDE.md`。定义 L1 的三小层（context window / PWF / ByteRover）、6 个触发词、沉淀流程、多 worktree 规则、路径守卫
- **[`L2-vault-CLAUDE.md`](./L2-vault-CLAUDE.md)** — Vault 项目级配置，放在你的 Obsidian vault 根目录。定义 4 个核心动作（Ingest / Query / Lint / Journal）、Obsidian Markdown 强制注入规则、search-before-write / pending-review 等对冲机制

## 快速开始

### 只想看设计思路

直接读 `L1-global-CLAUDE.md` 和 `L2-vault-CLAUDE.md`。两份文件**自成体系**，不需要额外文档。

### 想实际部署

1. **部署 L1**（任何 git 仓库都会用到）
   ```bash
   # 把 L1-global-CLAUDE.md 内容拷贝到你的全局配置
   cp L1-global-CLAUDE.md ~/.claude/CLAUDE.md

   # Codex 用户
   cp L1-global-CLAUDE.md ~/.codex/AGENTS.md
   # 把 H1 改成 "# Codex Global Configuration"

   # Gemini CLI 用户
   cp L1-global-CLAUDE.md ~/.gemini/GEMINI.md
   # 把 H1 改成 "# Gemini CLI Global Configuration"
   ```

   然后装 [planning-with-files](https://github.com/Bryce-Tang/planning-with-files) plugin（L1-2 的核心）和 [ByteRover CLI](https://byterover.dev)（L1-3 的核心，可选）。

2. **部署 L2**（需要 Obsidian vault）
   ```bash
   # 把 L2-vault-CLAUDE.md 放到你的 vault 根目录
   cp L2-vault-CLAUDE.md /path/to/your/vault/CLAUDE.md
   ```

   然后装：
   - [Basic Memory MCP](https://github.com/basicmachines-co/basic-memory)：`uv tool install basic-memory`
   - [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) plugin
   - [AgriciDaniel/claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) plugin
   - Obsidian 1.12+ 桌面版

3. **按需替换占位符**
   - `<your-username>` → 你的用户名
   - `<vault-path>` → 你的 vault 绝对路径

## 关键设计决策

### 为什么 L1 要再分三小层

| 小层 | 工具 | 生命周期 |
|---|---|---|
| L1-1 | 模型原生 context window | session 级，易失 |
| L1-2 | PWF 三件套（`task_plan.md` / `findings.md` / `progress.md`） | 任务级 / 项目级 |
| L1-3 | ByteRover（`.brv/context-tree/`） | 跨月份，结构化知识树 |

**核心思路**：L1-1 → L1-2 是**机械触发**（PWF hooks 自动注入），L1-2 → L1-3 是**主观判断**（任务结束时人工筛选哪些值得跨任务保留）。中间这道主观筛选闸拒绝把噪声沉淀到长期。

### 为什么 L1 和 L2 要严格隔离

- L1 触发词：`进入工作状态` / `记录工作进度` / `沉淀知识` / `审计长期记忆` / `查一下长期记忆`
- L2 触发词：全部含`第二大脑`锚点（`整理进我的第二大脑` / `检查下我的第二大脑`）
- **路径守卫**：CWD 在 vault 路径下时，主动跳过 L1 的所有 SessionStart 提示

两套触发词语义正交，任何输入只会命中一套。L1 的 PWF 文件**永不进入** vault，反之亦然。

### 为什么 L2 不能 100% AI 托管

实测结论：长期跑不通。AI 会幻觉 wikilink、重复创建已存在的概念页、累积孤儿页。必须接受每周 5 分钟 + 每月 1 小时人工审计。对冲机制：

1. **search-before-write** — 每次 ingest 前强制搜索，防重复
2. **pending-review** — 高风险操作（新建领域 / 删页 / 合并）必须人工审批
3. **`_index.md` 配额** — 每域 ≤50 条，超限提议拆分
4. **wiki-lint 月度审计** — 8 项检查（孤儿页 / 死链 / 过时声明 / ...）

### 为什么两份 CLAUDE.md 分开而不合并

- L1 是**全局**配置，所有项目共用
- L2 是**项目级**配置，只对 vault 目录生效
- Claude Code 的读取机制：全局 `~/.claude/CLAUDE.md` + 项目根 `CLAUDE.md` 自动合并进 context
- 分开写避免在非 vault 仓库里误触发 L2 规则

## 工具栈速查

| 工具 | 用途 | License | 必需性 |
|---|---|---|---|
| [planning-with-files](https://github.com/Bryce-Tang/planning-with-files) | L1-2 PWF 三件套 + 4 个 hooks | MIT | L1 必需 |
| [ByteRover CLI](https://byterover.dev) | L1-3 长期知识树 | 本地模式免费 | L1 可选 |
| [Basic Memory MCP](https://github.com/basicmachines-co/basic-memory) | L2 语义层 + search_notes | AGPL | L2 必需 |
| [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | Obsidian Markdown 语法规范 | MIT | L2 必需 |
| [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) | wiki-ingest / query / lint skill | MIT | L2 必需 |
| [Obsidian](https://obsidian.md) | 笔记 GUI + 1.12+ CLI | 免费个人版 | L2 必需 |

## 引用

如果这套方案对你有帮助，欢迎 star 🌟。引用本仓库时请注明：

```
Agent 三层记忆架构
https://github.com/<your-github>/agent-mem-architecture-design
CC-BY-SA 4.0
```

## License

[CC-BY-SA 4.0](./LICENSE) — 自由使用、修改、分发，请署名并以相同协议共享衍生作品。
