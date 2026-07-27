# 进度日志

## 会话：2026-06-12

### 阶段 1：Codex 全局规则和本机环境基础配置
- **状态：** complete
- **开始时间：** 2026-06-12 20:53:00 +0800
- **更新时间：** 2026-06-12 21:36:42 +0800
- 执行的操作：
  - 检查 `sharing-studio` 仓库结构，确认其是 agent memory、Second Brain、GTD、heavy workflows 和 sync pipeline 的公开脚手架集合。
  - 将 `projects/agent-memory-stack/global/AGENTS.md` 安装为 `/home/kevinlasnh/.codex/AGENTS.md`。
  - 根据 Ubuntu 24.04.4 LTS 环境，将 Windows 提权和 PowerShell 编码规则改为 Linux sudo 和 UTF-8 文本规则。
  - 设置用户标识为 `kevinlasnh`。
  - 设置 planned Second Brain vault 路径为 `/home/kevinlasnh/Documents/second-brain/`。
  - 删除 Codex 全局规则中所有 Gemini/GEMINI/.gemini 相关内容，将三方同步规则改为 Claude Code + Codex 双方同步规则。
  - 检查 brv 安装，确认版本为 `byterover-cli/3.16.1 linux-x64 node-v24.13.1`。
  - 连接 brv DeepSeek provider，并切换模型为 `deepseek-v4-pro`。
  - 修复当前 Codex 会话中 `brv` 不在 PATH 的问题，创建 `~/.local/bin/brv -> ~/.brv-cli/bin/brv` symlink。
  - 确认 PWF skill 已安装在 `~/.agents/skills/planning-with-files-zh/SKILL.md` 并读取规则。
- 创建/修改的文件：
  - `/home/kevinlasnh/.codex/AGENTS.md`
  - `/home/kevinlasnh/.local/bin/brv`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

### 阶段 2：ByteRover 项目记忆初始化
- **状态：** pending
- 执行的操作：
  - 已确认 `brv status` 显示当前项目 context tree 尚未初始化。
- 创建/修改的文件：
  - 暂无。

### 阶段 3：Second Brain vault 脚手架审查
- **状态：** in_progress
- **更新时间：** 2026-06-12 22:24:50 +0800
- 执行的操作：
  - 按用户要求将清理范围限定为 `/home/kevinlasnh/Documents/second-brain/` 的脚手架、agent 配置、插件和运行时状态。
  - 未扫描或修改 `daily/`、`wiki/`、`raw/` 等内容文档。
  - 扫描 root router、`.claude/`、`.agents/`、`.gemini/`、`.claudian/`、`.obsidian/*.json`、`.obsidian/plugins/realclaudian/`、`.brv/config.json` 和 `.workflows/` 中的 Gemini/Claudian/旧 Windows 路径残留。
  - 识别出默认删除候选、默认改写候选、默认保留项和需要用户确认的历史 workflow 项。
- 创建/修改的文件：
  - 暂无 vault 文件修改。

### 阶段 3：Second Brain vault Gemini/Claudian 清理
- **状态：** complete
- **更新时间：** 2026-06-12 22:34:02 +0800
- 执行的操作：
  - 删除 `/home/kevinlasnh/Documents/second-brain/GEMINI.md`。
  - 删除 `/home/kevinlasnh/Documents/second-brain/.gemini/`。
  - 删除 `/home/kevinlasnh/Documents/second-brain/.claudian/`。
  - 删除 `/home/kevinlasnh/Documents/second-brain/.obsidian/plugins/realclaudian/`。
  - 将 root `AGENTS.md` / `CLAUDE.md` 改为 Linux vault path 与 Claude Code + Codex 双宿主规则。
  - 同步改写 `.agents/skills/**` 与 `.claude/skills/**` 中的 Gemini/Claudian/旧 Windows vault path 规则。
  - 更新 `.obsidian/graph.json`、`.obsidian/workspace.json`、`.brv/config.json` 和 `.gitignore` 的相关脚手架状态。
- 验证：
  - 活动脚手架残留扫描 `Gemini|GEMINI.md|.gemini|Claudian|realclaudian|G:\|C:\Users`：无输出。
  - `diff -qr .claude/skills .agents/skills`：无输出。
  - `CLAUDE.md` / `AGENTS.md` 去除 frontmatter 后正文 diff：无输出。
  - `.claude`、`.agents`、`.obsidian`、`.brv/config.json` JSON parse：pass。
  - 16 个 `.claude/skills` / `.agents/skills` 目录通过 `quick_validate.py`。
  - `brv status` 识别 Project 为 `/home/kevinlasnh/Documents/second-brain`。
  - 当前系统未安装 `powershell` / `pwsh`，未执行 `.ps1` hook 语法/运行验证。
- 未触碰范围：
  - `daily/`
  - `wiki/`
  - `raw/`
  - `.workflows/` 历史产物

### 阶段 3：Second Brain vault Ubuntu 运行逻辑迁移
- **状态：** in_progress
- **更新时间：** 2026-06-12 23:09:48 +0800
- 执行的操作：
  - 将 `/home/kevinlasnh/Documents/second-brain/.claude/settings.json` 的 hook shell 从 PowerShell 迁移为 `bash`，命令统一调用 `python3 "$CLAUDE_PROJECT_DIR/.claude/scripts/hook_policy.py" <policy>`。
  - 新增 `.claude/scripts/hook_policy.py`，合并承接 session-start、shell-write-policy、wiki-path-policy、wiki-write-reminder、wiki syntax、daily no-link、raw-link 等原 `.ps1` hook 逻辑。
  - 将 `second-brain-delete`、`second-brain-lint`、`second-brain-hf-backup` 的活动脚本迁移为 Python，并同步到 `.claude/skills/**` 与 `.agents/skills/**`。
  - 删除活动脚手架中的 `.ps1` 文件，保留 `.workflows/` 历史产物，不修改 `daily/`、`wiki/`、`raw/` 内容文档。
  - 修复 `.claude/skills/second-brain-vault-audit/SKILL.md` 与 `.agents/skills/second-brain-vault-audit/SKILL.md` 未同步问题。
  - 修复 `.obsidian/workspace.json` 的 `realclaudian:Open Claudian` ribbon 残留，修正 `.obsidian/graph.json` 的 wiki color group。
  - 修复 `deep_audit.py`：禁止运行时写 `.pyc`，并在 skill 镜像比较时忽略 `__pycache__` / `.pyc` 验证产物。
  - 用户级安装 `uv` / `uvx` 到 `/home/kevinlasnh/.local/bin`，用于匹配 `.claude/mcp.json` 中的 `uvx basic-memory mcp` 入口。
- 验证：
  - `python3 -m py_compile` 检查 `.claude/scripts/hook_policy.py` 与 `.claude/skills` / `.agents/skills` 下所有 `.py`：pass。
  - 16 个 `.claude/skills` / `.agents/skills` 目录通过 `quick_validate.py`：pass。
  - `.claude`、`.agents`、`.obsidian`、`.brv/config.json` JSON 解析：pass。
  - `.claude/skills` 与 `.agents/skills` 递归 diff：无差异。
  - `CLAUDE.md` / `AGENTS.md` 去除 frontmatter 后正文 diff：无差异。
  - Hook dry-run 10 个阻断/放行样例：pass。
  - 活动文档/配置残留扫描 `powershell|pwsh|.ps1|Windows|G:\|C:\Users`（排除 Python 检测代码）：无输出。
  - `find .claude .agents -type f -name '*.ps1'`：无输出。
  - `brv status`：识别 Project 为 `/home/kevinlasnh/Documents/second-brain`。
  - `deep_audit.py --skip-basic-memory`：脚手架检查通过；剩余 2 条为 `wiki/` 内容页 raw link policy violation，本轮未修改内容文档。
- 未完成 / 后续：
  - `uvx basic-memory --help` 首次依赖环境构建未完成，已终止卡住进程；需要后续单独完成 Basic Memory 下载、项目初始化与 MCP 运行验证。
  - `wiki/robot-navigation-planning/astar-pathfinding-algorithm.md` 与 `wiki/robot-navigation-slam/slam-fundamentals.md` 各有 1 条 raw 图片语义问题，属于内容层清理，不属于本轮脚手架迁移。
