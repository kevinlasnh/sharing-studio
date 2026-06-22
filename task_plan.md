# 任务计划：Ubuntu agent 脚手架恢复

## 目标
在新 Ubuntu 系统上恢复并微调个人 agent 脚手架，使 Codex、brv、PWF 和后续 Second Brain/GTD 流程能按当前系统运行。

## 当前阶段
阶段 3

## 各阶段

### 阶段 1：Codex 全局规则和本机环境基础配置
- [x] 安装 Codex 全局 `AGENTS.md`
- [x] 将 Windows 专属规则改为 Ubuntu/Linux 规则
- [x] 设置用户名为 `kevinlasnh`
- [x] 设置 planned Second Brain vault 路径为 `/home/kevinlasnh/Documents/second-brain/`
- [x] 删除 Gemini 相关全局规则，仅保留 Claude Code 和 Codex
- [x] 配置 brv 使用 DeepSeek provider 和 `deepseek-v4-pro`
- [x] 修复当前会话中 `brv` 不在 PATH 的问题
- [x] 确认 PWF skill 已安装并可读取
- **状态：** complete

### 阶段 2：ByteRover 项目记忆初始化
- [ ] 决定是否在 `sharing-studio` 当前仓库初始化 `.brv/context-tree/`
- [ ] 确认 brv 是否仅本地使用，还是需要 ByteRover cloud login/push/pull
- [ ] 运行 brv 本地初始化和状态验证
- [ ] 明确 `.brv/` 与 `.brv` 的 Git ignore / push protection 边界
- **状态：** pending

### 阶段 3：Second Brain vault 脚手架创建
- [x] 确认 `/home/kevinlasnh/Documents/second-brain/` 已存在并包含 vault scaffold
- [ ] 从 `projects/second-brain-scaffold/` 复制 Claude/Codex 相关 router、skills、hooks 和 Obsidian 配置
- [x] 去除或跳过 Gemini 相关 vault 文件
- [x] 清理 Second Brain vault 中 Gemini / Claudian 脚手架残留（先审查讨论，确认后执行）
- [x] 将活动 Claude hooks 从 PowerShell `.ps1` 迁移为 Ubuntu `python3` 入口
- [x] 将 delete / lint / HF backup 等活动 skill 脚本从 PowerShell `.ps1` 迁移为 Python `.py`
- [x] 同步 `.claude/skills` 与 `.agents/skills`，并通过 16 个 skill 的 `quick_validate.py`
- [x] 为 terminal 永久配置本机 proxy env，覆盖 `curl`、`uv`、Python、npm 等不读取 Git proxy 的 CLI
- [x] 配置 Basic Memory / MCP（`basic-memory` / `bm` 0.22.1 已通过 `uv tool install basic-memory` 安装；project `second-brain` 已注册；status clean；CLI search probe 可用）
- [x] 运行脚手架级 vault audit（含 Basic Memory status/search probe；deep audit clean，56 checks，0 issues）
- [x] 写入 Second Brain 日记并完成 Basic Memory full reindex closure（497 entities embedded，0 skipped，0 errors）
- [x] 删除 Second Brain 中确认无必要的隐藏备份文件 `.obsidian/graph.json.bak`
- [x] 复核 Second Brain 全仓隐藏目录、缓存、脚手架和运行逻辑：deep audit clean，56 checks，0 issues；Basic Memory clean；`.claude/skills` 与 `.agents/skills` 镜像一致
- [ ] 完成 Hugging Face remote backup push（本地 commit `a9bfe2c`、`b33cb78` 已创建；push 被 HF HTTPS credential 缺失阻塞）
- **状态：** in_progress

### 阶段 4：GTD Todoist 和 agent workflows 恢复
- [x] 恢复 heavy-research / heavy-review skills
- [x] 将 heavy-research / heavy-review 从 Windows PowerShell 脚本迁移为 Ubuntu/Linux Python 脚本
- [x] 同步 Linux 版 heavy workflows 到全局 `~/.agents/skills/`，Claude Code 侧通过 symlink 复用
- [x] 使用 skill-creator `quick_validate.py` 校验 heavy-research / heavy-review 仓库源目录和全局安装目录
- [x] 让 heavy-research / heavy-review 派发 subagent 时继承 main agent thinking effort，并同步到全局 Skill
- [x] 复查 heavy-research / heavy-review 逻辑边界，修复 heavy-review 源码路线只读语法检查冲突
- [ ] 恢复 GTD Todoist skills
- [ ] 检查 Todoist CLI/API 和 reminder-only cron
- [ ] 运行 health check
- **状态：** pending

