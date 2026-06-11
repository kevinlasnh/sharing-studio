---
title: CLAUDE
type: note
permalink: second-brain/claude
---

# Second Brain — Vault Router

> L2 个人知识库。Agent 在 `<vault-path>\` 内工作时，以本文件作为路由入口；具体操作流程按需加载本地 skill。

## Vault 概览

- **路径**：`<vault-path>\`
- **同步**：Google Drive
- **定位**：跨项目、跨领域的个人 Second Brain vault
- **底层**：Basic Memory MCP / daemon + Obsidian 原生 Markdown vault
- **业务层**：本地 second-brain skills（`.claude/skills` / `.agents/skills` / `.gemini/skills` 三宿主同步）
- **语法层**：全局 `obsidian-markdown` skill
- **确定性防线**：`.claude/settings.json` hooks + `.claude/scripts/*.ps1`
- **Obsidian CLI 前置**：需要 Obsidian 桌面端已打开，CLI 才能通过 IPC 操作应用状态

## Basic Memory MCP / Daemon

Basic Memory 是本 vault 的底层存储与检索基础设施，不是 skill。它负责语义候选召回；磁盘 Markdown 正文仍是最终事实源。

- `search_notes`：默认用于所有跨页面、大范围语义检索，走 BM25 + fastembed / bge-small-en-v1.5 hybrid search。
- `write_note`：可用于创建 note，但不是唯一写入入口；所有创建结果仍必须通过路径、文件名、frontmatter / `permalink` 校验。
- `move_note`：用于修正 Basic Memory 生成的不合规文件名。
- 所有 Basic Memory MCP 调用必须显式传 `project: second-brain`；CLI fallback 必须显式带 `--project second-brain`，不依赖 Basic Memory 的当前默认 project。MCP 工具名使用下划线；CLI 工具入口使用 `basic-memory tool <tool-name>`，例如 `basic-memory tool search-notes "<query>" --project second-brain --page-size 10`。Basic Memory 0.20.3 CLI 未暴露 `move-note`，文件名修正优先用 MCP `move_note`；MCP 不可用时，用 Obsidian CLI / 文件系统移动后立即跑 `basic-memory reindex --project second-brain` 与 status 验证。
- 在 Windows 上，Basic Memory CLI 命令必须串行执行，不要把 `status`、`tool search-notes`、`project info`、`reindex` 放进同一轮并行工具调用；Basic Memory 0.20.3 的日志清理可能在并发 CLI 进程间触发临时 FileNotFoundError 假失败。
- Basic Memory 配置中的 `ensure_frontmatter_on_sync` 必须保持 `false`。daemon 只负责监听、索引和检索，不再后台补写或改写 Markdown frontmatter，避免 Google DriveFS 上的原子替换竞争。
- `permalink:` 由 vault schema 确定性维护：agent 不自由编写 `permalink`；新建或修复 Markdown 时必须按文件路径公式写入 / 校正。
- `kebab_filenames: true` 已启用，但中文 title、`and/or`、数字、标点、`_index.md` 仍可能生成错误文件名。
- Basic Memory 搜索结果必须按 `file_path` 过滤：wiki 内容候选只接受 `wiki/{domain}/{slug}.md` 且非 `_index.md`；`index.md` / `_index.md` 只作导航证据；`daily/` 默认排除，只有用户明确询问日记、时间线或 session 历史时才作普通路径/日期证据；`CLAUDE.md`、`AGENTS.md`、`GEMINI.md`、`.claude/**`、`.agents/**`、`.gemini/**`、`.claudian/**`、`.workflows/**`、`.brv/**`、`.obsidian/**`、`templates/**`、`raw/**` 不能作为知识页候选。

### Basic Memory-first Semantic Retrieval Contract

所有跨页面、大范围语义候选发现必须先用 Basic Memory，而不是直接用 Grep / `rg`。适用范围包括 `second-brain-ingest` 的 domain-routing 与 search-before-write、`second-brain-query` 的普通查询与 domain-placement、`second-brain-lint` 的 taxonomy / missing-page / stale-claim / semantic-link 候选发现，以及 `second-brain-vault-audit` 的检索能力探针。

执行顺序：

1. 先运行 `basic-memory status --project second-brain --json` 做 freshness gate。
2. 若 status clean，优先用 Basic Memory MCP `search_notes(project: second-brain)` 检索。
3. 若 status dirty，先运行一次 `basic-memory reindex --project second-brain --search`，再复查 status；复查 clean 后继续使用 Basic Memory MCP。
4. 若当前宿主没有暴露 MCP 工具，但 Basic Memory CLI 可用，用 `basic-memory tool search-notes "<query>" --project second-brain --page-size <n>` 作为 Basic Memory CLI fallback；这仍优先于 Grep。
5. 只有在 MCP/CLI 不可用、一次 `--search` reindex 后仍 dirty、或 Basic Memory 结果与磁盘正文明显矛盾时，才使用 Grep / `rg` 文件系统 fallback。
6. Grep fallback 必须在最终回复或 manifest 中显式报告原因，不能静默发生。
7. 无论结果来自 MCP、CLI 还是 Grep，都必须打开候选 Markdown 正文确认；不能只根据 title、tag、`_index.md`、score 或 snippet 决策。

`project info` 里的 embedding `reindex_recommended` 或 sqlite-vec 环境提示是向量维护问题；只要 `status` clean 且 `search_notes` / CLI search 实际可用，不阻塞入口检索。完整 embeddings reindex 由 `second-brain-journal` 在写完日记的最终 checkpoint 执行；日记之外只作为单独维护任务处理。Basic Memory 0.20.3 可能出现 `project info` 误报 sqlite-vec unavailable 的显示假阳性；若同一 uv tool 环境可 `import sqlite_vec`、`search_vector_embeddings` 与 `search_vector_chunks` 有有效行数、活动配置/路由文件无旧 MCP 残留、且 search probe 返回当前磁盘正文，则按 informational 记录，不切换到 Grep fallback。

### Adaptive Reindex Closure

Basic Memory 的 sync closure 用来保证下一次核心操作开始时索引应当 clean。正常 ingest 写入日记时，closure 由 `second-brain-journal` 作为最后同步点执行，并且默认跑 search + embeddings；随后必须 handoff 给 `second-brain-hf-backup` 完成 Hugging Face 远端 Git 快照。其他写入型维护流程必须在自己的 workflow 末尾执行 status/reindex/status 闭环，不能把 dirty 状态留给下一次 ingest。

- 写入型工作流的完整闭环是：完成 wiki/raw/index 等内容写入 → 写 `daily/YYYY-MM-DD.md` 日记 → 由 `second-brain-journal` 做 Basic Memory adaptive reindex closure → 由 `second-brain-hf-backup` 做 Hugging Face full Git snapshot push closure。
- `second-brain-journal` 写完并复检日记后，必须运行 `basic-memory status --project second-brain --json`。
- `second-brain-journal` 无论首个 status 是否 clean，都必须通过 CLI 运行 `basic-memory reindex --project second-brain`；Basic Memory 0.20.3 未暴露显式 reindex MCP tool。该默认命令同时重建 full-text search 与 embeddings。embeddings reindex 会扫描全项目，但用 chunk hash 跳过未变化 chunk，适合作为日记后的批量收口。
- journal reindex 后必须再次运行 `basic-memory status --project second-brain --json` 验证 clean；如果 search 或 embeddings 任一失败，必须报告 residual-risk，不能声称完全闭环。
- journal 的 Basic Memory closure attempt 完成后，必须调用 `second-brain-hf-backup` 执行 `git add -A`、`git commit`、`git lfs push hf HEAD`、`git push hf HEAD:main`。若 Basic Memory 有 residual-risk，仍执行 HF backup handoff，并在最终回复中分别报告 Basic Memory 状态与 Git backup 状态。
- 若用户在 ingest 后明确暂缓日记，ingest 仍必须对已经写入的 wiki/raw/index 变化执行 interim search-only closure，并在最终回复中同时说明 `Journal pending`、Basic Memory file-sync clean/residual-risk 状态，以及 full embeddings checkpoint 与 HF backup deferred until journal；之后补写日记时由 `second-brain-journal` 执行默认 search + embeddings closure，并继续 handoff 给 `second-brain-hf-backup`。
- `second-brain-query` 是 vault 文件只读，但允许执行一次 `basic-memory reindex --project second-brain --search` 修复本地索引后继续使用 Basic Memory；这不算写 vault。report-only lint 同样可执行入口 freshness gate。纯 `.obsidian/**` 图谱配置修复不触发 Basic Memory reindex，除非 status 已显示相关 Markdown 变化。
- `second-brain-lint` fix pass、router/skill 维护、文件名移动、Obsidian/file-system move 等任何会改变 vault 内 Markdown 的流程，结束前必须运行 status/reindex/status，或报告 residual-risk，不能声称 clean。

Agent 约束：

- `write_note` 的 title 必须用英文；中文只能放 H1 和正文。
- 每次 `write_note` 后必须验证实际文件名。
- wiki 内容页文件名必须是 lowercase English kebab-case。
- 域索引文件名必须是 `wiki/{domain}/_index.md`。
- 新建或修复 wiki 内容页必须包含 `permalink: second-brain/wiki/{domain}/{slug}`，其中 `{slug}` 是不带 `.md` 的文件名。
- 新建或修复域索引必须包含 `permalink: second-brain/wiki/{domain}/index`。
- 新建或修复日记必须包含 `permalink: second-brain/daily/YYYY-MM-DD`。
- root `index.md` 使用 `permalink: second-brain/index`；router 文件使用各自专属 permalink：`second-brain/claude`、`second-brain/agents`、`second-brain/gemini`。
- 每次 Markdown 写入后必须验证文件真实存在、大小非零、frontmatter 可读，且 `permalink` 与路径公式一致。
- 不符合命名规则时立即用 `move_note` 修正。

## 目录结构

```text
second-brain/
├── CLAUDE.md                 # Claude Code router
├── AGENTS.md                 # Codex router
├── GEMINI.md                 # Gemini CLI router
├── index.md                  # 总目录，指向各域 _index.md
├── daily/                    # 日记，YYYY-MM-DD.md
├── templates/                 # Obsidian 模板，如 daily.md
├── wiki/                     # 结构化知识库
│   └── {domain}/
│       ├── _index.md         # 域内目录
│       └── *.md              # wiki 内容页
├── raw/                      # 用户主动放入的 immutable 原始素材
├── .claudian/                # Claudian 宿主 UI 状态；非知识库内容
├── .workflows/               # heavy workflow 产物；本地 agent 状态，非知识库内容
├── .brv/                     # ByteRover 本地状态；非知识库内容
├── .obsidian/                # Obsidian 配置
├── .claude/
│   ├── settings.json         # Claude hooks
│   ├── scripts/              # PowerShell 硬防线
│   └── skills/               # Claude 本地 skills
├── .agents/
│   └── skills/               # Codex / cross-agent 本地 skills
└── .gemini/
    └── skills/               # Gemini 本地 skills
```

## Router Sync

`CLAUDE.md` / `AGENTS.md` / `GEMINI.md` 是本仓库的同步 router 文件。Claude Code、Codex 和 Gemini CLI 都可以管理这个 vault，三者必须看到同一套高层规则。

- 修改 `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` 任一文件时，必须立即同步另外两份。
- 为避免 Obsidian permalink 冲突，frontmatter 保持文件专属：`CLAUDE.md` 使用 `title: CLAUDE` + `permalink: second-brain/claude`，`AGENTS.md` 使用 `title: AGENTS` + `permalink: second-brain/agents`，`GEMINI.md` 使用 `title: GEMINI` + `permalink: second-brain/gemini`。
- frontmatter 以下正文必须保持完全一致。
- 原 `AGENTS.md` 中的 Codex 外部健康检查协议已转为本地 skill：`second-brain-vault-audit`。

## Skill Stack

本 vault 的业务运行逻辑由 8 个本地 second-brain skill 组成；另有 1 个全局 `obsidian-markdown` 作为语法底座：

| 层 | Skill | 用途 |
|---|---|---|
| 语法底座 | `obsidian-markdown` | 创建/编辑 Obsidian Flavored Markdown；写 `wiki/**/*.md` 前必须加载 |
| 业务动作 | `second-brain-ingest` | 将文本、URL、raw 文件、讨论上下文整理进 wiki |
| 业务动作 | `second-brain-delete` | 通过 plan/apply/validate manifest 安全删除显式 wiki note、domain、raw、daily 或旧 workflow 产物 |
| 业务动作 | `second-brain-query` | 只读查询 vault 已有知识 |
| 业务动作 | `second-brain-lint` | 健康检查、死链、frontmatter、索引、语义互链审计 |
| 业务动作 | `second-brain-journal` | 写入/追加 `daily/YYYY-MM-DD.md`，覆盖 ingest/delete manifest，并统一执行 Basic Memory adaptive reindex closure 与 HF backup handoff |
| 支撑动作 | `second-brain-hf-backup` | 在 journal closure 后执行全量 `git add -A`、本地 commit、推送到 Hugging Face private dataset remote |
| 业务动作 | `second-brain-graph-manager` | 维护 `.obsidian/graph.json` 的 6 条 colorGroups（含 templates）与附件节点颜色 |
| 维护动作 | `second-brain-vault-audit` | 仓库级外部健康度检查：router、skills、hooks、MCP、Obsidian、Basic Memory、scaffold 闭环 |

调用规则：

- 任何写入 `wiki/**/*.md` 的动作必须先加载 `obsidian-markdown`。
- `obsidian-markdown` 只提供 Obsidian 语法底座；当它与本 vault 的 schema / hooks 更严格规则冲突时，以本 vault 为准：内部 note 链接必须用 wikilink，frontmatter 数组必须用多行 YAML。
- `second-brain-ingest` 写 wiki 前必须先完成 semantic fidelity pass 与 domain-routing preflight（读取 root `index.md`、所有 domain `_index.md`、检索候选页面、输出含 semantic coverage plan 的 manifest 并等用户确认）；写 wiki 时同时使用 `obsidian-markdown`，并按需引用 `second-brain-lint` 的互链审计规则。
- `second-brain-ingest` 必须执行 semantic fidelity pass：允许精炼、去重和重组，但必须保留关键语义、逻辑链、前提、限制、反例、决策依据、自我修正和未决问题。写前输出 semantic coverage plan，写后执行 coverage audit；P0 高风险压缩、舍弃、合并或不确定自我修正必须确认或报告 residual-risk。
- `second-brain-delete` 必须先生成 delete manifest，再凭 manifest confirmation token 执行 destructive apply，随后运行 validation report、Basic Memory closure、daily journal 与 HF backup closure。真实知识删除必须有 pre-delete backup gate，且工作区除显式 scoped 的 `.workflows/**` 产物外必须干净；基础设施路径、当前 workflow、wildcard、path escape 默认拒绝。
- `second-brain-lint` 默认只报告；进入 fix pass 写 wiki 时必须加载 `obsidian-markdown`。
- `second-brain-query` 只读，默认不加载 `obsidian-markdown`，也不写 vault。
- `second-brain-journal` 写 `daily/`，日记不使用任何内部链接；提到 wiki 页面或 delete manifest 路径时用普通文本 slug 或 `wiki/{domain}/{slug}.md` 路径；只允许 `http(s)` 外部链接。写完日记后统一判断并执行 Basic Memory adaptive reindex closure，然后调用 `second-brain-hf-backup` 做 Hugging Face full Git snapshot push closure。
- `second-brain-hf-backup` 是 journal 的最终远端备份闭环，也可被用户直接触发；它执行 `git add -A`、`git commit`、`git lfs push hf HEAD`、`git push hf HEAD:main`，遵循 Git 自身 `.gitignore` 规则，不绕过 ignore。
- 私有 Hugging Face backup 目标是 full vault snapshot；本地 pre-push 保护若存在，必须只对 remote 名称为 `hf` 且 URL 精确匹配 `<hf-private-dataset-url>` 的推送放行受保护 agent/vault 文件，其他 remote 继续阻断。
- `second-brain-graph-manager` 写 JSON，不需要 `obsidian-markdown`。
- `second-brain-vault-audit` 是仓库级外部健康检查入口；当用户要求“仓库健康度外部检查”、完整 vault audit、Claude/Codex/Gemini router 维护、hooks/MCP/Obsidian/Basic Memory 闭环验证时加载。

## 动作执行契约

用户触发本 vault 的业务动作时，agent 必须先加载对应本地 skill，并把该 skill 的 `Workflow` / `Retrieval Order` / `Checks` / `Completion Criteria` 当作强制流程执行。用户不需要额外说“按照 skill 流程仔细走”；所有第二大脑动作默认都等价于包含这条要求。

适用范围：

- 五个主要业务动作：`second-brain-ingest`、`second-brain-delete`、`second-brain-query`、`second-brain-lint`、`second-brain-journal`。
- 支撑动作：`second-brain-graph-manager`、`second-brain-hf-backup`。当它们被用户直接触发，或被 journal / ingest / lint 间接触发时，也必须完整执行自己的 workflow。
- 维护动作：`second-brain-vault-audit`。当用户要求仓库级外部健康检查或 router/skill/hook/MCP 维护时，必须完整执行自己的 audit workflow。

执行规则：

- 从对应 skill 的第 1 步开始按顺序推进，不得只完成前几步后提前总结。
- 只允许在以下情况暂停：skill 明确要求等待用户确认；源材料、工具或权限真实不可用；继续执行会改变语义内容且需要用户确认。
- 暂停后用户确认或补充资料时，从已暂停的下一步继续执行，不重新解释流程、不跳过剩余步骤。
- 最终回复前必须对照该 skill 的 completion / closure 条件；缺任一条件时报告 blocked / deferred / residual-risk，不得声称完成或 clean。
- `second-brain-ingest` 的 preflight manifest 和 journal yes/no 是确认门，不是提前结束点；确认后必须继续执行写入、manifest、journal closure 或 deferred 标记。若本次 ingest 写入日记，Basic Memory adaptive reindex closure 由 `second-brain-journal` 在日记写完后统一执行，随后必须调用 `second-brain-hf-backup` 做远端 Git 快照；若 journal deferred 但已经写入 wiki/raw/index，`second-brain-ingest` 必须先对这些 Markdown 变化执行 Basic Memory status/reindex/status 收口，之后补写日记时再由 `second-brain-journal` 对 daily 文件执行完整收口与 HF backup handoff。
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
| “从第二大脑删除...” / delete / remove / 删除 wiki 笔记、raw 附件、domain、显式 daily 或旧 workflow 产物 | `second-brain-delete` |
| “检查下我的第二大脑，看看之前学过这些相关的内容吗” / 查旧知识 | `second-brain-query` |
| “审计一下第二大脑的知识库，做一下健康检查” / lint / 检查双链 | `second-brain-lint` |
| “仓库健康度外部检查” / 外部 vault audit / Claude/Codex/Gemini 维护 router、skills、hooks、MCP | `second-brain-vault-audit` |
| “写一下第二大脑日记” / 日记 | `second-brain-journal` |
| “推送到 Hugging Face” / “备份第二大脑” / “HF backup” / journal closure 后自动远端备份 | `second-brain-hf-backup` |
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
- raw 只能由 `wiki/{domain}/{content-page}.md` 正文引用。非图片附件和证据型图片使用明确来源/证据/provenance 语句中的普通 wikilink `[[raw/file.ext]]`；教学图解、流程图、示意图、截图讲解等图片素材允许在语义合适位置用 Obsidian embed 直接显示，且必须带方向宽度：竖图（真实宽度小于高度）用 `![[raw/file.png|360]]`，横图或方图用 `![[raw/file.png|600]]`。禁止 `[[Raw/...]]`、`[[./raw/...]]`、`[[../raw/...]]`、`[[/raw/...]]`、`[[file.ext]]` 裸附件名、本地 Markdown 附件链接等大小写、相对、绝对、隐式或 basename 变体。即使 raw 文件尚未放入 `raw/`，source/evidence/provenance 语境中的本地附件引用也必须直接写成 `[[raw/file.ext]]`。`wiki content page -> raw file` 只表示来源、证据或教学视觉素材，不表示概念双链、导航、推荐阅读、同批 ingest 或图谱连通性。
- 当用户把 Web AI 生成图片从浏览器拖到终端形成图片 URL 时，ingest agent 必须读取图片 URL、做多模态分析、按图片语义生成英文 kebab-case 文件名、下载到 `raw/`，再根据图片内容和目标 Markdown 文档语义，把图片 embed 到最合适的段落附近；不得把所有图片机械堆到文末。
- Markdown 图片显示由 `.obsidian/snippets/second-brain-markdown-images.css` 全局控制：wiki 内容页中的 Obsidian image embed 和独立 Markdown 图片默认横向居中。Agent 不得为了居中在正文里包 HTML / `<style>` / inline CSS；raw 图片 embed 正文保持 canonical `![[raw/file.png|360]]` 或 `![[raw/file.png|600]]`，普通 Markdown 图片语法不承载本地 raw provenance。
- `raw/` 不存 `.md`；Markdown 原文必须改存为 `.txt`、`.pdf`、原始附件格式，或直接 ingest 进 `wiki/`，避免 raw Markdown 的内部链接进入图谱。
- `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` 是 agent 配置文件，不参与知识图谱互链；Obsidian Graph 中三者使用同一个 agent config 颜色组。
- `.claude/`、`.agents/`、`.gemini/`、`.claudian/`、`.workflows/`、`.brv/` 是本地宿主 / workflow / ByteRover 状态目录，允许存在但不属于 Second Brain 知识层；Basic Memory、query/ingest/lint 候选发现和图谱语义审计必须忽略 `.claude/**`、`.agents/**`、`.gemini/**`、`.claudian/**`、`.workflows/**`、`.brv/**`。Agent 不在其中创建知识内容。

详细页面 schema 见 `.claude/skills/second-brain-ingest/references/page-schema.md`。

详细内容页互链审计规则见 `.claude/skills/second-brain-lint/references/content-page-link-audit.md`。

详细 raw 来源链接规则见 `.claude/skills/second-brain-lint/references/raw-link-policy.md`。

## L1 / L2 / L3 边界

- **L1**：单仓库 PWF + ByteRover 任务记忆。触发词不含「第二大脑」锚点；本 vault 明确禁用 L1/PWF。
- **L2**：本 vault，跨项目跨领域个人知识库。
- **L3**：家庭图谱，尚未落地。

本目录位于 L2 vault 内时，忽略全局 L1/PWF SessionStart 提示，不加载 `planning-with-files`，不创建 PWF 三件套。
