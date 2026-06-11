# second-brain-scaffold

一个 Obsidian + Basic Memory vault 脚手架，用于 AI 辅助 ingest、query、lint、graph maintenance 和 daily journaling。

<p>
  <img alt="Obsidian" src="https://img.shields.io/badge/Obsidian-vault-7c3aed?style=flat-square">
  <img alt="Basic Memory" src="https://img.shields.io/badge/Basic%20Memory-MCP-0f766e?style=flat-square">
  <img alt="No real notes" src="https://img.shields.io/badge/content-scaffold--only-2563eb?style=flat-square">
</p>

<!-- README-I18N:START -->
<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong>
</p>
<!-- README-I18N:END -->

> [!WARNING]
> 这个目录是脚手架，不是 vault 备份。它刻意不包含真实 `wiki/`、`daily/`、`raw/` 或个人 `index.md` 内容。

## 解决什么问题

长期运行的个人知识系统需要比“一堆笔记文件夹”更强的边界。这个脚手架会分离原始证据、持久 wiki 页面、daily 日志、图谱配置、删除流程、备份闭环和 agent 写入权限。

## 包含内容

```text
second-brain-scaffold/
├── CLAUDE.md                       # L2 vault router for Claude Code
├── AGENTS.md                       # L2 vault router for Codex
├── GEMINI.md                       # L2 vault router for Gemini CLI
├── .claude/
│   ├── settings.json               # vault-level hooks
│   ├── scripts/                    # deterministic PowerShell guardrails
│   └── skills/                     # Claude Code local Second Brain skills
├── .agents/
│   └── skills/                     # Codex / cross-agent local skill mirror
├── .gemini/
│   └── skills/                     # Gemini CLI local skill mirror
├── .obsidian/                      # portable Obsidian configuration
└── mcp/
    └── basic-memory-mcp.example.json
```

## Skill 清单

| Skill | 目的 |
| :--- | :--- |
| `second-brain-ingest` | 在 search-before-write 后，将来源材料路由到持久 `wiki/` 页面。 |
| `second-brain-delete` | 对显式 wiki、raw、daily、domain 或旧 workflow 目标执行 plan、确认、apply 和 validate。 |
| `second-brain-query` | 对结构化 vault 执行只读查询。 |
| `second-brain-lint` | 审计链接、frontmatter、index 覆盖、raw 边界和 graph health。 |
| `second-brain-journal` | 写入概念图谱之外的 `daily/YYYY-MM-DD.md` 条目，并收口 Basic Memory sync 与备份 handoff。 |
| `second-brain-hf-backup` | 在 journal closure 后，将完整私有 vault Git snapshot 推到配置好的 Hugging Face dataset remote。 |
| `second-brain-graph-manager` | 维护 graph color groups 和 image-display CSS。 |
| `second-brain-vault-audit` | 检查 router、hooks、skills、MCP、Obsidian 和 Basic Memory wiring。 |

## 快速开始

1. 在你偏好的本地或同步路径创建新的 Obsidian vault。
2. 将 `CLAUDE.md`、`AGENTS.md`、`GEMINI.md`、`.claude/`、`.agents/`、`.gemini/` 和 `.obsidian/` 复制到 vault root。
3. 为该 vault 注册 Basic Memory：

   ```powershell
   basic-memory project add second-brain "<vault-path>" --default --local
   ```

4. 将 [`mcp/basic-memory-mcp.example.json`](./mcp/basic-memory-mcp.example.json) 中的 MCP 注册片段加入你的 agent 运行时。
5. 如果使用 Hugging Face 备份 workflow，将 scaffold 中的 `<hf-private-dataset-url>` 替换为你的私有 dataset remote。
6. 先在 Obsidian 中打开一次 vault，让本地 plugin settings 初始化。
7. 在写入真实内容前运行 `second-brain-vault-audit`。

## 护栏

- `wiki-path-policy.ps1` 阻止 legacy 或不支持的 wiki paths。
- `shell-write-policy.ps1` 阻止绕过 vault 文件策略的 shell 写入。
- `wiki-prewrite-syntax-check.ps1` 和 `wiki-syntax-check.ps1` 强制 Obsidian Markdown contracts。
- `wiki-write-reminder.ps1` 提醒 agent 写入前先搜索，并完成 domain routing。
- `daily-no-link-policy.ps1` 让 daily notes 留在 concept graph 之外。
- `raw-link-policy.ps1` 让 source material 作为证据，而不是导航入口。

## 核心规则

- `wiki/` 是持久知识图谱。
- `raw/` 只存放证据和导入来源材料。
- `daily/` 存放时间线笔记，不应链接进概念图谱。
- 创建或更新知识页面前必须执行 search-before-write。
- 高风险结构修改走提案和确认门：新 domains、renames、moves、deletes 和 merges。
- Journal closure 负责最终 Basic Memory reindex checkpoint，并可 handoff 到私有 Hugging Face backup。

## 依赖

- [Obsidian](https://obsidian.md/) 1.12+。
- [Basic Memory](https://github.com/basicmachines-co/basic-memory)，推荐用于 MCP 支撑的索引。
- 能加载 vault 级 router 和本地 skills 的 agent 运行时。
- 可选 Obsidian 社区插件 `realclaudian` / Claudian，用于内嵌 agent tabs；本仓不包含插件包和运行时状态。
- 可选云同步，例如 Obsidian Sync、iCloud、Google Drive 或其他 provider。

## 隐私边界

不要发布：

- `wiki/`、`daily/` 或 `raw/` 中的真实笔记。
- Obsidian `workspace*.json` 文件。
- Basic Memory databases 或 project state。
- 私有 backup remote URL。
- 真实 vault paths、account identifiers、API keys 或 local machine paths。