- 创建/修改的脚手架文件：
  - `/home/kevinlasnh/Documents/second-brain/AGENTS.md`
  - `/home/kevinlasnh/Documents/second-brain/CLAUDE.md`
  - `/home/kevinlasnh/Documents/second-brain/.claude/settings.json`
  - `/home/kevinlasnh/Documents/second-brain/.claude/scripts/hook_policy.py`
  - `/home/kevinlasnh/Documents/second-brain/.claude/skills/**`
  - `/home/kevinlasnh/Documents/second-brain/.agents/skills/**`
  - `/home/kevinlasnh/Documents/second-brain/.obsidian/graph.json`
  - `/home/kevinlasnh/Documents/second-brain/.obsidian/workspace.json`
  - `/home/kevinlasnh/.local/bin/uv`
  - `/home/kevinlasnh/.local/bin/uvx`

### 阶段 3：Second Brain 复核、proxy 配置和进度记录
- **状态：** in_progress
- **更新时间：** 2026-06-12 23:53:37 +0800
- 执行的操作：
  - 二次复核 Second Brain 核心运行逻辑和脚手架逻辑。
  - 确认 Ubuntu 基线为 Ubuntu 24.04.4 LTS、Python 3.12.3、bash 5.2、uv/uvx 0.11.21、brv 3.16.1。
  - 再次扫描活动配置/Markdown：未发现 Windows、PowerShell、Gemini、Claudian 运行入口；`.ps1/.bat/.cmd` 扫描无输出；`.claude/skills` 与 `.agents/skills` 保持镜像一致。
  - 发现并修复 `second-brain-graph-manager` 的逻辑矛盾：wiki color contract 与 `deep_audit.py` / `.obsidian/graph.json` 不一致，并且 JSON 示例有错误转义；两份镜像 skill 已同步修正。
  - 将活动脚手架文档中的 Basic Memory CLI 命令迁移为 `uvx basic-memory ...`，匹配当前 Ubuntu 上已有的 `uvx` 入口。
  - 尝试 `uv tool install basic-memory`，约 26 分钟仍未生成 `basic-memory` 命令，随后终止进程。
  - 排查 terminal proxy：确认 `verge-mihomo` 监听 `127.0.0.1:7897`，Git 全局代理已配置，但 shell env 未导出 proxy。
  - 新增 `/home/kevinlasnh/.config/proxy-env.sh`，并修改 `/home/kevinlasnh/.bashrc` 与 `/home/kevinlasnh/.profile` 进行永久加载。
  - 验证 `bash -lc` 和 `bash -ic` 都能读取 `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY`；`curl` 访问 PyPI / Astral 默认走 `127.0.0.1:7897`。
  - 在 Second Brain 创建 `daily/2026-06-12.md`，记录本轮 Ubuntu agent 脚手架恢复、Basic Memory 依赖问题和 proxy 配置状态。
- 未完成 / 后续：
  - `deep_audit.py` 尚需补 Basic Memory CLI fallback/timeout 逻辑。
  - Basic Memory CLI 依赖安装与 `uvx basic-memory status --project second-brain --json` 仍需重试。
  - Second Brain full audit、两个 wiki raw 图片语义问题、journal 后 Basic Memory closure 和 HF backup closure 仍未完成。
- 创建/修改的文件：
  - `/home/kevinlasnh/.config/proxy-env.sh`
  - `/home/kevinlasnh/.bashrc`
  - `/home/kevinlasnh/.profile`
  - `/home/kevinlasnh/Documents/second-brain/.claude/skills/second-brain-graph-manager/SKILL.md`
  - `/home/kevinlasnh/Documents/second-brain/.agents/skills/second-brain-graph-manager/SKILL.md`
  - `/home/kevinlasnh/Documents/second-brain/CLAUDE.md`
  - `/home/kevinlasnh/Documents/second-brain/AGENTS.md`
  - `/home/kevinlasnh/Documents/second-brain/.claude/skills/**`
  - `/home/kevinlasnh/Documents/second-brain/.agents/skills/**`
  - `/home/kevinlasnh/Documents/second-brain/daily/2026-06-12.md`

## 测试结果
| 测试 | 输入 | 预期结果 | 实际结果 | 状态 |
|------|------|---------|---------|------|
| Codex 全局文件加载 | `codex debug prompt-input 'ping'` | prompt input 包含更新后的 AGENTS.md | 已包含更新内容 | pass |
| Gemini 残留扫描 | `rg -i 'gemini|GEMINI.md|.gemini' ~/.codex/AGENTS.md` | 无输出 | 无输出 | pass |
| brv 版本检查 | `brv --version` | 输出 brv 版本 | `byterover-cli/3.16.1 linux-x64 node-v24.13.1` | pass |
| brv provider/model | `brv providers`; `brv model` | DeepSeek + deepseek-v4-pro | Provider DeepSeek, Model deepseek-v4-pro | pass |
| PWF skill 可见性 | 查找 `~/.agents/skills/planning-with-files-zh/SKILL.md` | 文件存在并可读 | 文件存在并已读取 | pass |

## 错误日志
| 时间戳 | 错误 | 尝试次数 | 解决方案 |
|--------|------|---------|---------|
| 2026-06-12 21:26 +0800 | `brv` 不在当前 PATH | 1 | 使用绝对路径继续检查，并创建 `~/.local/bin/brv` symlink |
| 2026-06-12 21:30 +0800 | 通过非 TTY stdin 注入 DeepSeek key 失败 | 1 | 改用关闭回显的 TTY `read` 输入 |

## 五问重启检查
| 问题 | 答案 |
|------|------|
| 我在哪里？ | 阶段 1 已完成，准备进入阶段 2 ByteRover 项目记忆初始化 |
| 我要去哪里？ | 初始化/确认 brv context tree，然后创建 Second Brain vault 脚手架 |
| 目标是什么？ | 在 Ubuntu 上恢复用户的 agent 脚手架，并让 Codex + brv + PWF 可用 |
| 我学到了什么？ | 见 findings.md |
| 我做了什么？ | 见本进度日志 |

---
*每个阶段完成后或遇到错误时更新此文件*

## 会话：2026-06-13

### 阶段 3：Second Brain Basic Memory、audit 与备份闭环
- **状态：** in_progress（本地闭环完成；HF 远端 push 被凭据阻塞）
- **更新时间：** 2026-06-13 16:35 +0800
- 执行的操作：
  - 按 PWF 恢复 `task_plan.md` / `findings.md` / `progress.md`，并用 plan 工具建立当前会话步骤。
  - 查询 ByteRover 长期记忆：`Second Brain Basic Memory Ubuntu uvx`、`agent scaffold Ubuntu migration`、`sharing-studio PWF brv setup` 均无召回。
  - 使用 Basic Memory 官方当前用法复核本地安装路径；清理 malformed `basic-memory` uv tool 环境，并通过 `uv tool install basic-memory` 成功安装 `basic-memory` / `bm` 0.22.1。
  - 注册 Basic Memory 本地 project `second-brain` 到 `/home/kevinlasnh/Documents/second-brain`，首轮 search reindex 覆盖 497 个文件，后续 status clean。
  - 修复 Second Brain vault 中 `.obsidian/workspace.json` 的 Claudian UI 残留。
  - 修复 `wiki/robot-navigation-planning/astar-pathfinding-algorithm.md` 与 `wiki/robot-navigation-slam/slam-fundamentals.md` 的 raw instructional image 语义问题。
  - 修复 `.claude/scripts/hook_policy.py` 中 raw 文件名触发 forbidden context 的误伤。
  - 更新 `.claude/skills/second-brain-lint/scripts/deep_audit.py` 和 `.agents/skills/second-brain-lint/scripts/deep_audit.py`，增加 Basic Memory fallback、timeout、clean-status 校验和 search probe。
  - 创建 `daily/2026-06-13.md` 记录本轮 Second Brain scaffold closure，并执行完整 Basic Memory journal reindex：497 entities embedded，0 skipped，0 errors；最终 status clean。
  - 运行 `deep_audit.py --vault-root .`：clean，56 checks，0 issues。
  - 执行 `second-brain-hf-backup`：本地 commit `a9bfe2c` 创建成功，但远端 push 因 Hugging Face HTTPS credential 缺失失败。
- 验证：
  - `basic-memory --version` / `bm --version`：0.22.1。
  - `basic-memory status --project second-brain --json`：clean。
  - `basic-memory tool search-notes "second brain" --project second-brain --page-size 5`：可返回结果。
  - `PYTHONDONTWRITEBYTECODE=1 python3 .claude/skills/second-brain-lint/scripts/deep_audit.py --vault-root .`：clean。
  - `.claude/skills` 与 `.agents/skills` 递归 diff：无差异。
  - `.claude` / `.agents` 无 `__pycache__` / `.pyc` 验证产物。
