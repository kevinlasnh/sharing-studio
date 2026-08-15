<h1 align="center">kevin-AI-studio</h1>

<p align="center">
  <strong>个人 AI 使用生态：全局 agent markdown 脱敏镜像与全局 agent skills 权威副本。</strong>
</p>

<p align="center">
  <img alt="Personal AI ecosystem" src="https://img.shields.io/badge/personal-ai--ecosystem-0f766e?style=for-the-badge">
  <img alt="Agent skills" src="https://img.shields.io/badge/agent-skills-2563eb?style=for-the-badge">
  <img alt="Privacy first" src="https://img.shields.io/badge/privacy-first-7c3aed?style=for-the-badge">
</p>

<!-- README-I18N:START -->
<p align="center">
  <a href="./README.md">English</a> | <strong>简体中文</strong>
</p>
<!-- README-I18N:END -->

> [!NOTE]
> 这个仓库只发布可复用规则与技能。本机用户名、本机路径、凭据和私人内容不会进入跟踪文件。全局规则镜像保留 `<second-brain-path>` / `<your-username>` 占位符。

## 收录内容

| 目录 | 内容 |
| :--- | :--- |
| [`global/`](./global/) | 我的全局 agent 规则文件 `CLAUDE.md`（Claude Code）、`AGENTS.md`（Codex）、`AGENTS.dsh.md`（DeepSeek Harness）的脱敏镜像。三份文件逐字节一致，共用 H1 `# Global Agent Markdown`。 |
| [`skills/`](./skills/) | 我全部全局 agent skills 的权威副本。全局 skill 的任何本地改动都必须同步到这里。 |

## Skills 清单

| Skill | 用途 |
| :--- | :--- |
| [`baoyu-format-markdown`](./skills/baoyu-format-markdown/) | 把纯文本或 Markdown 格式化为带 frontmatter、标题、列表和代码块的结构化文章。 |
| [`brv-curate`](./skills/brv-curate/) | 把 PWF 任务知识沉淀到 ByteRover 长期仓库记忆（L2 → L3）。 |
| [`brv-query`](./skills/brv-query/) | 通过只读 `brv query` 接口查询 ByteRover 长期仓库记忆。 |
| [`find-skills`](./skills/find-skills/) | 发现并安装社区 agent skills。 |
| [`heavy-research`](./skills/heavy-research/) | 触发词门控的重型调研，产出带文件证据契约的部署计划。 |
| [`heavy-review`](./skills/heavy-review/) | 触发词门控的重型审查，以 provenance 快照验证部署计划。 |
| [`obsidian-markdown`](./skills/obsidian-markdown/) | 创建和编辑带 wikilinks、embeds、callouts、properties 的 Obsidian Flavored Markdown。 |
| [`planning-with-files-zh`](./skills/planning-with-files-zh/) | Manus 风格文件规划，持久化 `task_plan.md` / `findings.md` / `progress.md` 三件套。 |
| [`skill-creator`](./skills/skill-creator/) | 创建、修改和评测 agent skills（Apache-2.0，基于上游 skill-creator）。 |
| [`tavily-search`](./skills/tavily-search/) | 经 Tavily CLI 做 LLM 优化的 Web 搜索；只作为宿主内置 Web Search 的获批 fallback。 |
| [`eco-sync`](./skills/eco-sync/) | **仓库级 skill。** 双向同步 AI 生态（全局规则 + 全局 skills）与本仓库脱敏副本，只在本仓库内可运行。 |

## 仓库结构

```text
kevin-AI-studio/
├── global/
│   ├── AGENTS.md          # 全局 Codex 规则脱敏镜像
│   ├── AGENTS.dsh.md      # 全局 DSH 规则脱敏镜像
│   └── CLAUDE.md          # 全局 Claude Code 规则脱敏镜像
├── skills/                # 全部全局 skills 权威副本
│   ├── baoyu-format-markdown/
│   ├── brv-curate/
│   ├── brv-query/
│   ├── find-skills/
│   ├── heavy-research/
│   ├── heavy-review/
│   ├── obsidian-markdown/
│   ├── planning-with-files-zh/
│   ├── skill-creator/
│   ├── tavily-search/
│   └── eco-sync/           # 仓库级同步 skill（权威源）
├── AGENTS.md              # 仓库规则（已跟踪，公开安全）
├── CLAUDE.md              # 仓库规则（与 AGENTS.md 一致）
├── task_plan.md           # PWF 任务记忆（已跟踪）
├── progress.md            # PWF 会话日志（已跟踪）
├── findings.md            # PWF 发现记录（已跟踪）
├── README.md
├── README.zh-CN.md
└── LICENSE
```

## 同步模型

本机真源 → 脱敏镜像：

1. 全局 skill 本地有改动 → 更新 `skills/` 下对应副本 → commit。
2. 全局规则文件本地有改动 → 同步改 `global/` 下三份镜像（保持逐字节一致）→ commit。
3. 回装机器的过程手动进行：把 `skills/` 实体复制到本机全局 skills 目录（Claude Code 侧用 symlink 复用），把 `global/` 镜像替换两个占位符后渲染为本机 `CLAUDE.md` / `AGENTS.md`。

### eco-sync（仓库级 skill）

`skills/eco-sync/` 自动化上述同步流程，但刻意只在本仓库内运行。运行时实体位于 `.agents/skills/eco-sync/` 与 `.claude/skills/eco-sync/`（未跟踪、两份内容一致）。新设备 clone 后部署一次：

```bash
cp -a skills/eco-sync .agents/skills/
cp -a skills/eco-sync .claude/skills/
```

## 发布边界

跟踪文件必须保持不含：

```text
密钥 / API key              （.env、.env.*、*.key、*.pem）
本机用户名                  （以 <your-username> 占位）
本机专属路径                （以 <second-brain-path> 占位）
账号 ID / 私有 IP / 个人内容
```

发布前应扫描密钥、真实本机路径、账号 ID 和私有 IP。
