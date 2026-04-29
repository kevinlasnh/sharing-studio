---
title: AGENTS
type: note
permalink: second-brain/agents
---

# Second Brain — Vault Router

> L2 个人知识库。Agent 在 `<vault-path>\` 内工作时，以本文件作为路由入口；具体操作流程按需加载本地 skill。

## Vault 概览

- **路径**：`<vault-path>\`
- **同步**：Google Drive
- **定位**：跨项目、跨领域的个人 Second Brain vault
- **底层**：Basic Memory MCP / daemon + Obsidian 原生 Markdown vault
- **业务层**：本地 second-brain skills
- **语法层**：全局 `obsidian-markdown` skill
- **确定性防线**：`.claude/settings.json` hooks + `.claude/scripts/*.ps1`
- **Obsidian CLI 前置**：需要 Obsidian 桌面端已打开，CLI 才能通过 IPC 操作应用状态

## Basic Memory MCP / Daemon

Basic Memory 是本 vault 的底层存储与检索基础设施，不是 skill。

- `search_notes`：优先用于 vault 检索，走 BM25 + fastembed / bge-small-en-v1.5 hybrid search。
- `write_note`：可用于创建 note，但文件名生成不完全可靠。
- `move_note`：用于修正 Basic Memory 生成的不合规文件名。
- 所有 Basic Memory MCP 调用必须显式传 `project: second-brain`；CLI fallback 必须显式带 `--project second-brain`，不依赖 Basic Memory 的当前默认 project。MCP 工具名使用下划线；CLI 工具入口使用 `basic-memory tool <tool-name>`，例如 `basic-memory tool search-notes "<query>" --project second-brain --page-size 10`。Basic Memory 0.20.3 CLI 未暴露 `move-note`，文件名修正优先用 MCP `move_note`；MCP 不可用时，用 Obsidian CLI / 文件系统移动后立即跑 `basic-memory reindex --project second-brain` 与 status 验证。
- daemon 自动给 Markdown 文件维护 `permalink:`；agent 不手写、不修改 `permalink`。
- `kebab_filenames: true` 已启用，但中文 title、`and/or`、数字、标点、`_index.md` 仍可能生成错误文件名。
- `search_notes` 只有在 Basic Memory 文件索引与磁盘同步时才可作为主检索依据；若 `basic-memory status --project second-brain --json` 非 clean，或搜索片段明显与磁盘文件不一致，必须改用 Grep 文件系统 fallback，并报告 Basic Memory 索引待同步。
- Basic Memory 搜索结果必须按 `file_path` 过滤：wiki 内容候选只接受 `wiki/{domain}/{slug}.md` 且非 `_index.md`；`index.md` / `_index.md` 只作导航证据；`daily/` 默认排除，只有用户明确询问日记、时间线或 session 历史时才作普通路径/日期证据；`CLAUDE.md`、`AGENTS.md`、`.claude/**`、`.obsidian/**`、`raw/**` 不能作为知识页候选。

Agent 约束：

- `write_note` 的 title 必须用英文；中文只能放 H1 和正文。
- 每次 `write_note` 后必须验证实际文件名。
- wiki 内容页文件名必须是 lowercase English kebab-case。
- 域索引文件名必须是 `wiki/{domain}/_index.md`。
- 不符合命名规则时立即用 `move_note` 修正。

## 目录结构

```text
second-brain/
├── CLAUDE.md                 # 本文件：vault router
├── AGENTS.md                 # Codex 同步 router
├── index.md                  # 总目录，指向各域 _index.md
├── daily/                    # 日记，YYYY-MM-DD.md
├── wiki/                     # 结构化知识库
│   └── {domain}/
│       ├── _index.md         # 域内目录
│       └── *.md              # wiki 内容页
├── raw/                      # 用户主动放入的 immutable 原始素材
├── .obsidian/                # Obsidian 配置
└── .claude/
    ├── settings.json         # hooks
    ├── scripts/              # PowerShell 硬防线
    └── skills/               # vault 本地 skills
```

## Router Sync

`CLAUDE.md` 与 `AGENTS.md` 是本仓库的同步 router 文件。Claude Code 和 Codex 都可以管理这个 vault，二者必须看到同一套高层规则。

- 修改 `CLAUDE.md` 或 `AGENTS.md` 任一文件时，必须立即同步另一份。
- 为避免 Obsidian permalink 冲突，frontmatter 保持文件专属：`CLAUDE.md` 使用 `title: CLAUDE` + `permalink: second-brain/claude`，`AGENTS.md` 使用 `title: AGENTS` + `permalink: second-brain/agents`。
- frontmatter 以下正文必须保持完全一致。
- 原 `AGENTS.md` 中的 Codex 外部健康检查协议已转为本地 skill：`second-brain-vault-audit`。

## Skill Stack

本 vault 的运行逻辑由 7 个 skill 组成：

| 层 | Skill | 用途 |
|---|---|---|
| 语法底座 | `obsidian-markdown` | 创建/编辑 Obsidian Flavored Markdown；写 `wiki/**/*.md` 前必须加载 |
| 业务动作 | `second-brain-ingest` | 将文本、URL、raw 文件、讨论上下文整理进 wiki |
| 业务动作 | `second-brain-query` | 只读查询 vault 已有知识 |
| 业务动作 | `second-brain-lint` | 健康检查、死链、frontmatter、索引、语义互链审计 |
| 业务动作 | `second-brain-journal` | 写入/追加 `daily/YYYY-MM-DD.md`，覆盖 ingest manifest |
| 业务动作 | `second-brain-graph-manager` | 维护 `.obsidian/graph.json` 的 5 条 colorGroups 与附件节点颜色 |
| 维护动作 | `second-brain-vault-audit` | 仓库级外部健康度检查：router、skills、hooks、MCP、Obsidian、Basic Memory、scaffold 闭环 |

调用规则：

- 任何写入 `wiki/**/*.md` 的动作必须先加载 `obsidian-markdown`。
- `obsidian-markdown` 只提供 Obsidian 语法底座；当它与本 vault 的 schema / hooks 更严格规则冲突时，以本 vault 为准：内部 note 链接必须用 wikilink，frontmatter 数组必须用多行 YAML。
- `second-brain-ingest` 写 wiki 前必须先完成 domain-routing preflight（读取 root `index.md`、所有 domain `_index.md`、检索候选页面、输出 manifest 并等用户确认）；写 wiki 时同时使用 `obsidian-markdown`，并按需引用 `second-brain-lint` 的互链审计规则。
- `second-brain-lint` 默认只报告；进入 fix pass 写 wiki 时必须加载 `obsidian-markdown`。
- `second-brain-query` 只读，默认不加载 `obsidian-markdown`，也不写 vault。
- `second-brain-journal` 写 `daily/`，日记不使用任何内部链接；提到 wiki 页面时用普通文本 slug 或 `wiki/{domain}/{slug}.md` 路径；只允许 `http(s)` 外部链接。
- `second-brain-graph-manager` 写 JSON，不需要 `obsidian-markdown`。
- `second-brain-vault-audit` 是仓库级外部健康检查入口；当用户要求“仓库健康度外部检查”、完整 vault audit、Codex/Claude router 维护、hooks/MCP/Obsidian/Basic Memory 闭环验证时加载。

## 动作执行契约

用户触发本 vault 的业务动作时，agent 必须先加载对应本地 skill，并把该 skill 的 `Workflow` / `Retrieval Order` / `Checks` / `Completion Criteria` 当作强制流程执行。用户不需要额外说“按照 skill 流程仔细走”；所有第二大脑动作默认都等价于包含这条要求。

适用范围：

- 四个主要业务动作：`second-brain-ingest`、`second-brain-query`、`second-brain-lint`、`second-brain-journal`。
- 支撑动作：`second-brain-graph-manager`。当它被用户直接触发，或被 ingest / lint 间接触发时，也必须完整执行自己的 workflow。
- 维护动作：`second-brain-vault-audit`。当用户要求仓库级外部健康检查或 router/skill/hook/MCP 维护时，必须完整执行自己的 audit workflow。

执行规则：

- 从对应 skill 的第 1 步开始按顺序推进，不得只完成前几步后提前总结。
- 只允许在以下情况暂停：skill 明确要求等待用户确认；源材料、工具或权限真实不可用；继续执行会改变语义内容且需要用户确认。
- 暂停后用户确认或补充资料时，从已暂停的下一步继续执行，不重新解释流程、不跳过剩余步骤。
- 最终回复前必须对照该 skill 的 completion / closure 条件；缺任一条件时报告 blocked / deferred / residual-risk，不得声称完成或 clean。
- `second-brain-ingest` 的 preflight manifest 和 journal yes/no 是确认门，不是提前结束点；确认后必须继续执行写入、索引同步、manifest、journal closure 或 deferred 标记。
- `second-brain-lint` 不能只跑确定性脚本就声称全面审计完成；full audit 必须覆盖 skill 里列出的全部检查和必要的人工语义检查。

### Claude Code 交互提问规则

- 在 Claude Code 中，任何本地 skill workflow 需要向用户确认、二选一/三选一、澄清范围、确认 preflight manifest、确认是否写入 journal、确认 fix pass、确认语义改动或新 domain 时，必须调用 Claude Code 的 `AskUserQuestion` 工具，不得只在普通文本回复里提问。
- `AskUserQuestion` 问题应保持 1-3 个短问题；能列选项时给 2-3 个互斥选项，并把推荐项标为 `(Recommended)`；不确定用户自由输入时保留自由输入路径。
- 如果当前宿主不是 Claude Code 或未暴露 `AskUserQuestion`，使用该宿主的原生等价交互提问机制；若没有等价工具，才退回简短普通文本提问并说明工具不可用。
- 使用 Claude Code SDK 或自定义宿主时，若限制 `tools` 列表，必须显式允许 `AskUserQuestion`；否则 skill 的确认门可能退化成普通文本或被宿主拦截。

## L2 触发路由

用户输入含「第二大脑」时，语义匹配以下动作：

| 触发意图 | 本地 skill |
|---|---|
| “把这些东西都整理进我的第二大脑里面” / ingest / 沉淀到第二大脑 | `second-brain-ingest` |
| “检查下我的第二大脑，看看之前学过这些相关的内容吗” / 查旧知识 | `second-brain-query` |
| “审计一下第二大脑的知识库，做一下健康检查” / lint / 检查双链 | `second-brain-lint` |
| “仓库健康度外部检查” / 外部 vault audit / Codex 维护 router、skills、hooks、MCP | `second-brain-vault-audit` |
| “写一下第二大脑日记” / 日记 | `second-brain-journal` |
| “重刷图谱颜色” / 图谱色组 / 新建域后验证 | `second-brain-graph-manager` |

不再运行时引用外部 wiki-ingest / wiki-query / wiki-lint。它们只作为本地 second-brain skill 的上游设计来源。

## Hooks 与硬防线

`.claude/settings.json` 保留以下 hooks：

| Layer | 时机 | 机制 |
|---|---|---|
| L2 启动守卫 | `SessionStart` | 注入 L2 BOOT，跳过 L1/PWF，不创建 `task_plan.md` / `progress.md` / `findings.md` |
| 路径策略 | `PreToolUse` | `.claude/scripts/wiki-path-policy.ps1` 阻止废弃脚手架 |
| 写入提醒 | `PreToolUse` | `.claude/scripts/wiki-write-reminder.ps1` 提醒加载 `obsidian-markdown` |
| 语法预检 | `PreToolUse` | `.claude/scripts/wiki-prewrite-syntax-check.ps1` 阻止确定性 wiki Markdown 违规写入 |
| 链接语义 | `PreToolUse` prompt | 对新增 wiki 内容页 wikilink 做轻量语义审查 |
| 语法复检 | `PostToolUse` | `.claude/scripts/wiki-syntax-check.ps1` 事后复查并把违规反馈给 agent 立即修复 |
| 日记隔离 | `PreToolUse` / `PostToolUse` | `.claude/scripts/daily-no-link-policy.ps1` 阻止 `daily/*.md` 产生 Obsidian 图谱边 |
| Raw 来源边界 | `PreToolUse` / `PostToolUse` | `.claude/scripts/raw-link-policy.ps1` 阻止 raw 被 index/daily/frontmatter/Markdown link 误用 |

PowerShell 脚本读写中文时必须显式使用 UTF-8。

## 禁用脚手架

以下路径不属于本 vault 架构，禁止创建：

- `wiki/log.md`
- `wiki/hot.md`
- `wiki/ingest-log.md`
- `wiki/sources/**`
- `.raw/**`
- `wiki/overview.md`
- `wiki/index.md`
- `wiki/meta/dashboard.md`
- `wiki/meta/overview.canvas`
- `wiki/**/*.canvas`

对应职责已经由 `daily/`、页面 frontmatter、root `raw/`、root `index.md`、Obsidian Graph View 和 lint 对话报告承担。

## Wiki 基本边界

- root `index.md` 只指向各域 `_index.md`。
- `_index.md` 只列同域 wiki 内容页。
- wiki 内容页可链接 wiki 内容页；跨域链接必须有正文关系句支撑。
- daily 是时间线，不参与知识图谱；`daily/*.md` 禁止任何 `[[wikilink]]` 和本地/相对 Markdown link，只允许 `http(s)` 外部链接。日记提到 wiki 页面时使用普通文本、slug 或 `wiki/{domain}/{slug}.md` 路径。
- Obsidian Graph 默认不强制设置全局 `search` 过滤器；可以显示全 vault 节点。daily 的低噪音目标靠“无内部链接”实现，而不是靠隐藏节点实现。
- raw 文件 immutable；仅用户主动提供的原始素材、以及用户从 Web AI / 浏览器拖入终端形成的图片 URL 下载件进入 root `raw/`，不进入 root `index.md`、域 `_index.md`、daily 或 query answer source。
- raw 只能由 `wiki/{domain}/{content-page}.md` 正文引用。非图片附件和证据型图片使用明确来源/证据/provenance 语句中的普通 wikilink `[[raw/file.ext]]`；教学图解、流程图、示意图、截图讲解等图片素材允许在语义合适位置用 Obsidian embed `![[raw/file.png]]` / `![[raw/file.png|600]]` 直接显示。禁止 `[[Raw/...]]`、`[[./raw/...]]`、`[[../raw/...]]`、`[[/raw/...]]`、`[[file.ext]]` 裸附件名、本地 Markdown 附件链接等大小写、相对、绝对、隐式或 basename 变体。即使 raw 文件尚未放入 `raw/`，source/evidence/provenance 语境中的本地附件引用也必须直接写成 `[[raw/file.ext]]`。`wiki content page -> raw file` 只表示来源、证据或教学视觉素材，不表示概念双链、导航、推荐阅读、同批 ingest 或图谱连通性。
- 当用户把 Web AI 生成图片从浏览器拖到终端形成图片 URL 时，ingest agent 必须读取图片 URL、做多模态分析、按图片语义生成英文 kebab-case 文件名、下载到 `raw/`，再根据图片内容和目标 Markdown 文档语义，把图片 embed 到最合适的段落附近；不得把所有图片机械堆到文末。
- Markdown 图片显示由 `.obsidian/snippets/second-brain-markdown-images.css` 全局控制：wiki 内容页中的 Obsidian image embed 和独立 Markdown 图片默认横向居中。Agent 不得为了居中在正文里包 HTML / `<style>` / inline CSS；正文保持 canonical `![[raw/file.png|600]]` 或普通 Markdown 图片语法。
- `raw/` 不存 `.md`；Markdown 原文必须改存为 `.txt`、`.pdf`、原始附件格式，或直接 ingest 进 `wiki/`，避免 raw Markdown 的内部链接进入图谱。
- `CLAUDE.md` 与 `AGENTS.md` 是 agent 配置文件，不参与知识图谱互链；Obsidian Graph 中二者使用同一个 agent config 颜色组。

详细页面 schema 见 `.claude/skills/second-brain-ingest/references/page-schema.md`。

详细内容页互链审计规则见 `.claude/skills/second-brain-lint/references/content-page-link-audit.md`。

详细 raw 来源链接规则见 `.claude/skills/second-brain-lint/references/raw-link-policy.md`。

## L1 / L2 / L3 边界

- **L1**：单仓库 PWF + ByteRover 任务记忆。触发词不含「第二大脑」锚点；本 vault 明确禁用 L1/PWF。
- **L2**：本 vault，跨项目跨领域个人知识库。
- **L3**：家庭图谱，尚未落地。

本目录位于 L2 vault 内时，忽略全局 L1/PWF SessionStart 提示，不加载 `planning-with-files`，不创建 PWF 三件套。
