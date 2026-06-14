# 发现与决策

## 需求
- 在新 Ubuntu 系统上逐步恢复个人 agent 脚手架。
- 当前优先 Codex，不急于启用 Claude Code。
- 不再使用 Gemini 作为 agent。
- brv 已下载，需要配置 DeepSeek provider 和 `deepseek-v4-pro`。
- PWF 已安装，需要确认当前 Codex 是否可见，并记录进度。

## 研究发现
- `sharing-studio` 是公开脚手架仓库，根 README 明确只发布可复用结构，不发布私人数据。
- Codex 全局规则路径为 `/home/kevinlasnh/.codex/AGENTS.md`。
- 当前系统是 Ubuntu 24.04.4 LTS on Lenovo ThinkPad X13 Gen 4。
- 当前 planned Second Brain vault 路径是 `/home/kevinlasnh/Documents/second-brain/`，目录尚不存在。
- `brv` 安装在 `/home/kevinlasnh/.brv-cli/bin/brv`，版本为 `byterover-cli/3.16.1 linux-x64 node-v24.13.1`。
- `brv` 已连接 DeepSeek provider，当前模型为 `deepseek-v4-pro`。
- `brv status` 显示当前项目 `/home/kevinlasnh/Projects/sharing-studio` 的 `.brv/context-tree/` 尚未初始化。
- `brv` PATH 持久配置已写入 `~/.profile` 和 `~/.bashrc`，但当前 Codex 会话未继承新 PATH。
- 已通过 `~/.local/bin/brv` symlink 让当前会话可直接调用 `brv`。
- PWF skill 已安装在 `~/.agents/skills/planning-with-files-zh/SKILL.md`，Claude 侧也存在 `~/.claude/skills/planning-with-files-zh`。
- Second Brain vault 已存在于 `/home/kevinlasnh/Documents/second-brain/`；本轮只审查脚手架/agent/插件配置，不清理 `daily/`、`wiki/`、`raw/` 内容文档。
- vault 中明确的 Gemini/Claudian 删除候选包括 `GEMINI.md`、`.gemini/`、`.claudian/`、`.obsidian/plugins/realclaudian/`。
- `AGENTS.md`、`CLAUDE.md`、保留的 `.agents/skills/**` 与 `.claude/skills/**` 仍包含 Gemini、`.gemini`、`.claudian` 和旧 Windows 路径/PowerShell 规则，需要改为 Claude Code + Codex 双宿主和 Ubuntu 路径。
- `.obsidian/graph.json` 的 agent config 颜色组仍包含 `file:GEMINI`；`.obsidian/workspace.json` 仍有 `realclaudian:Open Claudian` UI 状态。
- `.brv/config.json` 仍记录旧 Windows cwd `G:\My Drive\second-brain`，应改为 `/home/kevinlasnh/Documents/second-brain` 或通过 brv 重新初始化/修复。
- `.workflows/` 中也有 Gemini/Claudian 文本残留，但属于历史 workflow 产物，不是当前生效脚手架；默认建议保留，除非用户要求零残留或归档历史工作流。
- 已完成 Second Brain 活动脚手架清理：删除 `GEMINI.md`、`.gemini/`、`.claudian/`、`.obsidian/plugins/realclaudian/`；保留 `.claude/`、`.agents/`、`.obsidian/`、`.brv/`、`.workflows/`。
- 已将 `AGENTS.md` / `CLAUDE.md` 改为 Ubuntu vault 路径与 Claude Code + Codex 双宿主 router，同步正文保持一致。
- 已将 `.claude/skills` 和 `.agents/skills` 的 Gemini/Claudian/旧 Windows vault 路径规则清理为双宿主规则；两套 skill 递归 diff 无差异，16 个 skill 目录通过 `quick_validate.py`。
- 已更新 `.obsidian/graph.json` agent config query 为 `file:CLAUDE OR file:AGENTS`，移除 `.obsidian/workspace.json` 的 `realclaudian:Open Claudian` 状态，更新 `.brv/config.json` cwd 到 Linux vault 路径，并从 `.gitignore` 移除 `.claudian/`。
- 当前 Ubuntu 系统没有 `powershell` / `pwsh`，因此 `.claude/settings.json` 与 `.claude/scripts/*.ps1` 的实际执行验证未跑；这是后续 Claude Code hook Linux 化任务，不属于本轮 Gemini/Claudian 清理。
- Second Brain 活动运行脚手架已迁移到 Ubuntu 原生路径：`.claude/settings.json` 使用 `bash` + `python3 "$CLAUDE_PROJECT_DIR/.claude/scripts/hook_policy.py" <policy>`；原 `.claude/scripts/*.ps1` 已删除并由 `.claude/scripts/hook_policy.py` 合并承接。
- 活动 skill 脚本已迁移为 Python：`second-brain-delete`、`second-brain-lint`、`second-brain-hf-backup` 的 `.ps1` 脚本已移除，`.claude/skills` 与 `.agents/skills` 下对应 `.py` 脚本保持镜像一致。
- Ubuntu 迁移验证结果：Python 语法编译通过；`.claude` / `.agents` / `.obsidian` JSON 解析通过；`.claude/skills` 与 `.agents/skills` 递归 diff 无差异；16 个 skill 目录通过 `quick_validate.py`；root `CLAUDE.md` / `AGENTS.md` 正文同步。
- Hook dry-run 覆盖了废弃 wiki scaffold、wiki frontmatter、daily no-link、raw provenance / embed 等阻断和放行路径，结果全部符合预期。
- `deep_audit.py --skip-basic-memory` 已确认脚手架层 no Windows/PowerShell runtime references、no `.ps1` runtime files、Obsidian graph/workspace 配置清理完成；剩余 2 条失败均为 `wiki/` 内容页 raw 语义问题，不属于本轮脚手架迁移范围，未修改。
- 为 Basic Memory MCP 的 Ubuntu 入口安装了用户级 `uv` / `uvx` 到 `/home/kevinlasnh/.local/bin`，现有 `.claude/mcp.json` 的 `uvx basic-memory mcp` 命令入口可被 shell 找到。
- `uvx basic-memory --help` 首次运行开始解析/下载依赖，但在数分钟后缓存停止增长且进程未返回，已终止；Basic Memory 依赖环境仍需后续单独完成下载/初始化验证。
- 二次复核发现 `second-brain-graph-manager` 的 wiki color contract 与 `deep_audit.py` / `.obsidian/graph.json` 不一致：graph-manager 写 `40563/#009E73`，实际检查契约为 `33791`；已修正 graph-manager 两份镜像 skill，并修复其 JSON 示例中的错误转义。
- Basic Memory 的真实闭环问题不是 MCP 配置缺失，而是 CLI 入口未安装：`.claude/mcp.json` 使用 `uvx basic-memory mcp`，但系统没有 `basic-memory` 可执行命令，原 skill 文档假设 `basic-memory ...` 可直接运行。
- 已将活动脚手架文档中的 Basic Memory CLI 命令迁移为 `uvx basic-memory ...`，使其匹配当前 Ubuntu 上已存在的 `uvx` 入口；`deep_audit.py` 的 runtime fallback/timeout 修复尚未完成。
- `uv tool install basic-memory` 曾运行约 26 分钟，缓存仍增长但没有生成 `basic-memory` 命令；用户指出可能是 terminal proxy 问题后，检查确认 `verge-mihomo` 监听 `127.0.0.1:7897`，Git 全局代理已配置，但当前 shell env 没有 `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY`。
- 已新增 `/home/kevinlasnh/.config/proxy-env.sh`，并让 `/home/kevinlasnh/.bashrc` 在 non-interactive guard 前加载，同时让 `/home/kevinlasnh/.profile` 加载。验证 `bash -lc` 与 `bash -ic` 均能读到 proxy env，`curl` 访问 PyPI / Astral 的 remote IP 显示 `127.0.0.1`。
- Second Brain 日记已写入 `daily/2026-06-12.md`；因 Basic Memory CLI 依赖仍未完成，journal 的 Basic Memory closure 与 Hugging Face backup closure 暂时 deferred。
- 2026-06-13 复核 Basic Memory 官方文档：当前本地安装仍推荐 `uv tool install basic-memory`，安装后验证 `basic-memory --version`；MCP 配置可用 `uvx basic-memory mcp`；项目目录通过 `bm project add <name> <path>` 和 `bm project default <name>` 管理；Codex CLI 本地 MCP 可用 `codex mcp add basic-memory bash -c "uvx basic-memory mcp"`，如需锁定项目则追加 `--project <name>`。来源：docs.basicmemory.com quickstart/local install/CLI/Codex integration/configuration。
- 2026-06-13 ByteRover 查询 `Second Brain Basic Memory Ubuntu uvx`、`agent scaffold Ubuntu migration`、`sharing-studio PWF brv setup` 均无召回，说明本轮 Ubuntu 迁移闭环尚未沉淀到长期知识库。
- 2026-06-13 Basic Memory 本机闭环完成：清理 malformed uv tool 环境后，`uv tool install basic-memory` 成功安装 `basic-memory` / `bm` 0.22.1；注册本地 project `second-brain` 指向 `/home/kevinlasnh/Documents/second-brain`；首轮 search reindex 处理 497 个文件；journal checkpoint 的完整 reindex 完成 497 个 entity embeddings，0 skipped，0 errors；最终 `basic-memory status --project second-brain --json` clean。
- 2026-06-13 Second Brain deep audit clean：修复 `.obsidian/workspace.json` 的 `realclaudian:Open Claudian` 残留、两处 raw instructional image policy 问题，以及 `hook_policy.py` 中 raw 文件名误触发 forbidden context 的 false positive；更新两份镜像 `deep_audit.py`，增加 `basic-memory` / `uvx basic-memory` fallback、timeout、status clean 校验和 search probe；最终 `deep_audit.py --vault-root .` 返回 clean、56 checks、0 issues。
- 2026-06-13 HF backup 收口仍有外部凭据阻塞：`second-brain-hf-backup` 已在 vault 本地创建 commit `a9bfe2c`，但 `git push hf HEAD:main` 失败，真实错误为 Hugging Face HTTPS 没有可用 credential（`could not read Username for 'https://huggingface.co'`）。当前 vault 工作区 clean；需要用户完成 HF Git 凭据登录后重跑 push。
- 2026-06-13 Second Brain 额外清理复核：全仓检查隐藏目录、缓存、备份文件和脚手架状态后，唯一确认无必要并已删除的文件是 `.obsidian/graph.json.bak`；`.brv/` 是 ByteRover 本地状态且被忽略，不属于应删除对象。复核结果为 `deep_audit.py` clean（56 checks，0 issues）、Basic Memory status clean、search probe 可用、embeddings 498/498 up to date、`.claude/skills` 与 `.agents/skills` 镜像一致。HF 远端备份仍受 HTTPS credential 缺失阻塞。
- 2026-06-13 Second Brain 日记闭环复核：已追加 `daily/2026-06-13.md` 记录 `.obsidian/graph.json.bak` 删除、全仓 audit clean 和 Basic Memory clean；日记链接边界检查无 wikilink / 本地 Markdown link。随后执行 `uvx basic-memory reindex --project second-brain`，结果 498 entities embedded、496 skipped、0 errors，二次 status clean。HF backup 脚本创建本地 commit `b33cb78`，但 `git push hf HEAD:main` 仍因 Hugging Face HTTPS credential 缺失失败。
- 2026-06-13 Claude Code 全局配置已部署：创建 `/home/kevinlasnh/.claude/CLAUDE.md`，内容从 `/home/kevinlasnh/.codex/AGENTS.md` 同步，仅 H1 改为 `# Claude Code Global Configuration`。验证 H1 以下 `diff` 无输出，sha256 一致。
- 2026-06-13 PWF worktree 继承问题：`sharing-studio` 当前 `.gitignore` 忽略 `task_plan.md` / `findings.md` / `progress.md`，且这三份文件未被 `git ls-files` 跟踪。因此新建 git worktree 时不会自动带上 PWF 上下文。下回任务应调整为“本地 Git 可跟踪三件套 + pre-push/等价检查阻止推送受保护路径”，以匹配多 worktree 记忆策略。