- 阻塞：
  - Hugging Face remote push 失败：`fatal: could not read Username for 'https://huggingface.co': No such device or address`。本机未发现 `hf` / `huggingface-cli` 登录入口、Git credential helper 或 Hugging Face token 缓存。需要用户提供/配置 HF Git 凭据后重跑 `git push hf HEAD:main` 或备份脚本。
- 创建/修改的关键文件：
  - `/home/kevinlasnh/Documents/second-brain/daily/2026-06-13.md`
  - `/home/kevinlasnh/Documents/second-brain/.claude/scripts/hook_policy.py`
  - `/home/kevinlasnh/Documents/second-brain/.claude/skills/second-brain-lint/scripts/deep_audit.py`
  - `/home/kevinlasnh/Documents/second-brain/.agents/skills/second-brain-lint/scripts/deep_audit.py`
  - `/home/kevinlasnh/Documents/second-brain/.obsidian/workspace.json`
  - `/home/kevinlasnh/Documents/second-brain/wiki/robot-navigation-planning/astar-pathfinding-algorithm.md`
  - `/home/kevinlasnh/Documents/second-brain/wiki/robot-navigation-slam/slam-fundamentals.md`
  - `/home/kevinlasnh/Documents/second-brain/.git/config`（本地 Git author identity）

### 阶段 3：Second Brain 非必要文件删除与全仓复核
- **状态：** complete（本地逻辑完整；HF 远端 push 仍被凭据阻塞）
- **更新时间：** 2026-06-13 17:31 +0800
- 执行的操作：
  - 按用户要求全面检查 `/home/kevinlasnh/Documents/second-brain` 下的非必要文件、隐藏目录、缓存、备份文件和脚手架残留。
  - 删除唯一确认无必要的文件：`/home/kevinlasnh/Documents/second-brain/.obsidian/graph.json.bak`。
  - 复核 `.claude/skills` 与 `.agents/skills` 镜像一致，Python/JSON/router/Obsidian 配置检查通过。
  - 复跑 Second Brain deep audit：56 checks，0 issues。
  - 复核 Basic Memory：status clean，search probe 可用，embeddings 498/498 up to date。
  - 按用户要求在 `sharing-studio` 更新 PWF 三件套，并在 Second Brain 追加 `daily/2026-06-13.md` 的 `17:31` 日记小节。
  - 对日记运行 no-internal-link 边界检查：未发现 wikilink 或本地 Markdown link。
  - 执行 journal closure：`uvx basic-memory status --project second-brain --json` 预检查只发现 `daily/2026-06-13.md`，随后 full reindex 完成，二次 status clean。
  - 执行 HF backup 脚本：本地 commit `b33cb78` 创建成功；远端 push 失败。
- 验证：
  - `deep_audit.py --vault-root .`：clean，56 checks，0 issues。
  - `basic-memory status --project second-brain --json`：clean。
  - `uvx basic-memory reindex --project second-brain`：498 entities embedded，496 skipped，0 errors。
  - `.claude/skills` 与 `.agents/skills` 递归 diff：无差异。
- 阻塞：
  - Hugging Face remote backup push 仍因 HTTPS credential 缺失阻塞；直接复现 `GIT_TERMINAL_PROMPT=0 git push hf HEAD:main` 的错误为 `fatal: could not read Username for 'https://huggingface.co': terminal prompts disabled`。
- 创建/修改/删除的关键文件：
  - 删除 `/home/kevinlasnh/Documents/second-brain/.obsidian/graph.json.bak`
  - 修改 `/home/kevinlasnh/Documents/second-brain/daily/2026-06-13.md`
  - 修改 `/home/kevinlasnh/Projects/sharing-studio/task_plan.md`
  - 修改 `/home/kevinlasnh/Projects/sharing-studio/findings.md`
  - 修改 `/home/kevinlasnh/Projects/sharing-studio/progress.md`

### 阶段 5：Claude Code 全局配置部署
- **状态：** complete
- **更新时间：** 2026-06-13 17:49 +0800
- 执行的操作：
  - 检查全局配置状态：`/home/kevinlasnh/.codex/AGENTS.md` 已存在，`/home/kevinlasnh/.claude/CLAUDE.md` 不存在。
  - 按全局同步规则从 Codex 全局配置创建 `/home/kevinlasnh/.claude/CLAUDE.md`。
  - 将 Claude 文件 H1 设置为 `# Claude Code Global Configuration`，保留 Codex 文件 H1 为 `# Codex Global Configuration`。
  - 保持 H1 以下所有内容完全一致。
- 验证：
  - 两个文件均存在：`/home/kevinlasnh/.claude/CLAUDE.md` 与 `/home/kevinlasnh/.codex/AGENTS.md`。
  - `diff -u <(tail -n +2 ~/.claude/CLAUDE.md) <(tail -n +2 ~/.codex/AGENTS.md)`：无输出。
  - H1 以下 sha256 一致：`4a5f902fa492adc5b73f3358a355a27b6b854b909c7dcbe2cd39fd03fb38c218`。
- 创建/修改的关键文件：
  - 创建 `/home/kevinlasnh/.claude/CLAUDE.md`
  - 修改 `/home/kevinlasnh/Projects/sharing-studio/task_plan.md`
  - 修改 `/home/kevinlasnh/Projects/sharing-studio/findings.md`
  - 修改 `/home/kevinlasnh/Projects/sharing-studio/progress.md`

### 阶段 5：PWF worktree 继承问题记录
- **状态：** pending（按用户要求留到下回改动）
- **更新时间：** 2026-06-13 18:01 +0800
- 记录的问题：
  - 当前 `sharing-studio` 的 `task_plan.md` / `findings.md` / `progress.md` 被 `.gitignore` 忽略，且未被 Git 跟踪。
  - 因此新开 git worktree 时不会自动出现这三份 PWF 文件，无法继承当前任务上下文。
  - 这与“多 worktree 并行时 PWF 三件套应随 worktree / 本地 commit 同步”的策略冲突。
- 下回任务：
  - 调整 PWF 三件套 Git 跟踪策略，让新 worktree 能继承上下文。
  - 同时配置或验证 pre-push/等价检查，阻止 `task_plan.md` / `findings.md` / `progress.md` 推送到公开远端。
  - 检查 `.gitignore` 与受保护路径策略是否一致，避免只靠 ignore 导致 worktree 上下文丢失。

### 阶段 5：全局 agent markdown 规则校验
- **状态：** in_progress
- **更新时间：** 2026-06-14 13:58 +0800
- 执行的操作：
  - 读取 `planning-with-files-zh` skill，并按恢复规则读取 `task_plan.md`、`progress.md`、`findings.md`。
  - 读取 `/home/kevinlasnh/.codex/AGENTS.md`，并验证 `/home/kevinlasnh/.claude/CLAUDE.md` 与其完全一致。
  - 使用 `brv status`、`brv query`、`brv query --help`、`brv curate --help`、`brv review pending --help`、`brv worktree --help` 校验 L3 规则与本机 ByteRover CLI 行为。
  - 联网检索 OpenAI Codex、Claude Code、ByteRover、Git、sudo 等官方文档，用于逐条校验全局 agent markdown 规则。
  - 本地检查 sudo、locale、文件编码、skill symlink、Tavily CLI、Git ignore / tracking 状态。
- 当前发现：
  - 全局 `AGENTS.md` / `CLAUDE.md` 内容一致。
  - 当前仓库 PWF 三件套已从 `.gitignore` 放开，但尚未 `git add` 进入 Git 跟踪。
  - 当前仓库根已补齐实体 `AGENTS.md` / `CLAUDE.md`，两份内容一致并被 `.gitignore` 忽略。
  - `planning-with-files-zh` 的扩展 frontmatter 对 Codex `quick_validate.py` 不完全兼容，但当前会话可正常加载该 skill。

### 阶段 5：仓库根 agent markdown 与 PWF ignore 策略修复
- **状态：** partial
- **更新时间：** 2026-06-14 14:12 +0800
- 执行的操作：
  - 创建仓库根 `AGENTS.md` / `CLAUDE.md`，H1 均为 `# Repository Agent Markdown`，正文完全一致。
  - 修改 `.gitignore`：新增 `/AGENTS.md`、`/CLAUDE.md`、`/.codex/`、`/.agents/`、`/.workflows/`、`/.obsidian/` 等忽略项；保留 `/.claude/`、`/.brv/`、`/.brv`；移除 `task_plan.md`、`findings.md`、`progress.md` 忽略项。
  - 验证 `AGENTS.md` / `CLAUDE.md` 内容一致且被 Git 忽略。
  - 验证 PWF 三件套不再被 Git 忽略，现在显示为未跟踪文件。
  - 复核 `planning-with-files-zh`：当前会话可用，但 Codex `quick_validate.py` 不接受其 `hooks` / `user-invocable` frontmatter；为避免破坏 Claude Code hook 行为，本轮不删除这些字段。
