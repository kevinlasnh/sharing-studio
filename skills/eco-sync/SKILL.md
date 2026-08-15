---
name: eco-sync
description: kevin-AI-studio 仓库级 skill，双向同步个人 AI 使用生态（全局 agent markdown 与全局 skills）与仓库脱敏副本。只在 kevin-AI-studio 仓库目录内可用；当用户在该仓库中说"同步 AI 生态"、"同步生态"、"eco sync"、"生态同步"或需要对比设备与仓库的生态副本差异时使用。支持 status（只读对比）、push（设备→仓库）、pull（仓库→设备），自动完成脱敏占位符渲染、三路冲突检测、secrets 安全扫描和 Git 提交推送。
---

# eco-sync（仓库级 skill）

个人 AI 使用生态双向同步 skill：只在 **kevin-AI-studio 仓库目录内**可用，把设备上的全局 agent 规则与全局 skills 和仓库脱敏副本做双向同步。脚本会验证当前目录确实位于 kevin-AI-studio 仓库内，其他仓库或普通目录一律拒绝执行。

## 部署位置

本 skill 是仓库级 skill，运行时实体放在仓库内（不进入 Git，由 `.gitignore` 的 `/.agents/`、`/.claude/` 规则忽略），权威源在仓库 `skills/eco-sync/`：

```text
kevin-AI-studio/
├── skills/eco-sync/            # 权威源（Git 跟踪，随仓库分发）
├── .agents/skills/eco-sync/    # Codex 仓库级运行时副本（未跟踪）
└── .claude/skills/eco-sync/    # Claude Code 仓库级运行时副本（未跟踪）
```

新设备 clone 后需部署一次（两份实体副本，内容与权威源一致）：

```bash
cp -a skills/eco-sync .agents/skills/
cp -a skills/eco-sync .claude/skills/
```

## 生态范围

| 设备端 | 仓库端 | 处理 |
|---|---|---|
| `~/.claude/CLAUDE.md` | `global/CLAUDE.md` | 占位符渲染（本机值 ↔ `<second-brain-path>` / `<your-username>`） |
| `~/.codex/AGENTS.md` | `global/AGENTS.md` | 同上 |
| `~/.dsh/AGENTS.md` | `global/AGENTS.dsh.md` | 同上 |
| `~/.agents/skills/<name>/` | `skills/<name>/` | 逐文件 hash 对比与复制，忽略 `__pycache__` / `*.pyc` |
| `~/.claude/skills/` symlink | 不入库 | pull 后校验 symlink 完整性 |

## 用法（在仓库目录内执行）

```bash
python3 .agents/skills/eco-sync/scripts/sync.py status
python3 .agents/skills/eco-sync/scripts/sync.py push [--yes] [--force local|repo] [--prune]
python3 .agents/skills/eco-sync/scripts/sync.py pull [--yes] [--force local|repo] [--prune]
```

- 默认 dry-run：只输出变更计划；加 `--yes` 才执行。
- push 流程：`git pull --ff-only` → 三路对比 → 变更计划 →（`--yes`）写仓库副本 → 安全扫描 → commit → push。
- pull 流程：`git pull --ff-only` → 渲染镜像 → 三路对比 →（`--yes`）写设备端 → 校验 symlink。
- 冲突（同一文件设备与仓库都改过）：默认报告并跳过；`--force local` 以设备为准，`--force repo` 以仓库为准。
- 删除语义：默认只增改不删；`--prune` 允许 push 方向删除"仓库中已不存在于设备的 skill"，或 pull 方向删除"设备中仓库已不存在的 skill"。

## Agent 使用指引

1. 用户在本仓库内要求同步生态时，先跑 `status` 看差异。
2. 有差异时向用户展示变更计划，确认后带 `--yes` 执行 push 或 pull。
3. 出现 CONFLICT 时不要自动选择方向，把冲突文件清单给用户，由用户指定 `--force local|repo` 或手动处理。
4. 安全扫描失败时立即停止同步，报告命中文件，绝不把本机值写进仓库。