## 技术决策
| 决策 | 理由 |
|------|------|
| 删除 Codex 全局规则中所有 Gemini/GEMINI/.gemini 内容 | 用户明确当前只使用 Claude Code 和 Codex |
| 创建并同步 `~/.claude/CLAUDE.md` | 用户要求按规则部署 Claude Code 全局配置；全局两份文件必须同时存在，仅 H1 按工具差异化 |
| 创建 PWF 三件套记录恢复进度 | 用户明确要求如果 PWF 可见就记录进度 |
| 不在 PWF 中记录 API key | 避免 secret 持久化 |
| Second Brain 清理先只处理脚手架 | 用户明确不需要清理 `daily/`、`wiki/` 等具体内容文档 |
| `.workflows/` 历史产物默认保留 | 其中可能有旧 Gemini/Claudian 字样，但不是当前生效配置，避免误删历史 workflow 记录 |

## 遇到的问题
| 问题 | 解决方案 |
|------|---------|
| 当前 Codex 会话直接执行 `brv` 报 command not found | 创建 `~/.local/bin/brv` symlink 指向 `/home/kevinlasnh/.brv-cli/bin/brv` |
| `brv providers connect deepseek` 只支持 `--api-key` 参数 | 使用关闭回显的 TTY `read` 获取 key 后调用 brv，避免 key 出现在命令文本和输出中 |
| 当前项目没有 PWF 三件套 | 用户明确要求记录进度后，按 PWF 模板创建三件套 |
| `uvx basic-memory --help` 首次构建未完成 | 已安装 `uv` / `uvx`；Basic Memory 依赖下载/初始化后续单独处理 |
| terminal 工具没有走 Clash Verge / Mihomo 代理 | Git 有 `http.proxy` / `https.proxy`，但 shell env 未设置；已通过 `~/.config/proxy-env.sh` + `~/.bashrc` + `~/.profile` 永久配置 |