- 后续动作：
  - 执行 Git `add` / `commit` / `push`，让 `.gitignore` 与 PWF 三件套进入版本历史。
  - 如需彻底解决 PWF skill 校验问题，单独设计 Codex-safe 与 Claude-hooked 的 skill 拆分方案。

### 阶段 5：全局 agent markdown 二次逻辑复查
- **状态：** complete
- **更新时间：** 2026-06-14 14:20 +0800
- 执行的操作：
  - 重新读取 `/home/kevinlasnh/.codex/AGENTS.md`，并验证其与 `/home/kevinlasnh/.claude/CLAUDE.md` 完全一致。
  - 复查当前仓库根 `AGENTS.md` / `CLAUDE.md` 同步状态和 `.gitignore` 生效状态。
  - 复查 ByteRover 当前本机状态：`.brv/context-tree` 路径存在，`brv vc status` 未初始化。
  - 复查 sudo、locale、文本编码和当前 Git 状态。
- 当前结论：
  - 全局规则无严重阻断性逻辑错误。
  - 仓库根 agent markdown 规则已放宽：多 Git worktree 缺少 `AGENTS.md` / `CLAUDE.md` 属于允许状态，不再要求自动补齐。
  - PWF 三件套当前规则意味着应被提交并推送；如不想推远端，需要重新添加 pre-push 保护策略。

### 阶段 5：记录进度并推送 PWF 跟踪策略
- **状态：** complete
- **更新时间：** 2026-06-14 14:26 +0800
- 执行的操作：
  - 按用户要求执行“记录进度”同步。
  - 将 `task_plan.md` 中 PWF 三件套 Git 跟踪策略标记为完成。
  - 准备 stage `.gitignore`、`task_plan.md`、`progress.md`、`findings.md`。
  - 仓库根 `AGENTS.md` / `CLAUDE.md` 已被 `.gitignore` 忽略，不纳入本次提交。
  - 执行 Git `add` / `commit`，创建 commit `8859b2a`（`chore: track PWF memory files`）。
  - 首次 `git push origin master` 因 TLS 连接非正常终止失败；检查代理和 GitHub HTTPS 连通后重试成功，将 `master` 从 `d5c54bd` 推进到 `8859b2a`。

## 会话：2026-06-22

### 阶段 4：agent workflows Skill 存在性检查
- **状态：** in_progress
- **更新时间：** 2026-06-22 16:00 +0800
- 执行的操作：
  - 检查当前仓库 `projects/` 下的 Skill 结构。
  - 确认 `projects/agent-workflows/skills/heavy-research/SKILL.md` 与 `projects/agent-workflows/skills/heavy-review/SKILL.md` 存在。
  - 读取两个 Skill 的开头说明，确认触发词分别为“准备开始进行重型调研”和“准备开始进行重型审查”。
  - 搜索 `medium` / “中型”，未发现 `medium-research` 或“中型调研”独立 Skill。
  - 检查本机全局 `/home/kevinlasnh/.agents/skills/` 与 `/home/kevinlasnh/.claude/skills/`，未发现 `heavy-research` / `heavy-review` 已部署。
  - 检查运行时，当前 Ubuntu 环境未发现 `pwsh` / `powershell`，而仓库内两个 Skill 的辅助脚本仍是 `.ps1`。
- 后续：
  - 部署前需要决定：迁移 `.ps1` 脚本为 `.sh` / `.py` 并更新 Skill 文档，或先安装 PowerShell 运行时。

### 阶段 4：heavy-research / heavy-review 全局部署
- **状态：** complete
- **更新时间：** 2026-06-22 16:02 +0800
- 执行的操作：
  - 将仓库 `projects/agent-workflows/skills/heavy-research` 复制到 `/home/kevinlasnh/.agents/skills/heavy-research`。
  - 将仓库 `projects/agent-workflows/skills/heavy-review` 复制到 `/home/kevinlasnh/.agents/skills/heavy-review`。
  - 在 `/home/kevinlasnh/.claude/skills/` 下创建 `heavy-research` 和 `heavy-review` symlink，分别指向 `/home/kevinlasnh/.agents/skills/` 中的实体目录。
  - 验证全局 `.agents` 目录中的两个 Skill 与仓库源目录 `diff -qr` 无差异。
  - 更新 `task_plan.md`，将“恢复 heavy-research / heavy-review skills”标记完成。
- 后续：
  - 当前部署版本仍使用 `.ps1` 辅助脚本；Ubuntu 环境没有 `pwsh` / `powershell`，后续优化应迁移为 Linux 可执行脚本并同步更新全局 Skill 与仓库 scaffold。

### 阶段 4：heavy workflows Ubuntu/Linux 迁移与校验
- **状态：** complete
- **更新时间：** 2026-06-22 16:35 +0800
- 执行的操作：
  - 全面扫描 `projects/agent-workflows/skills/heavy-research` 与 `heavy-review` 的 `.ps1` 脚本、`SKILL.md` 调用点、hash 示例和 review reference 中的 Windows/PowerShell 假设。
  - 将 `heavy-research/scripts/new-session-dir.ps1` 迁移为 `new-session-dir.py`，将 `find-latest-session.ps1` 迁移为 `find-latest-session.py`。
  - 将 `heavy-review/scripts/find-latest-plan.ps1` 迁移为 `find-latest-plan.py`，将 `ensure-review-dir.ps1` 迁移为 `ensure-review-dir.py`。
  - 更新 heavy-research / heavy-review 主文档和 reference：脚本调用改为 `python3`，plan hash 示例改为 `sha256sum` / Python `hashlib`，源码审查路线改为 Ubuntu/Linux + bash/python3 取证语义。
  - 用 `rsync -a --delete` 将仓库源目录同步到 `/home/kevinlasnh/.agents/skills/heavy-research` 与 `/home/kevinlasnh/.agents/skills/heavy-review`；Claude Code 侧继续通过 symlink 复用。
- 验证：
  - `python3 -m py_compile` 覆盖 4 个新 Python 脚本：pass。
  - 临时目录 smoke test 覆盖 session 创建、session 恢复、deployment-plan 定位、review 目录创建：pass。
  - 全局 `/home/kevinlasnh/.agents/skills/...` 路径 smoke test：pass。
  - 仓库源目录与全局安装目录 `diff -qr`：无差异。
  - PowerShell / `.ps1` / Windows 残留扫描：无输出。
  - `skill-creator/scripts/quick_validate.py` 校验仓库源目录和全局安装目录的 `heavy-research` / `heavy-review`：4 项均 `Skill is valid!`。
- 后续：
  - 继续恢复 GTD Todoist skills、Todoist CLI/API 和 reminder-only cron。

### 阶段 4：heavy workflows 触发词扩展
- **状态：** complete
- **更新时间：** 2026-06-22 16:55 +0800
- 执行的操作：
  - 将 `heavy-research` frontmatter description 从单一触发词扩展为 `准备开始进行重型调研` 或 `准备开始进行 Heavy Research`。
  - 将 `heavy-review` frontmatter description 从单一触发词扩展为 `准备开始进行重型审查` 或 `准备开始进行 Heavy Review`。
  - 同步更新 `projects/agent-workflows/README.md` 与 `projects/agent-workflows/README.zh-CN.md` 中的触发词表。
  - 用 `rsync -a --delete` 将两个仓库源 Skill 同步到 `/home/kevinlasnh/.agents/skills/`；Claude Code 侧继续通过 symlink 复用。
- 验证：
  - 仓库源目录与全局安装目录 `diff -qr`：无差异。
  - 触发词一致性脚本：pass。
  - `skill-creator/scripts/quick_validate.py` 校验仓库源目录和全局安装目录的 `heavy-research` / `heavy-review`：4 项均 `Skill is valid!`。
  - 逻辑扫描未发现与“只响应精确触发词”相矛盾的表述；当前语义是每个 Skill 分别有两个精确触发词。

