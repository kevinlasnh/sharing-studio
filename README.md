# Agent 三层记忆架构

一套给 AI coding agent 使用的记忆系统脚手架，覆盖 Claude Code、Codex、Gemini CLI 与 Obsidian Second Brain。仓库只包含可复用配置、规则、skills、hooks 和 Obsidian 稳定设置，不包含个人知识库内容。

## 这是什么

这套架构把 agent 记忆拆成三层：

| 层 | 作用域 | 核心工具 | 用途 |
|---|---|---|---|
| L1 | 单个 git 仓库 | planning-with-files + ByteRover | 当前任务进度、项目决策、长期仓库知识 |
| L2 | 个人 Second Brain vault | Obsidian + Basic Memory + local skills | 跨项目个人知识库的 ingest / query / lint / journal |
| L3 | 家庭共享图谱 | 未落地 | 多成员共享知识层 |

当前仓库公开的是 L1 与 L2 的脱敏实现。L2 只开源脚手架，不上传真实 `index.md`、`wiki/`、`daily/`、`raw/` 内容。

## 仓库结构

```text
.
├── L1-global-CLAUDE.md          # L1 全局配置脱敏副本，兼容旧入口
├── L2-vault-CLAUDE.md           # L2 vault router 脱敏副本，兼容旧入口
├── global/
│   ├── CLAUDE.md                # Claude Code 全局配置模板
│   ├── AGENTS.md                # Codex 全局配置模板
│   ├── GEMINI.md                # Gemini CLI 全局配置模板
│   └── claude-settings.example.json
├── vault-scaffold/
│   ├── CLAUDE.md                # L2 vault router 模板
│   ├── AGENTS.md                # Codex router 模板
│   ├── .claude/
│   │   ├── settings.json        # L2 hooks
│   │   ├── scripts/             # PowerShell 硬防线
│   │   └── skills/              # second-brain-* 本地 skills
│   └── .obsidian/               # 可公开 Obsidian 稳定配置与 CSS snippets
└── mcp/
    └── basic-memory-mcp.example.json
```

## 不包含什么

以下内容有意不进仓库：

- 真实 Second Brain 的 `index.md`
- 真实 `wiki/` 内容页、域索引、笔记正文
- 真实 `daily/` 日记
- 真实 `raw/` 原始素材和附件
- `.obsidian/workspace*.json`
- `.claude/settings.local.json`
- 任何真实 token、provider env、API key、本机绝对路径

## 快速使用

### L1：全局 agent 记忆

把 `global/` 里的模板放到对应工具配置目录：

```powershell
Copy-Item .\global\CLAUDE.md $HOME\.claude\CLAUDE.md
Copy-Item .\global\AGENTS.md $HOME\.codex\AGENTS.md
Copy-Item .\global\GEMINI.md $HOME\.gemini\GEMINI.md
```

按需参考 `global/claude-settings.example.json` 配置 Claude Code 的 SessionStart hook 与 plugin marketplace。不要提交真实 provider token。

### L2：Second Brain 脚手架

把 `vault-scaffold/` 中的脚手架复制到你的 Obsidian vault 根目录：

```powershell
Copy-Item .\vault-scaffold\CLAUDE.md <vault-path>\CLAUDE.md
Copy-Item .\vault-scaffold\AGENTS.md <vault-path>\AGENTS.md
Copy-Item .\vault-scaffold\.claude <vault-path>\.claude -Recurse
Copy-Item .\vault-scaffold\.obsidian <vault-path>\.obsidian -Recurse
```

然后配置 Basic Memory：

```powershell
basic-memory project add second-brain "<vault-path>" --default --local
```

MCP 示例见 `mcp/basic-memory-mcp.example.json`。

## L2 脚手架内容

`vault-scaffold/.claude/skills/` 包含 6 个本地 skills：

| Skill | 用途 |
|---|---|
| `second-brain-ingest` | 将粘贴文本、URL、文件、讨论上下文整理进 wiki |
| `second-brain-query` | 只读查询已有知识 |
| `second-brain-lint` | 健康检查、死链、frontmatter、索引、raw 边界、语义互链审计 |
| `second-brain-journal` | 写入 `daily/YYYY-MM-DD.md`，且不产生 Obsidian 图谱边 |
| `second-brain-graph-manager` | 维护 Obsidian graph color groups 与图片显示 snippet |
| `second-brain-vault-audit` | 外部健康度检查：router、skills、hooks、MCP、Obsidian、Basic Memory |

`vault-scaffold/.claude/scripts/` 是确定性防线，负责阻止废弃路径、wiki Markdown 确定性违规、daily 内部链接、raw 弱引用等问题。

## 关键设计

- L1 与 L2 用触发词和路径守卫隔离，避免在 vault 中误创建 `task_plan.md` / `progress.md` / `findings.md`。
- L1 的短期记忆由 PWF 三件套承担，长期仓库知识由 ByteRover 承担。
- L2 的写入动作必须先 search-before-write，再按 domain-routing preflight 让用户确认。
- L2 的 daily 不参与知识图谱，禁止 `[[wikilink]]` 和本地 Markdown link。
- Raw 只作为来源、证据或教学图片素材，不作为导航页或知识图谱概念节点。

## License

[CC-BY-SA 4.0](./LICENSE)。可以使用、修改、分发；请署名并以相同协议共享衍生作品。