## 资源
- `/home/kevinlasnh/.codex/AGENTS.md`
- `/home/kevinlasnh/.agents/skills/planning-with-files-zh/SKILL.md`
- `/home/kevinlasnh/.brv-cli/bin/brv`
- `/home/kevinlasnh/.local/bin/brv`
- `/home/kevinlasnh/.local/bin/uv`
- `/home/kevinlasnh/.local/bin/uvx`
- `/home/kevinlasnh/.config/proxy-env.sh`
- `/home/kevinlasnh/Documents/second-brain/daily/2026-06-12.md`
- `/home/kevinlasnh/Projects/sharing-studio/projects/`

## 视觉/浏览器发现
- 无。

## 2026-06-14 全局 agent markdown 校验发现

- OpenAI Codex 官方 `AGENTS.md` 文档确认 Codex 会合并全局和仓库级指令；`~/.codex/AGENTS.md` 是用户级指令路径，仓库根 `AGENTS.md` 是仓库级指令路径。
- OpenAI Codex skills 文档确认用户级 skill 目录为 `~/.codex/skills`，同时也支持 `~/.agents/skills` 作为 Agent Skills 生态路径；当前本机全局规则选择 `~/.agents/skills` 作为跨宿主真源，属于可行的个人约定。
- Claude Code memory / skills 文档确认 `CLAUDE.md` 可作为 memory 文件，Claude Code skill 可放在用户级 `~/.claude/skills` 或项目级 `.claude/skills`。
- ByteRover CLI 本机版本 `3.16.1` 确认 `brv query` / `brv curate` / `brv review pending` / `brv worktree` 命令存在；`brv curate --files` 最多 5 个文件引用；`--timeout` 在当前 help 中标记为 deprecated/no effect。
- `brv query` 对本仓库的三条记忆框架相关问题均无召回，说明本轮全局 agent markdown / PWF / ByteRover 规则尚未沉淀到 L3 长期记忆。
- 本机 `sudo -n true` 与 `sudo -n whoami` 验证通过，当前用户 `kevinlasnh` 可免密执行单条 sudo 命令；locale 和全局/PWF markdown 文件均为 UTF-8。
- 已为当前 `sharing-studio` 仓库根补齐实体 `AGENTS.md` / `CLAUDE.md`，两份内容一致，并通过 `.gitignore` 保持本地忽略。
- 已调整当前 `sharing-studio` 的 `.gitignore`：`task_plan.md`、`progress.md`、`findings.md` 不再被忽略；三件套当前仍是未跟踪文件，需要后续 `git add` 才会真正进入 Git 跟踪并支持新 worktree 继承。
- `brv-query` / `brv-curate` skill 校验通过；`planning-with-files-zh` 可被当前 Codex 会话列为可用 skill，但用 Codex `skill-creator` 的 `quick_validate.py` 校验会因 `hooks`、`user-invocable` frontmatter 扩展键失败，属于跨宿主 skill 元数据兼容性风险。