### 阶段 4：heavy workflows subagent thinking effort 对齐
- **状态：** complete
- **更新时间：** 2026-06-22 15:42 +0800
- 执行的操作：
  - 扫描 `heavy-research` 与 `heavy-review` 的所有 subagent 派发点和 prompt 模板。
  - 在 `heavy-research/SKILL.md` 的 B2 派发规则中新增 thinking effort 继承规则，并在联网、源码、记忆三个 subagent prompt 中加入“推理强度”行。
  - 在 `heavy-review/SKILL.md` 的 R2.3 派发规则中新增 thinking effort 继承规则，并在联网、源码两个 subagent prompt 中加入“推理强度”行。
  - 在 `research-loop-core.md` 和 `review-loop-core.md` 中补充同一执行约束，确保 subagent 读取 core reference 后仍能保持与 main agent 一致的推理强度。
  - 将仓库源目录同步到 `/home/kevinlasnh/.agents/skills/heavy-research` 和 `/home/kevinlasnh/.agents/skills/heavy-review`；Claude Code 侧 symlink 自动复用。
- 验证：
  - `quick_validate.py` 校验仓库源目录和全局安装目录的 `heavy-research` / `heavy-review`：4 项均 `Skill is valid!`。
  - 机械覆盖检查：Research 3 个 subagent prompt 均含“推理强度”行；Review 2 个 subagent prompt 均含“推理强度”行；两个 core reference 均含 effort 约束。
  - Linux 残留扫描 `powershell|pwsh|.ps1|Windows|C:\\|G:\\`：无输出。
  - Python 脚本语法检查使用内存 `compile()` 覆盖 4 个脚本：pass。
  - 仓库源目录与全局安装目录 `diff -qr`：无差异。
- 备注：
  - 首次语法检查生成了临时 `__pycache__`，已清理并改用内存 `compile()` 复跑，避免验证产物污染仓库。

### 阶段 4：heavy workflows 最细逻辑复查
- **状态：** complete
- **更新时间：** 2026-06-22 18:02 +0800
- 执行的操作：
  - 重新读取 `heavy-research` / `heavy-review` 的 `SKILL.md`、所有 reference 和 4 个 Python helper 脚本。
  - 复查触发词、恢复规则、subagent prompt、文件可见性闭环、空路线占位、输出契约、模板占位禁止、只读边界和 Ubuntu/Linux 运行假设。
  - 修复 `heavy-review` 源码路线的只读语法检查冲突：移除 `python3 -m py_compile` 示例，改为内存 `compile()`，避免生成 `__pycache__` / `.pyc`。
  - 修复 inline Bash 片段语法检查边界：不再建议保存临时 scratch 文件，改为 stdin / here-doc 等无持久文件方式；无法无写入解析时标记 `UNVERIFIABLE`。
  - 用 `rsync -a --delete` 将仓库 `heavy-review` 同步到 `/home/kevinlasnh/.agents/skills/heavy-review`；Claude Code 侧 symlink 自动复用。
- 验证：
  - `quick_validate.py` 校验仓库源目录和全局安装目录的 `heavy-research` / `heavy-review`：4 项均 `Skill is valid!`。
  - 结构化一致性检查：触发词、exact-trigger 描述、subagent prompt 数量、thinking effort 覆盖、core reference 覆盖、Review 源码路线内存 compile 规则均通过。
  - Linux/PowerShell 残留扫描 `powershell|pwsh|.ps1|Windows|C:\\|G:\\`：无输出。
  - Python helper 脚本内存 `compile()` 语法检查：pass。
  - 仓库源目录与全局安装目录 `diff -qr`：无差异。
  - `git diff --check`：pass。

### 阶段 4：heavy workflows 再次最细逻辑复查
- **状态：** complete
- **更新时间：** 2026-06-22 18:15 +0800
- 执行的操作：
  - 重新读取 `planning-with-files-zh` 与 `skill-creator` 规则，并按 PWF 恢复 `task_plan.md` / `findings.md` / `progress.md`。
  - 重新完整读取 `heavy-research` / `heavy-review` 的 `SKILL.md`、所有 reference 和 4 个 Python helper 脚本。
  - 检查触发词、Ubuntu/Linux 假设、subagent thinking effort 继承、恢复 / 重跑状态机、文件可见性闭环、只读 Shell 白名单、dry-run 边界和模板占位规则。
  - 修复 `heavy-review` 源码路线：将 `git status --short` 改为 `git --no-optional-locks status --short`，避免普通 status 的 index refresh 副作用与只读边界冲突。
  - 修复 `heavy-review` 源码路线：将 `bash -n <script>` / Python compile 示例中的 `<script>` 改为 `SCRIPT_PATH`，避免 shell 重定向歧义。
  - 收紧 `heavy-review` dry-run 规则，要求确认无缓存、锁文件、构建产物或外部状态写入；不确定时标记 `UNVERIFIABLE`。
  - 修复 `heavy-research` 恢复规则底部约束，使其覆盖 `_run.md` 缺失或半写时的单次恢复字段确认例外。
  - 补齐 `heavy-research` / `heavy-review` synthesis reference 与主流程的一致性，并澄清 deployment-plan 文件由阶段 D 写入。
  - 用 `rsync -a --delete` 将两个仓库源 Skill 同步到 `/home/kevinlasnh/.agents/skills/`；Claude Code 侧 symlink 自动复用。
- 验证：
  - `quick_validate.py` 校验仓库源和全局安装目录的 `heavy-research` / `heavy-review`：4 项均 `Skill is valid!`。
  - 自定义一致性检查：触发词、exact-trigger 描述、subagent prompt effort 行数、core effort 约束、Review no-optional-locks、`SCRIPT_PATH`、无 `<script>`、无 `py_compile`、dry-run cache guard、Research/Review 重跑 reference 对齐、Research 恢复例外对齐均通过。
  - 4 个 Python helper 脚本使用内存 `compile()` 语法检查：pass。
  - 仓库源目录与全局安装目录 `diff -qr`：无差异。
  - 仓库源和全局安装目录无 `__pycache__` / `.pyc`。
  - 危险残留扫描 `powershell|pwsh|.ps1|Windows|C:\\|G:\\|py_compile|<script>|git status --short`：无命中。
  - `git diff --check`：pass。
- 遇到的问题：
  - 一次 `rg` 命令字符串中包含反引号包裹的 `run_id`，shell 先尝试执行命令替换并输出 `run_id: command not found`；未影响文件，后续搜索改用单引号避免命令替换。

### 阶段 4：heavy workflows goal 自我迭代逻辑复查
- **状态：** complete
- **更新时间：** 2026-06-22 18:53 +0800
- 执行的操作：
  - 使用 goal 继续反复细粒度审查 `heavy-research` 与 `heavy-review`，直到最后一轮找不到新增逻辑问题。
  - 修复最终产物模板残留问题：在主 Skill、core reference、synthesis reference、deployment-plan 模板和 review fix 模式中补充“不得保留尖括号占位符或省略号占位”的规则。
  - 修复查询模板字面复制风险：`heavy-research` 记忆路线的 `brv query` 示例改为真实关键词占位，并要求实际执行时替换；`heavy-review` 联网反向词扫描同样要求替换真实工具/API/命令/操作动词。
  - 修复 Ubuntu 版示例残留：将 Review 联网 HyDE 示例从 `PSScriptAnalyzer` 改为 `rsync 3.2.7`。
  - 补齐 Research / Review synthesis 输入校验，使综合阶段也会拒绝带模板占位的坏报告。
  - 用 `rsync -a --delete` 将两个仓库源 Skill 同步到 `/home/kevinlasnh/.agents/skills/`；Claude Code 侧 symlink 保持指向 `.agents` 真源。
- 验证：
  - 仓库源 `heavy-research` / `heavy-review` 通过 `skill-creator/scripts/quick_validate.py`。
  - 全局安装目录 `heavy-research` / `heavy-review` 通过 `skill-creator/scripts/quick_validate.py`。
  - 自定义一致性检查覆盖触发词、exact-only guard、Linux 残留、thinking effort 继承、文件可见性 fallback、Done 信号、占位符拒绝、旧报告隔离、route_items、route_conclusion 和 inline fix hash guard，全部通过。
  - 4 个 helper 脚本通过内存 `compile()`；临时目录 smoke test 覆盖 session 创建、latest session 查找、review 目录创建和 latest plan 查找。
  - 仓库源与全局安装目录 `diff -qr` 无差异；全局 Claude Code symlink 指向 `.agents`；危险残留扫描和 `git diff --check` 均通过；无 `__pycache__` / `.pyc`。
  - 最后一轮未发现新增逻辑问题。