### 阶段 5：收口和同步策略
- [x] 创建并部署 `~/.claude/CLAUDE.md`，与 `~/.codex/AGENTS.md` 按全局同步规则保持 H1 以下一致
- [x] 调整 PWF 三件套 Git 跟踪策略：已从 `.gitignore` 放开 `task_plan.md` / `findings.md` / `progress.md`，本轮执行 `git add` / `commit` / `push`
- [ ] 决定是否同步更新公开 `sharing-studio` scaffold
- [ ] 检查 secret/path/personal data 边界
- **状态：** pending

## 关键问题
1. 是否现在就初始化当前仓库的 `.brv/context-tree/`？
2. Claude Code 全局文件是否需要部署？已部署 `~/.claude/CLAUDE.md`，H1 以下与 Codex 全局规则一致。
3. Second Brain vault 已创建并完成本地 Basic Memory / audit 闭环；HF 远端备份仍等待凭据。
4. PWF 三件套已从 `.gitignore` 放开，但尚未 `git add` 进入 Git 跟踪；新 worktree 继承需要后续完成 add/commit，并确认远端 push 策略。

## 已做决策
| 决策 | 理由 |
|------|------|
| 先只配置 Codex 全局 `AGENTS.md` | 当前主要先恢复 Codex 工作环境 |
| 全局规则只保留 Claude Code 和 Codex，删除 Gemini | 用户明确不再使用 Gemini 作为 agent |
| planned Second Brain 路径设为 `/home/kevinlasnh/Documents/second-brain/` | 用户指定该路径，但目录尚未创建 |
| brv provider 使用 DeepSeek，模型使用 `deepseek-v4-pro` | 用户提供 DeepSeek API key 并指定 DeepSeek v4 pro |
| 使用 `~/.local/bin/brv` symlink 修复当前 PATH | `~/.brv-cli/bin` 已写入 shell profile，但当前 Codex 会话没有继承新 PATH |
| 部署 `~/.claude/CLAUDE.md` 并与 `~/.codex/AGENTS.md` 同步 | 用户要求按全局同步规则部署 Claude Code 全局配置；H1 根据工具差异化，H1 以下保持一致 |

## 遇到的错误
| 错误 | 尝试次数 | 解决方案 |
|------|---------|---------|
| `brv` 不在当前 PATH | 1 | 创建 `~/.local/bin/brv -> ~/.brv-cli/bin/brv` symlink |
| `brv providers connect deepseek` 不支持隐藏交互输入 key | 1 | 使用关闭回显的 TTY `read` 注入 key，避免命令文本和输出包含 key |
| PWF 未出现在当前 Codex 系统技能列表 | 1 | 通过 filesystem 确认 `~/.agents/skills/planning-with-files-zh/SKILL.md` 已安装并读取规则 |
| `uvx basic-memory --help` 首次依赖环境构建长时间无输出 | 1 | 已确认 `uv` / `uvx` 安装成功；终止卡住进程，将 Basic Memory 依赖下载作为后续单独收口项 |
| `uv tool install basic-memory` 运行超过 20 分钟仍未生成 CLI | 1 | 终止安装；确认终端未导出 proxy env，已新增永久 proxy 配置后再单独重试 |
| `uv tool list` 显示 malformed `basic-memory` 环境 | 1 | 运行 `uv tool uninstall basic-memory` 清理 dangling environment，再重新 `uv tool install basic-memory` 成功 |
| `second-brain-hf-backup` 首次 commit 失败：Git author identity unknown | 1 | 在 Second Brain vault 本地设置 `user.name=kevinlasnh`、`user.email=kevinlasnh@users.noreply.github.com` 后重跑 |
| `git push hf HEAD:main` 失败：HF HTTPS credential 缺失 | 1 | 本地 commit 已创建且工作区 clean；需要用户完成 Hugging Face Git 凭据登录后重跑 push |

## 备注
- 不记录任何 API key。
- 当前仓库 `task_plan.md` / `progress.md` / `findings.md` 已按新规则从 `.gitignore` 放开，应通过 Git 跟踪以支持 worktree 上下文继承；是否推送远端按当前全局 Git 策略执行。