## 2026-06-14 全局 agent markdown 二次逻辑复查

- 仓库根 `AGENTS.md` / `CLAUDE.md` 的规则已调整：主工作仓库若存在必须成对同步，多 Git worktree 可缺少这两份文件；此时沿用已加载的仓库级规则与全局规则，不强制补齐。
- “任何未被 `.gitignore` 排除的文件都视为应提交和推送”与 PWF 三件套“必须 Git 跟踪”逻辑一致；这意味着 PWF 三件套也会被视为应推送。该行为符合当前规则文本，但如果未来想让 PWF 只本地提交、不推远端，需要重新引入 pre-push 保护规则。
- ByteRover 当前 `.brv/context-tree` 路径存在，但本仓 `brv vc status` 返回 version control not initialized；全局 L3 规则说“数据位于 `.brv/context-tree/`、不使用云同步”仍成立，但不应假设 ByteRover version control 已初始化。
- 本机全局 `AGENTS.md` / `CLAUDE.md` 完全一致，仓库根 `AGENTS.md` / `CLAUDE.md` 完全一致，sudo/locale/encoding 校验仍通过。
- 2026-06-14 记录进度前复核：本次 Git 提交范围应包含 `.gitignore` 与 PWF 三件套；仓库根 `AGENTS.md` / `CLAUDE.md` 为本地 agent 配置且已被 `.gitignore` 忽略，不应进入提交。

---
*每执行2次查看/浏览器/搜索操作后更新此文件*
*防止视觉信息丢失*