## 会话：2026-07-26

### 阶段 4：Heavy Research / Heavy Review 逻辑闭环再审查
- **状态：** in_progress
- **开始时间：** 2026-07-26 +0800
- 执行的操作：
  - 归一化并确认当前工作目录为 `sharing-studio` 仓库根，未命中 Second Brain Path Guard。
  - 完整读取 `planning-with-files-zh` 与 `skill-creator` 的工作规则，恢复并读取 PWF 三件套，运行 `session-catchup.py`，未报告未同步会话。
  - 确认 Git 当前位于 `master`，初始工作区 clean，跟踪 `origin/master`。
  - 建立本轮“盘点 → 逻辑审查 → 修复 → 同标准零问题复审 → 本机重新装载 → commit/push 核验”计划。
- 当前结论：
  - 2026-06-22 的历史记录只能作为线索，不能替代本轮对当前文件、安装副本、测试和远端状态的重新取证。
  - 已完整读取两个 Skill 的主文档、全部 references、四个 helper scripts 和双语 README；已确认 post-fix 复审缺失、helper symlink 逃逸、硬编码个人 Git/PWF policy、恢复字段校验不完整、证据级别校验歧义和 Claude 安装链接缺失等问题。
- 遇到的问题：
  - 首次 PWF `apply_patch` 因错误假定 `progress.md` 末尾仍有 footer 而上下文匹配失败；未产生文件变更，改用当前真实 EOF 上下文后成功追加。

### 阶段 4：Heavy Workflows 首批加固中间检查点
- **状态：** in_progress（中间检查点，尚不可视为最终可发布版本）
- **更新时间：** 2026-07-26 15:50 +0800
- 执行的操作：
  - 汇总三条独立审查路线，确认 post-fix 未复审、Research/Review provenance 缺失、session 生命周期不闭合、helper symlink 越界、plan/source 快照不稳定、证据状态误判和公共 Git/PWF policy 硬编码等问题。
  - 为 Heavy Research 增加 session identity、topic hash、phase/status、原子 active pointer、source roots/excludes、持久 attempts、summary/approval/provenance 和 deployment-plan 验证相关契约。
  - 新增 `update-session-state.py`、`emit-plan-provenance.py`、`validate-deployment-plan.py`，并加固 `new-session-dir.py`、`find-latest-session.py` 的路径与恢复规则。
  - 为 Heavy Review 引入同一次读取生成的 plan snapshot/hash、Research provenance 校验、Git-visible source snapshot，以及带批准记录、期望 hash、锁、备份和 checkpoint 的 inline fix helper。
  - 新增 `verify-plan-provenance.py`、`capture-plan.py`、`capture-source-snapshot.py`、`apply-inline-fixes.py`，并加固 `find-latest-plan.py`、`ensure-review-dir.py` 的仓库边界与 symlink 拒绝规则。
- 检查点级验证：
  - 两个 Skill 目录下 11 个 Python 脚本使用内存 `compile()`：pass，未生成 `.pyc`。
  - `quick_validate.py` 校验仓库源 `heavy-research` / `heavy-review`：2 项均 `Skill is valid!`。
  - `git diff --check`：pass。
- 未完成 / 后续：
  - Heavy Review 后半段 R2/R3/R4、全部 review references、双语 README 和 post-fix 自动完整复审契约仍需统一。
  - Research 文档一致性、严格时间戳校验、active pointer 恢复重写、provenance 字段校验和 plan validator 表格定位仍需补强。
  - 尚未补齐自动化不变量与行为 smoke tests，尚未同步本机全局 Skill；本次提交仅用于保存进度。

### 阶段 4：中间提交后全量契约复核
- **状态：** in_progress
- **更新时间：** 2026-07-26 +0800
- 执行的操作：
  - 创建并 push 中间 commit `b0ccf3b`（`wip: checkpoint heavy workflow hardening`），核验本地 HEAD 与远端 `origin/master` 哈希一致，随后继续完整目标。
  - 重新读取 Heavy Review 主文档、review framework、loop core、路线 references 与全部现有 helper；逐项对照恢复、新建、综合、用户批准和 inline fix 契约。
  - 确认七字段 checklist 与旧四字段模板、完整 `_run.md` 恢复要求与残缺新建模板、事务 helper 与旧逐次 Edit 流程之间存在直接自相矛盾。
  - 重新检查 Research session/provenance helper，确认 active pointer、phase transition、session/report metadata 和严格时间戳仍需补强。
- 下一步：
  - 统一改写 Review R2-R4 及全部 references，新增可机械验证的 review bundle/approval/post-fix 闭环。
  - 同步修复 Research helper 与契约后，补齐自动化测试并开始同标准复审循环。

### 阶段 4：Research/Review 文件真源与 post-fix 闭环重构
- **状态：** in_progress
- **更新时间：** 2026-07-26 +0800
- 执行的操作：
  - Research session helper 增加真实时间戳语义、active pointer symlink/多行/相对路径拒绝、fallback 原子修复、显式 phase transition 和完成时指针关闭。
  - Research provenance 现绑定 `_state.md`、topic hash、run schema、source roots/excludes、attempts、全部启用报告 metadata/hash、summary key gaps 和用户 approval；deployment-plan validator 改为按章节解析步骤、回滚、风险表与关键缺口。
  - Heavy Review 主 Skill 和全部 references 统一为七字段 checklist、plan/source/provenance 三重绑定、公开 Web 隐私边界、仓库 policy 驱动的 Git/PWF 判断，以及严格证据等级到 PASS/FAIL/UNVERIFIABLE 映射。
  - 新增 review run id、locator hash、bundle validator、run 准备/归档、用户决定记录、事务 inline fix 和 post-fix verified helper。
  - R3 现在持久化 `summary.md` 与精确 `fixes.json`；R4 只通过批准/hash 绑定的事务 helper 修改 plan，之后强制新 `review_run_id` 全量复审。
  - 双语 README 已补 post-fix 回环，并移除“所有 planning 文件永不进入 Git”的通用硬编码。
- 当前验证：
  - 两份 Skill `quick_validate.py`：pass。
  - 当前 18 个 Python helper 内存 `compile()`：pass。
  - `git diff --check`：pass。
- 下一步：
  - 新增自动化行为测试，先用测试暴露 helper 边界错误，再继续同标准静态/动态复审。

### 自动化测试首轮
- **状态：** in_progress
- 新增 `projects/agent-workflows/tests/test_workflow_contracts.py`，覆盖并发 session、active lifecycle、伪日期/symlink、Research provenance 篡改、plan/source snapshot 漂移、证据状态误判、事务 inline fix 与 post-fix verified。
- 首轮 `unittest`：7 项中 6 项通过；唯一错误是静态契约测试文件漏写 `import re`，触发 `NameError`，不涉及生产 helper。已补 import，准备重跑。
- 第二轮：6 项行为测试继续通过；静态测试把跨 Skill 依赖 `emit-plan-provenance.py` 错当作 Heavy Review 本地脚本，断言范围过窄。已改为同时校验 Review 本地 scripts 与明确的 Research 配套 scripts。

### 第二轮机械闭环修复与回归
- **状态：** in_progress
- **更新时间：** 2026-07-26 +0800
- 执行的操作：
  - `emit-plan-provenance.py` 现在从 web/memory/source 报告逐项提取 confidence，按 P0/P1 规则机械反推关键缺口，并要求 `summary.md key_gap_ids` 精确一致。
  - `prepare-review-run.py` 现在在归档 changes-required bundle 前校验 `_approval.md` 与当前 summary/hash/全部 actionable item 的绑定，禁止绕过用户决定直接开新 run。
  - `apply-inline-fixes.py` 在任何幂等恢复前验证真实 session 时间戳、固定 `deployment-plan.md` 文件名和真实 fix-state；同时补充 state 的 session 绑定。
  - `validate-review-run.py` 拒绝额外非法 `状态：...` 值，并要求 `_run.md` 只能出现一个 `route_items` web/source block。
  - `new-session-dir.py` 在 active pointer 原子写入失败时回滚本次创建的 state/research/session，避免留下可被 fallback 误恢复的孤儿 session。
  - 测试从 7 项扩展到 11 项，新增关键缺口反推、未记录决定、非法状态、重复 route block、伪 session 幂等路径和 active pointer 回滚覆盖。
- 验证：
  - `python3 -m unittest discover -s projects/agent-workflows/tests -v`：11/11 pass。
- 遇到的问题：
  - 新增 active pointer 回滚测试首次把测试预置的非法日期目录也纳入“新建 session”集合，导致 1 个测试断言失败；已把断言改为核对目录集合只保留预置目录和阻断指针，复跑 11/11 pass。生产 helper 未出现失败。
- 下一步：
  - 按同一标准完整静态/动态复审全部主文档、references、helper 与测试；发现问题继续修复，直至最后一轮零问题。

### 第三轮静态复审修复与会话恢复检查点
- **状态：** in_progress
- **更新时间：** 2026-07-26 +0800
- 执行的操作：
  - 完成 Research helper 的 phase/timestamp/state 恢复、父目录 symlink、active pointer 事务清理与 deployment-plan 结构校验加固。
  - 完成 Review provenance 重验证、Git-visible source snapshot、mandatory synthetic items、按小节证据映射、summary 正文覆盖、fix 来源编号、双重稳定归档、plan mode 保留、approval hash、完整 fix-state 与 `fix-history/` 加固。
  - 测试扩展至 17 项；上一轮结果为 16/17，唯一失败是测试断言文字与受控错误文案不完全一致，生产 helper 未失败；断言已收窄为稳定语义片段，等待复跑。
  - 本次接续重新归一化仓库路径，完整读取 `planning-with-files-zh` / `skill-creator`、PWF 三件套并运行 `session-catchup.py`；未发现未同步会话，当前 worktree 差异与记录一致。
- 下一步：
  - 复跑 17 项测试，随后同步 Research/Review 文档契约并继续逐 helper 静态复审与边界测试。
- 遇到的问题：
  - 接续后首次复跑仍为 16/17：断言错误地要求“不是”和“真实”连续出现，而实际受控文案为“不是当前只读 verifier 的真实输出”。已改为匹配更精确且稳定的 `不是当前只读 verifier`；生产 helper 行为符合预期。
- 验证：
  - 修正测试契约后复跑 `python3 -m unittest discover -s projects/agent-workflows/tests -v`：17/17 pass。

### 第四轮共享状态契约与证据归属加固
- **状态：** in_progress
- **更新时间：** 2026-07-26 17:53 +0800
- 执行的操作：
  - `find-latest-session.py` 拒绝绝对但非 canonical 的 active pointer；Research deployment-plan/provenance 在校验结束前执行双重稳定性复核。
  - 新增 Heavy Review 共享只读契约 `fix_state_contract.py`，由 apply、prepare 和 verified helper 统一验证 session/review ID、全部 hash、archive manifest/真实归档文件、backup、approval hash、状态时间及 post-fix 字段。
  - 明确 `prepared` 只表示事务已准备，恢复时必须幂等重跑 `apply-inline-fixes.py`，只有 `applied-awaiting-post-fix-review` 才能启动 post-fix review。
  - source snapshot 绑定 Git porcelain、HEAD、文件内容、类型与可执行位；summary 分类改为精确集合覆盖，每条 PASS/FAIL/UNVERIFIABLE 明细必须在自身状态块内具备完整证据字段。
  - inline fix 的临时候选清理不再让目录竞争遮蔽原始错误；连续多轮修复通过 `fix-history/` 保留旧事务状态。
  - 同步更新 Research/Review 主文档与 references，补充 plan 结构、provenance、source snapshot、prepared 恢复、approval hash、fix 来源编号和审计历史契约。
- 验证：
  - 测试扩展至 21 项，新增非 canonical pointer、未跟踪文件可执行位漂移、prepared 恢复、篡改 fix-state/archive binding、summary 额外分类、同小节跨状态借证和连续两轮 fix-history 覆盖。
  - `python3 -m unittest discover -s projects/agent-workflows/tests -v`：21/21 pass。
- 下一步：
  - 完成剩余 helper 与双语文档的逐文件静态复审；发现问题继续修复并补回归，直到最后一轮零问题。

### 第五轮路径、稳定性与事务语义修复
- **状态：** in_progress
- **更新时间：** 2026-07-26 +0800
- 执行的操作：
  - 修复 invalid review bundle 的 orphan 顺序：先持久化 validation error，再移动文件；任一步失败都清理说明/空目录，已移动文件由 helper 回滚。
  - Review plan/snapshot/locator helper 改为直接校验固定 lexical 普通文件与父目录，不再先跟随 symlink 后丢失原路径证据；可疑 `_run.md` 不再被 run-id generator 静默忽略。
  - provenance verifier 增加两次 Research generator 一致性和末端 live plan/snapshot bytes 复核；deployment-plan validator 前移 research 父目录检查，并在最终 provenance 复核后再次确认 plan 稳定。
  - fix-state 共享契约开始从 archived base plan 顺序重放 fixes，并对账 approval、summary、批准编号、replacement 数量与 candidate hash。
  - Review validator 使用同一次已验证报告 bytes 计算 summary 绑定，返回 `summary_sha256`，末端复核 bundle 文件、source snapshot 与 provenance；decision/verified helper 使用该 hash 并二次验证。
  - source snapshot 增加 Git index entry 绑定；clean submodule 要求 index gitlink 等于实际 HEAD 且 worktree clean，dirty/缺失 submodule 降级为 unverifiable。
  - 同步补充 source reference 与双语 README 的 snapshot / prepared 恢复契约。
- 遇到的问题：
  - 首次修改 `capture-plan.py` 条件表达式时漏写一个 `or`；读取变更片段立即发现并修复，随后 19 个 helper 内存 `compile()` 全部通过，未执行到该错误版本。
- 验证：
  - 既有完整回归 `python3 -m unittest discover -s projects/agent-workflows/tests -v`：21/21 pass（60.646 秒）。
- 下一步：
  - 为本轮新增不变量补行为测试，再继续第二次同标准静态复审。

### 第六轮回归与特殊文件边界复审
- **状态：** in_progress
- **更新时间：** 2026-07-26 +0800
- 执行的操作：
  - 按 PWF 恢复流程重新读取三件套并运行 `session-catchup.py`；未发现额外未同步上下文。
  - 19 个 Heavy Research / Heavy Review helper 通过内存 `compile()`。
  - 完整行为回归扩展至 28 项，`python3 -m unittest discover -s projects/agent-workflows/tests -v`：28/28 pass（75.740 秒）。
  - 使用隔离临时 Git 仓库验证特殊文件枚举：纯未跟踪 FIFO 不会进入 `git ls-files --others`；已跟踪普通文件被 FIFO 替换后仍进入 snapshot 路径，当前 helper 错误返回 `confirmed`。
  - 审查 `find-latest-plan.py`，确认候选选中后 state 漂移可能导致成功输出 `SESSION_STATE=None`，且单次扫描无法证明“最新候选”稳定。
  - 全 helper 静态扫描通过 pyflakes，生产脚本无直接 `Path.read_text/read_bytes`、裸 `except` 或 traceback 路径；发现 provenance verifier 的脚本参数仍存在先 `resolve()` 后丢失 symlink 证据的问题。
  - 继续复核 Research session helper，确认 fallback 会在单次扫描后直接修复 active pointer，缺少候选稳定性与写后复核。
  - 对照 apply/prepare/verified 与共享 `fix_state_contract.py` 的字段集，未发现字段缺失或 post-fix hash 漂移；发现 summary/approval/apply/post-fix/verified 时间顺序尚未机械校验。
  - 首次时间线修复补丁因错误假定测试方法末尾的精确上下文而验证失败，`apply_patch` 整体未应用、无部分文件修改；改为拆分生产代码与测试补丁。
  - 复核 validator 最外层异常收口时发现：合法但非 object 的 `provenance.json` 会在 `.get()` 处漏出 `AttributeError` traceback；开始全脚本 JSON shape 扫描。
  - 首次跨 7 个脚本的 JSON object parser 批量补丁因 `prepare-review-run.py` import context 假定错误而整体验证失败，未产生部分修改；后续改为逐文件小补丁并即时编译。
  - JSON 非 object 回归首次插入又因假定了既有断言文案而 context 失败，测试文件未修改；改用相邻方法定义边界定位插入。
  - JSON object parser 改造后 20 个 Python 文件内存 compile 通过；pyflakes 唯一报错是 `prepare-review-run.py` 遗留未使用 `json` import，已定位为机械清理项。
  - JSON shape 5 项定向回归通过；继续复核时间语义，发现 run/report/summary 之间缺少单调顺序和通用未来时间拒绝。
  - 时间线 4 项定向回归通过；隔离仓库复现 source snapshot 的反斜杠路径漏绑定：`.workflows\visible.txt` 被 Git 枚举但未进入 hash，内容变化不改变 snapshot。
  - 盘点 12 个生产 no-follow reader，确认纯 `O_RDONLY` 在普通文件竞态替换为 FIFO 时可能阻塞；准备统一加入 `O_NONBLOCK`。
  - nonblocking reader 动态测试通过；新增静态守卫误匹配 `apply-inline-fixes.py` 的 `O_CREAT | O_RDWR` 锁文件 open，导致 1 项测试失败。生产逻辑无失败，守卫改为只匹配 `O_RDONLY + O_NOFOLLOW`。
  - ID/归档并发复核发现 history broken symlink 会被 archive rename 覆盖，新 ID generator 也未把它视为占用；inline-fix lock 还缺少 fd 普通文件类型确认。
  - 全 `exists()` 与 cleanup 分支扫描发现 capture-plan snapshot 写入、ensure-review-dir mkdir 及多处 finally cleanup 仍可能漏出或遮蔽 OSError traceback；进入写入 helper 故障收口。
  - 首次定向 compile/test 命令把 workdir 设为 `tests/` 却继续使用仓库根相对路径，测试启动前触发 `FileNotFoundError`；未执行生产代码、未产生文件，后续改为从仓库根配合 `PYTHONPATH` 运行。
  - 本次 resume 的改动前全量回归在 `test_fix_state_rejects_reversed_audit_timestamps` 失败：测试把 post-fix summary 时间改到 2000 年，先触发 validator 的 evidence 时间链拒绝，因而无法到达原断言期待的 mark-helper 文案；另一个全量测试进程仍在后台运行，已按精确 PID 终止且确认无残留进程。后续将夹具改为断言稳定的不变量语义，并为写入/清理异常补独立故障注入测试。
- 下一步：
  - 已开始将 Git-visible FIFO/socket/device 等特殊节点降级为 `unverifiable`；继续为 latest-plan 双扫描稳定性补实现与回归，随后进入最终静态复审。

### 第七轮写入异常收口与最终零问题复审
- **状态：** complete
- **更新时间：** 2026-07-26 +0800
- 执行的操作：
  - 将 Git-visible 特殊节点统一降级为 `unverifiable`，保留 Linux 字面反斜杠 Git 路径，并为 12 个 no-follow reader 加入 `O_NONBLOCK`。
  - Research/Review latest discovery 使用有界双扫描；Research fallback pointer 写回后再次验证，失效时只清理自身仍匹配的 pointer。
  - 收紧 provenance script lexical symlink、fix-state 全时间链、JSON object shape、evidence 时间链、broken history symlink 和 inline-fix lock 普通文件契约。
  - 为所有写入 helper 收口 `mkdir/open/replace/subprocess` 的预期环境错误；临时文件/目录清理失败会追加到原始错误，不再从 `finally` 遮蔽主错误或输出 traceback。
  - `record-review-decision.py` 与 `archive-review-run.py` 在 `resolve()` 前拒绝 session symlink；prepare 可依据完整 history 幂等退休部分清理的 root bundle，并把 `_run.md` 最后删除以保留重试 identity。
  - history archive、prepare 与共享 fix-state 契约现在要求目录项精确等于 `manifest.json + manifest.files`，额外注入文件也视为篡改。
  - 测试从 28 项扩展到 37 项，新增特殊文件、反斜杠路径、双扫描漂移、JSON shape、时间倒序/未来时间、broken history symlink、组合写入/清理故障、只读目录、session symlink、部分归档恢复和额外 history 文件覆盖。
- 验证：
  - 最终完整回归 `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s projects/agent-workflows/tests -v`：37/37 pass（92.255 秒）。
  - 19 个生产 helper 内存 compile：pass；`pyflakes`：pass；`git diff --check`：pass。
  - 仓库源 `heavy-research` / `heavy-review` 的 `quick_validate.py`：2/2 pass。
  - 最后一轮同标准静态复审未发现新增逻辑问题：无临时文件 unguarded cleanup、直接 `Path.read_text/read_bytes`、裸 `except`、JSON shape 漏口或已知旧闭环残留。
- 遇到的问题：
  - 改动前全量测试的时间链断言期待不可达的 mark-helper 文案，实际先被更早的 evidence 时间链正确拒绝；已改为断言稳定的 `summarized_at` 不变量且明确无 traceback。
  - 一次并行收尾检查的 JavaScript 包装器因字符串转义语法错误在执行前失败；未运行 shell 命令、未修改文件，随后改用简单输出包装完成检查。
  - 首个全量测试调用因轮询方式不当留下后台进程；已按精确 PID 终止并确认无残留，后续全部长测试均使用 session id 轮询到明确 exit code。
- 清理：
  - 删除 `projects/agent-workflows/tests/__pycache__/` 与 `projects/agent-workflows/skills/heavy-review/scripts/__pycache__/` 两个测试缓存目录。
- 本机重新装载：
  - 使用 `rsync -a --delete` 将仓库 `heavy-research` / `heavy-review` 同步到 `/home/kevinlasnh/.agents/skills/`。
  - 检查确认 Claude Code 两个安装路径原先不存在且无冲突后，创建 symlink 指向对应 `.agents` 实体目录。
  - 两个源/安装目录 `diff -qr` 无差异；全局 quick_validate 2/2 pass；安装副本 19/19 helper 内存 compile；无 `__pycache__` / `.pyc`。
- 下一步：
  - 审查提交边界与敏感信息，提交、push 并核验远端 commit。
- 发布：
  - staged 边界审查确认 36 个文件全部属于 Heavy Workflows、自动化测试与 PWF；根 agent markdown / `.brv` 保持 ignored，常见凭据格式扫描 clean。
  - 创建功能提交 `e503e7c`（`feat: harden heavy workflow contracts`），并成功 push `master`。
  - `git rev-parse HEAD` 与 `git ls-remote origin refs/heads/master` 均为 `e503e7ce8cad0e3a2d6b23c3405ea0562f037999`，确认远端包含完整功能提交。
  - Heavy Research / Heavy Review 本轮优化、零问题复审、本机重新装载和功能提交/push 已完成；后续阶段 4 只剩独立的 GTD Todoist 恢复事项。

## 会话：2026-07-27

### 阶段 4：Heavy Workflows 双宿主重新部署与验证
- **状态：** complete
- **更新时间：** 2026-07-27 11:00:48 +0800
- 执行的操作：
  - 以当前仓库源为权威重新审计 `heavy-research` / `heavy-review`；确认 Codex 全局副本过期、Claude Code 两个全局 symlink 缺失。
  - 将两个 Skill 完整同步到 `/home/kevinlasnh/.agents/skills/`，并创建 `/home/kevinlasnh/.claude/skills/` 到这些实体目录的 symlink。
  - 在只读模式实际触发 Codex 的 `准备开始进行 Heavy Research`，确认它读取当前新安装的 `SKILL.md`、进入阶段 A、要求澄清和写入权限，未创建 `.workflows/` 或执行调研。
  - 用 Claude Code 正常 TTY 入口确认 `/heavy-research` Slash Skill 被识别；用于自动化的非交互 Slash 调用存在 CLI 行为不稳定，因此已在无项目文件的临时目录中受限测试并清理，未将其视为安装内容缺失。
- 验证：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s projects/agent-workflows/tests -v`：37/37 pass（62.101 秒）。
  - 源目录与安装目录 `quick_validate.py`：4/4 `Skill is valid!`。
  - 源目录与 Codex 安装目录 `diff -qr`：无差异；Claude Code 两个 symlink 均解析到对应 Codex 实体目录。
  - 安装副本 19 个 helper 内存编译：pass；无 `__pycache__` / `.pyc`；`git diff --check`：pass。
  - Codex 模型可见 Skill 清单已列出两个 Skill；`tvly --status`：authenticated。
- 运行时说明：
  - 当前机器没有 `brv` CLI；memory 维度按 Skill 的既有降级契约跳过 ByteRover 查询、保留 `findings.md` 读取，不阻断主流程。
  - 已删除临时 Claude Code 探针目录，且按精确 PID 终止测试会话后确认没有残留 Claude 进程。
  - 首次 Git commit 因当前仓库和全局均缺少作者身份被拒绝，未生成提交；核对历史五个 commit 后仅在本仓设置既有的 `kevinlasnh <kevinlasnh@users.noreply.github.com>` 身份，准备重试。
