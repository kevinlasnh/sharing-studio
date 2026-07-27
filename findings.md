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

## 2026-06-22 agent workflows Skill 存在性检查

- 当前仓库存在 `projects/agent-workflows/skills/heavy-research/SKILL.md` 和 `projects/agent-workflows/skills/heavy-review/SKILL.md`。
- 仓库内没有找到 `medium-research` 或“中型调研”命名的独立 Skill；现有调研 Skill 是 `heavy-research`，触发词为“准备开始进行重型调研”。
- 本机全局 `/home/kevinlasnh/.agents/skills/` 与 `/home/kevinlasnh/.claude/skills/` 下尚未部署 `heavy-research` / `heavy-review`。
- 现有仓库版本的两个 Skill 辅助脚本均为 `.ps1`；当前 Ubuntu 环境未发现 `pwsh` 或 `powershell`，直接部署后脚本调用需要先迁移为 Linux 可执行入口或安装 PowerShell。

## 2026-06-22 agent workflows Skill 全局部署

- 已将 `projects/agent-workflows/skills/heavy-research` 复制到 `/home/kevinlasnh/.agents/skills/heavy-research`。
- 已将 `projects/agent-workflows/skills/heavy-review` 复制到 `/home/kevinlasnh/.agents/skills/heavy-review`。
- 已创建 Claude Code 全局 symlink：`/home/kevinlasnh/.claude/skills/heavy-research -> /home/kevinlasnh/.agents/skills/heavy-research`，`/home/kevinlasnh/.claude/skills/heavy-review -> /home/kevinlasnh/.agents/skills/heavy-review`。
- 已验证全局 `.agents` 目录中的两份 Skill 与仓库 `projects/agent-workflows/skills/` 源目录当前内容一致。
- 注意：部署内容仍包含 `.ps1` 辅助脚本；当前 Ubuntu 环境没有 PowerShell 运行时，后续优化应优先迁移这些脚本和 `SKILL.md` 中对应命令。

## 2026-06-22 heavy workflows Ubuntu/Linux 迁移

- 已将 `heavy-research` 的 `new-session-dir.ps1` / `find-latest-session.ps1` 替换为 Python 脚本：`new-session-dir.py` / `find-latest-session.py`。
- 已将 `heavy-review` 的 `find-latest-plan.ps1` / `ensure-review-dir.ps1` 替换为 Python 脚本：`find-latest-plan.py` / `ensure-review-dir.py`。
- 已更新 `SKILL.md` 和 reference 文档中的脚本调用为 `python3 ~/.agents/skills/.../*.py`，并将审查 hash 示例切到 `sha256sum` / Python `hashlib`。
- 已将源码审查 reference 从 Windows + PowerShell 取证语义迁移到 Ubuntu/Linux + bash/python3：路径检查使用 `test` / `stat` / `find` / `git ls-files`，语法检查使用 `bash -n` / `python3 -m py_compile`，dry-run 只允许无状态变更模式。
- 仓库源目录与全局 `/home/kevinlasnh/.agents/skills/heavy-research` / `heavy-review` 已同步；Claude Code 侧 symlink 继续指向 `.agents` 真源。
- 验证通过：Python 编译、临时 `.workflows` smoke test、全局脚本 smoke test、PowerShell/`.ps1` 残留扫描、`skill-creator/scripts/quick_validate.py` 对仓库源目录和全局安装目录共 4 次校验。

## 2026-06-22 heavy workflows 触发词扩展

- `heavy-research` 现在接受两个精确触发词：`准备开始进行重型调研` 和 `准备开始进行 Heavy Research`。
- `heavy-review` 现在接受两个精确触发词：`准备开始进行重型审查` 和 `准备开始进行 Heavy Review`。
- 已同步更新 `projects/agent-workflows/README.md` 与 `README.zh-CN.md` 的触发词表。
- 已同步全局 `/home/kevinlasnh/.agents/skills/heavy-research` 与 `/home/kevinlasnh/.agents/skills/heavy-review`；Claude Code 侧 symlink 自动复用。
- 逻辑检查结果：`quick_validate.py` 对仓库源目录与全局目录共 4 项均通过；触发词一致性脚本通过；仓库与全局 skill 目录 `diff -qr` 无差异。README 的“只响应精确触发词”仍成立，因为每个 Skill 现在有两个精确触发词。

## 2026-06-22 heavy workflows subagent thinking effort 对齐

- 当前宿主 subagent 工具支持 `reasoning_effort` override，且省略该字段时默认继承父 agent effort；因此 Skill 文档应优先保持继承，不应无条件写入可能覆盖继承值的不同参数。
- `heavy-research` 现在在 B2 派发规则中要求 subagent thinking effort / 推理强度与 main agent 本轮实际 effort 一致，并在 web / source / memory 三个 subagent prompt 中加入“推理强度”行。
- `heavy-review` 现在在 R2.3 派发规则中要求 subagent thinking effort / 推理强度与 main agent 本轮实际 effort 一致，并在 web / source 两个 subagent prompt 中加入“推理强度”行。
- 两个 core reference（`research-loop-core.md`、`review-loop-core.md`）也补充同一执行约束，明确后台 / 并行执行不代表降低 effort，同时禁止要求输出隐藏思维链。
- 已同步全局 `/home/kevinlasnh/.agents/skills/heavy-research` 与 `/home/kevinlasnh/.agents/skills/heavy-review`；Claude Code 侧 symlink 自动复用。
- 验证通过：仓库源和全局目录 `diff -qr` 无差异；`quick_validate.py` 对仓库源目录和全局安装目录共 4 项通过；触发词、prompt effort 覆盖、core reference 覆盖、Linux 残留和 Python 脚本语法检查均通过。

## 2026-06-22 heavy workflows 最细逻辑复查

- 本轮重新全量读取 `heavy-research` / `heavy-review` 的 `SKILL.md`、所有 reference 和 4 个 Python helper 脚本，重点复查触发词、恢复规则、subagent prompt、文件可见性闭环、只读边界、输出契约、模板占位禁止和 Linux 运行假设。
- 发现并修复一个 `heavy-review` 源码取证路线逻辑冲突：文档把 `python3 -m py_compile` 列入“只读 Shell / 不修改系统状态”的 syntax-check 范围，但该命令会生成 `__pycache__` / `.pyc`，与只读边界冲突。
- 同一处还存在 inline Bash 片段“保存到临时 scratch 文件后运行 `bash -n`”的写入冲突；已改为 stdin / here-doc 等无持久文件方式，无法无写入解析时标记 `UNVERIFIABLE`。
- 修复后 Review 源码路线统一要求 Python 使用内存 `compile()` 检查，并明确禁止生成 `__pycache__` / `.pyc`。
- 已同步全局 `/home/kevinlasnh/.agents/skills/heavy-review`；`heavy-research` 本轮未发现需修改的逻辑问题。仓库源目录与全局安装目录 `diff -qr` 无差异，Claude Code 侧 symlink 自动复用。
- 验证通过：`quick_validate.py` 对仓库源和全局安装目录的 `heavy-research` / `heavy-review` 共 4 项通过；结构化一致性检查、Linux/PowerShell 残留扫描、脚本内存语法检查、`git diff --check` 均通过。

## 2026-06-22 heavy workflows 再次最细逻辑复查

- 发现并修复 `heavy-review` 源码路线只读 Shell 白名单中的 `git status --short` 风险：本机 Git 文档说明普通 `git status` 可能作为副作用刷新 index；已改为 `git --no-optional-locks status --short`，并同步到主 prompt 与 source reference。
- 发现并修复源码语法检查示例里的 `<script>` 占位风险：该写法若被复制到 shell 中会被解释为重定向语法；已改为 `SCRIPT_PATH`。
- 收紧 dry-run 逻辑：Review 源码路线现在只允许已确认不会写缓存、锁文件、构建产物或外部状态的 dry-run / syntax-check；不确定时必须标记 `UNVERIFIABLE` 或改用静态证据。
- 修复 `heavy-research` 恢复规则文字冲突：B0 允许在 `_run.md` 缺失或半写且无法可靠修正时确认一次缺失恢复字段，底部约束现已同步覆盖该例外。
- 补齐 reference 与主流程一致性：Research 综合模板明确“方案不合理”重跑时复用同一 SESSION_DIR、生成新 `run_id` 且不混合旧报告；Review 综合模板明确“修复方案不合理”时使用新的 `review_run_id` 且不混合旧报告；deployment-plan 模板明确文件由阶段 D 写入而非脚本预创建。
- 仓库源与全局 `/home/kevinlasnh/.agents/skills/heavy-research` / `heavy-review` 已同步，Claude Code 侧 symlink 自动复用。
- 验证通过：仓库源与全局安装目录 `quick_validate.py` 共 4 项通过；自定义一致性检查、Python helper 内存编译、仓库/全局 `diff -qr`、`__pycache__` / `.pyc` 扫描、危险残留扫描和 `git diff --check` 均通过。

## 2026-06-22 heavy workflows goal 自我迭代复查

- 本轮使用 goal 持续迭代检查 `heavy-research` / `heavy-review`，每轮发现问题后立即修复并重跑验证；最后一轮未发现新增逻辑问题后收口。
- 发现并修复最终产物模板占位漏洞：Research 报告、综合摘要、deployment-plan、Review 报告、综合审查报告和 inline fix 都必须拒绝尖括号占位符和省略号占位；未知内容要写成真实 `UNVERIFIABLE`、待确认、前置检查或风险项。
- 发现并修复查询模板字面复制风险：`brv query "<关键概念>"` 改为非尖括号示例并要求替换为真实关键词；Review 联网反向词扫描同样要求替换为真实工具名/API/命令/操作动词。
- 发现并修复 Ubuntu 版 Skill 中的 PowerShell 生态示例残留：`PSScriptAnalyzer` HyDE 示例已替换为 `rsync 3.2.7` 示例。
- 补齐 synthesis reference 的输入校验闭环：即使主 Skill 已在 B3/R2.4 拦截，Research/Review 综合模板自身也会拒绝带模板占位的坏报告，不把坏报告继续综合。
- 仓库源已同步到 `/home/kevinlasnh/.agents/skills/heavy-research` 和 `/home/kevinlasnh/.agents/skills/heavy-review`；Claude Code 侧 symlink 继续指向 `.agents` 真源。
- 最后一轮验证通过：仓库源与全局安装目录 `quick_validate.py` 共 4 项通过；自定义 50+ 项一致性检查、helper 脚本临时目录 smoke test、helper 内存编译、仓库/全局 `diff -qr`、危险残留扫描、`__pycache__` / `.pyc` 扫描和 `git diff --check` 均通过。

---
*每执行2次查看/浏览器/搜索操作后更新此文件*
*防止视觉信息丢失*

## 2026-07-26 Heavy Workflows 再审查启动发现

- 当前仓库源目录仍为 `projects/agent-workflows/skills/heavy-research` 与 `projects/agent-workflows/skills/heavy-review`。
- PWF 显示 2026-06-22 已做过多轮逻辑修复和全局同步，但本轮完成条件要求以当前 worktree 与本机安装状态重新证明，不直接沿用旧的“零问题”结论。
- 本轮必须同时覆盖：主 `SKILL.md`、全部 references、helper scripts、README 触发契约、源目录与全局安装一致性、Claude Code symlink、可执行 smoke tests、最终 Git commit 与远端 push 状态。
- 当前本机 `~/.agents/skills/heavy-research` 与 `heavy-review` 存在且和仓库源目录无 diff；但 `~/.claude/skills/heavy-research` 与 `heavy-review` 均不存在，历史记录中的跨宿主 symlink 已丢失，最终重新装载必须补回并验证。
- Heavy Review 的核心闭环存在自相矛盾：R1/R2 明确规定 plan hash 变化后旧 review 报告不可复用，但 R4 inline 修改 plan 后直接宣称“可以基于此版本部署”并结束，没有对新 hash 版本做 post-fix verification；修复本身可能引入新冲突，当前证据不能证明修改后的 plan 已通过审查。
- `find-latest-session.py` 的 active 指针路线会校验路径仍位于当前 `.workflows/`，但 fallback candidates 未复用该校验；`find-latest-plan.py` 也会跟随时间戳目录 symlink 到仓库外，`ensure-review-dir.py` 则接受任意目录。组合后可能审查或创建 review 目录到授权仓库之外，路径闭环不完整。
- `heavy-review/references/review-framework.md` 含本机特化且逻辑错误的“跨仓库影响”定义，并把所有 `git push` 一概判 HIGH；`subagent-source.md` 又把 PWF 三件套一概视为不得 push，直接与本仓当前“PWF 必须 Git 跟踪并推送”的仓库规则冲突。公共 Skill 应依据目标仓库的明确 policy、Git ignore 和敏感内容边界判断，不能硬编码个人仓库规则。
- Research 恢复契约的完整性检查未覆盖 `_run.md` 的 `topic` / `mode` 有效性；Review 恢复契约未明确要求 `plan_path` 存在且等于当前 `PLAN_PATH`。两者都可能把字段不完整的半写父契约误判为可恢复。
- Review R2.4 的“证据级别缺失即失败”未限定到需要证据的 FAIL finding，和 PASS / UNVERIFIABLE 模板本身不要求证据级别存在冲突，需收窄校验条件。
- 两份 README 的流程图在 inline fix 后结束，复现了 post-fix 未复审缺口；“本地 planning 文件都留在 Git 之外”也与本仓实际跟踪 PWF 的 policy 不一致，需要改为尊重目标仓库策略且不发布私密内容。

## 2026-07-26 Heavy Workflows 首批加固发现

- Review 的 plan 内容和 plan hash 必须来自同一次 byte read；分别读取会产生 TOCTOU，导致报告审查的内容与声明 hash 不一致。当前已增加稳定 plan snapshot helper，但后续所有报告与复审契约仍需统一只引用该快照。
- 仅绑定 plan hash 不足以复用审查结果：源码在 plan 不变时仍可能漂移。Review 需要同时绑定 Git-visible source snapshot，并在源码状态变化后使旧报告失效。
- inline fix 必须绑定用户批准记录和 expected plan hash，并具备锁、备份、原子替换与 checkpoint；修改完成后还必须以新 hash 和新 `review_run_id` 自动完整复审，不能直接宣称可部署。
- Research 的综合摘要、用户批准和 plan provenance 若只存在聊天上下文，会与“文件是真源”冲突；这些状态必须持久化，并由 Review 在进入审查前校验其链路完整性与防篡改 hash。
- `.active-session` 不能无限保留；session 完成或放弃后必须关闭。fallback 找到合法未完成 session 后还应重新原子写回 active pointer，避免后续继续扫描或误恢复旧任务。
- 时间戳目录不能只靠正则判断，必须用真实日期解析并拒绝伪日期、`-0` 和非法前导零后缀；所有 helper 应共享同一语义。
- plan 中的 Markdown 内容不能直接成为 `_run.md` 控制字段；必须编码或使用独立结构化 metadata，避免换行和伪字段注入。`unverified`、`STALE`、`CONFLICT` 等状态也不能因文件存在或字符串命中而被误判为 PASS。
- 当前首批 helper 和 Research 契约只解决了部分底层机制；Heavy Review references、证据等级映射、web privacy/URL 边界、公共 Git/PWF policy、post-fix 复审和自动化测试仍是发布阻断项。

## 2026-07-26 中间提交后契约复核发现

- Heavy Review 的恢复段已经要求 checklist 七字段和完整父级元数据，但 R2.1、`_run.md` 示例、subagent prompt、`review-loop-core.md` 与 `synthesis-prompt.md` 仍只定义旧四字段；按当前文本，新建产物会被同一 Skill 的恢复校验判无效。
- `_run.md` 新建模板缺少恢复阶段宣称必需的 `session_id`、`plan_snapshot_path`、`repo_root`、`source_snapshot_sha256`、`web_evidence_ttl_hours` 等字段，说明父契约尚未真正落地。
- `review-framework.md` 仍把个人 Second Brain 层级当作公共“跨仓库”定义，并把所有 Git push 直接判 HIGH；`subagent-source.md` 仍一概禁止 PWF/隐藏目录 push，与目标仓库 policy 冲突。
- `synthesis-prompt.md` 与报告模板尚未把 `CONFLICT` / `STALE` / `MISSING` / `unverified` 明确映射到 FAIL 或 UNVERIFIABLE；仅检查证据级别字符串合法，仍可能让非 confirmed 证据支撑 PASS。
- R3 综合结果只输出 terminal，用户批准也未持久化；而新增 inline-fix helper 要求 `review/_approval.md` 和 `review_summary_sha256`，主流程尚未说明如何生成、校验和恢复这些文件。
- R4 主文档与 `fix-edit-pattern.md` 仍要求逐次 Edit 并在完成后直接宣称可部署，没有调用新增事务 helper，也没有强制创建新 review run 做 post-fix 全量复审。
- Research `find-latest-session.py` 会跟随 `.active-session` symlink，fallback 成功后不修复 active pointer；`update-session-state.py` 未验证 topic hash 格式或 phase 转移；`emit-plan-provenance.py` 尚未绑定 `_state.md`、topic hash、session_id 与各报告元数据。

## 2026-07-26 文件真源重构决策

- 中断恢复不再尝试混用“单条合法旧报告 + 单条补跑报告”；只要完整 bundle 未通过 validator，就用新 review id 全量重跑。该选择增加少量成本，但消除了半轮证据组合和恢复分支爆炸。
- checklist 不再把 plan 原文复制进 `_run.md` 控制字段；改用安全摘要 + `lines N-M`/synthetic locator + 精确 bytes hash。这样 subagent 仍可从只读 snapshot 找回原文，同时阻断 Markdown 伪字段注入。
- Review 的综合报告、精确替换和用户决定分别落到 `summary.md`、`fixes.json`、`_approval.md`；批准后 helper 归档旧 run、保存备份并写 prepared/applied transaction state，支持中断后的 hash 幂等恢复。
- PASS 的机械规则收紧为只接受 confirmed；CONFLICT/MISSING 只能支撑 FAIL，unverified/STALE 只能支撑 UNVERIFIABLE。文件存在、字符串命中或非 confirmed 证据不再可能静默通过。
- 普通 Git push 的严重度不能预设为 HIGH；应按强推/保护历史、可逆性、共享或生产范围、敏感内容和仓库明确 policy 逐案判定。

## 2026-07-26 第二轮机械闭环复核

- Research 目前只校验 `summary.md` 自报的 `key_gap_ids` 格式与编号范围，没有从各启用维度报告的 P0/P1 confidence 机械反推关键缺口；因此摘要仍可把真实 `unverified` / `CONFLICT` / 仅记忆支撑项谎报为 `none`。
- `prepare-review-run.py` 会归档任何通过 `--require-summary` 的 changes-required bundle，即使 `_approval.md` 尚未记录用户决定；这允许新 run 绕过 R3 的持久化批准/拒绝关口。
- `apply-inline-fixes.py` 的幂等提前返回发生在 session 时间戳语义校验之前，且未限定 plan 文件名；伪 session 名或同目录其他文件可能进入事务恢复分支。
- `validate-review-run.py` 只抽取合法的 `状态：PASS|FAIL|UNVERIFIABLE`，会忽略同一审查项中的额外非法状态行；`route_items` 也只取首个匹配 block，重复父级控制块没有被显式拒绝。
- `new-session-dir.py` 在 `.active-session` 原子替换失败时会留下可被 fallback 恢复的孤儿 `in_progress` session；创建事务必须在指针失败时回滚自身创建的空 session，并返回明确错误。

## 2026-07-26 第三轮 Research 静态复审

- `find-latest-session.py` 的 state 恢复只检查 `status != complete`，没有校验 phase 是否属于 B0-D，也没有校验唯一、带时区的 `updated_at`；损坏 state 仍可能被自动恢复。
- Research 多个 helper 只拒绝最终文件本身是 symlink，却没有拒绝 `research/` 父目录 symlink；`_state.md`、报告、summary 和 approval 可能经父目录跳到 session 外，违背仓库边界。
- `update-session-state.py` 把 absolute active pointer 描述成 canonical，但没有要求原字符串等于 resolve 后路径；完成阶段的 pointer 删除与临时文件清理也缺少受控错误返回。
- `new-session-dir.py` 的 finally 对异常临时路径直接 `unlink()`，若同名路径被竞争替换成目录会再次抛错并遮蔽原始回滚结果；创建 research/state 失败的错误文案也被误称为 active pointer 失败。
- `validate-deployment-plan.py` 未限定文件名必须为 `deployment-plan.md`，回滚表只按集合比较而不拒绝重复步骤行，也未机械要求 `⚠️ 不可逆` 与“不可逆步骤的回滚方案”内容一致。

## 2026-07-26 第三轮 Review helper 静态复审

- `capture-plan.py` 未限定输入文件名，且可在已有 `_run.md` 时覆盖当前 plan snapshot；直接调用可能让一个正在使用的 review run 失效。
- `capture-source-snapshot.py` 只 hash 文件内容与粗粒度类型；可执行位变更和 submodule/index 状态等 Git-visible 变化可能不改变 snapshot hash，需要绑定稳定的 porcelain/index 状态。
- `prepare-review-run.py` 以字符串包含判断 fix-state waiting，未拒绝非文件 fix-state；invalid bundle 的“已归档”捷径只看 run_id/manifest 存在，不比较当前文件 hash，可能直接删除与历史内容不同的当前 bundle。
- `archive-review-run.py` 先算 manifest 后重新读取文件写归档，存在 TOCTOU；已有 history target 只比较 manifest JSON，不复核归档文件真实 hash，tamper 后仍可能返回 already-archived。
- `mark-fix-verified.py` 没有机械要求当前 PASS run 的 mode 为 post-fix，也没有完整验证 fix-state 的 session/hash/路径/timestamp schema，可能把错误父状态标为 verified。
- 多个 review 写入 helper 的临时文件 finally 直接 unlink，目录竞争会遮蔽原错误；`record-review-decision.py` 的 summary 读取和 archive 后续失败也缺少完整受控错误闭环。
- `field()` 对任何包含三个点的单行值都判模板残留，与文档只禁止“独占行省略号”不一致，会误拒绝合法主题、原因或路径文本。

## 2026-07-26 第三轮 Review validator / 事务复审

- `_run.md` 可以绑定手工伪造的 `provenance.json`；validator 目前只核对 JSON status/hash，没有重新运行只读 provenance verifier，因此 fabricated `confirmed` 可绕过 Research 链路。
- source snapshot 为 `unverifiable` 时 validator 不要求当前 helper 结果仍为 unverifiable，也没有机械要求 checklist 包含 `synthetic:source-snapshot:unverifiable`；provenance 非 confirmed 和必需 plan 章节缺失同样只靠文字要求，checklist 可省略后全 PASS。
- 报告证据等级按整个 item body 汇总，FAIL 可以借用 PASS 小节的 confirmed 证据通过；validator 没有要求 FAIL/UNVERIFIABLE/PASS 状态位于对应小节并具有问题/建议、原因/处理、检查点/证据等完整字段。
- `summary.md` 目前只校验元数据，不校验 HIGH/MED/LOW、通过项、无法验证项、修复方案等正文结构及 item 覆盖；空正文加正确 hash 仍可通过。
- `fixes.json` 只要求 `new` 含 `[REVIEW-FIX]`，没有要求写出其 `item_ids` 来源编号；与 synthesis 文档的可追溯要求不一致。
- `apply-inline-fixes.py` 用 `mkstemp` 候选替换 plan 时没有保留原文件 mode，会把原 plan 权限机械改成临时文件权限；幂等提前返回也未验证 backup/archive/timestamp/approved ids 完整性。
- 多轮 post-fix 再修复会覆盖单一 `fix-state.md`，而 history archive 不包含旧 fix-state；上一轮事务状态缺少独立持久化记录，审计链不完整。

## 2026-07-26 接续后的文档契约复核

- Research 的 `validate-deployment-plan.py` 已机械要求固定文件名、唯一 H1、非空成功标准、四类唯一前置检查、逐步骤字段、回滚表顺序/唯一性、不可逆补救一致性，以及权限/数据影响/依赖版本三类基础风险；主 Skill 仍只笼统写“必需章节、字段值、模板标记和 provenance”，代码与文档契约尚未完全同步。
- `find-latest-session.py` 当前 active pointer 路线要求 absolute path，但没有像 `update-session-state.py` 那样验证原字符串等于 resolve 后 canonical path；绝对但含 `..` 等非 canonical 表达仍可能被恢复。恢复指针的 canonical 不变量尚未在所有 helper 中闭合。
- Review 恢复把 `fix-state status: prepared` 与“plan 已应用、等待 post-fix”混为一谈；prepared 可能表示备份/state 已写但 plan 仍是 base hash，此时直接 `prepare-review-run --mode post-fix` 会审查旧 plan。恢复必须先幂等重跑 `apply-inline-fixes.py`，把状态推进到 `applied-awaiting-post-fix-review`。
- `prepare-review-run.py` 目前只校验 fix-state 的 status，没有验证 session/review/hash、archive manifest、backup、approval hash 与 timestamp 完整 schema；损坏 state 可能错误决定下一轮 mode。三个事务 helper 需要共享同一只读 fix-state contract，避免各自漂移。
- `validate-review-run.py` 的 summary 正文只确认预期编号“至少出现”，没有拒绝额外编号、重复编号或把同一 FAIL 同时归入多个严重度；报告明细也可在同一个小节内跨多条状态借用 detail。正文分类和每条状态明细仍需一一绑定。

## 2026-07-26 第四轮剩余 helper 静态复审

- `prepare-review-run.py` 先把 invalid bundle 全部移动到 orphan 目录，再创建 `validation-error.txt`；若错误说明写入失败，helper 返回失败但当前 bundle 已被移走，缺少回滚或“先写说明再移动”的事务顺序。
- `verify-plan-provenance.py` 只在调用 Research provenance generator 前读取 live plan 与 snapshot；generator 运行期间若 plan/snapshot 漂移，仍可能输出 `confirmed`。应在生成后重读并确认两个 hash 仍等于 expected，再持久化结果。
- `hash-plan-locator.py` 等小 helper 对输入先 `resolve()`，随后再检查 `review_dir.is_symlink()` / `session_dir.is_symlink()`；resolved 对象已无法反映原始父路径是否为 symlink。需要在 resolve 前检查 lexical session/review 父级，或明确只接受 canonical 输入并机械拒绝别名路径。
- `new-review-run-id.py` 遇到 symlink `_run.md` 时会把它当作“无当前 run”而继续生成 ID；虽然 prepare 主流程会先退休 invalid bundle，helper 独立调用时仍应拒绝可疑父状态，避免生成与未解析当前 run 冲突的标识。
- `heavy-review/references/subagent-source.md` 只描述 source snapshot 非 confirmed 时的判定闸门，没有说明 snapshot 实际绑定 Git HEAD/porcelain、tracked 与未忽略 untracked 的内容、文件类型和可执行位；与主 `SKILL.md` 的机械契约不完整同步。
- 双语 README 已有 post-fix 回环，但核心契约未提示 `fix-state status: prepared` 不能直接开始 review、必须幂等续跑 apply helper；作为工作流总览容易把 prepared 误解成已应用状态。
- `validate-deployment-plan.py` 在验证 `research/` 是 session 内真实目录之前先用 `Path.read_text()` 读取 `research/summary.md`，会跟随 summary 或父目录 symlink；边界检查顺序应前移，并统一使用 no-follow 普通文件读取。
- deployment-plan validator 在第一次 plan 稳定性复核后才运行第二次 provenance generator，但第二次 generator 返回后未再读取 plan；plan 若在末次 provenance 复核期间漂移，仍可能返回成功。最终返回前必须同时再确认 plan bytes 与两次 provenance 输出稳定。
- `fix_state_contract.py` 尚未从 archived `plan-snapshot.md` 与 `fixes.json` 顺序重放 replacements，也未把 state 的 `candidate_plan_sha256`、`applied_replacements`、`approved_item_ids` 与 archived approval/fixes 机械对账。若 state candidate hash 与 live plan 被一起篡改，`apply-inline-fixes.py` 的幂等分支可能误报 already-applied。
- `validate-review-run.py` 把固定的 `session/deployment-plan.md` 和 `review/plan-snapshot.md` 先 `resolve()` 再 no-follow 读取；原路径若是指向 session 外的 symlink，resolved 目标会失去 symlink 证据，并可被伪造 `_run.md` canonical path 绑定。必须直接校验固定 lexical 路径为普通文件，不能先跟随 symlink。
- Review validator 先验证 `web.md` / `source.md`，随后又重新读取当前文件计算 summary hash；若文件在两次读取之间变化，summary 可能绑定未被验证的新 bytes。summary/fixes 与 PASS mark/decision 也缺少由 validator 返回的精确已验证 hash，存在 TOCTOU。应让 validator 对单次读取数据完成验证/聚合/hash，并在返回前做稳定性复核。
- `capture-source-snapshot.py` 对普通 tracked/untracked 文件已绑定内容、类型和可执行位，但 tracked gitlink/submodule 只会被当成目录类型；submodule 已 dirty 后，内部内容继续变化时顶层 porcelain 状态可能仍相同，snapshot hash 不一定变化。clean submodule 应绑定 index object 与实际 HEAD；dirty、缺失或无法检查的 submodule 应降级为 unverifiable。

## 2026-07-26 第五轮修复后复审

- 26 项行为回归、19 个 helper 内存 compile、`pyflakes` 与 `git diff --check` 均通过。
- 少数边缘 helper 仍保留“先检查 `is_symlink()`，再调用 `Path.read_text()` / `read_bytes()`”的两步读取；检查与打开之间可被替换，和主契约的 `O_NOFOLLOW` 普通文件读取语义不一致。应统一替换为共享/本地 no-follow reader。
- `fix_state_contract.py` 的 `verified` 分支只验证 `post_fix_review_run_id` / `post_fix_summary_sha256` 格式，尚未从当前根 bundle 或 `review/history/<post_fix_run_id>/` 证明该 run 是 mode=post-fix、审查 candidate hash 且 summary verdict=pass；手工把 applied state 改写为 verified 可能被接受。
- Heavy Review 的 legacy 判定只看 `research/` 或 `_state.md` 是否缺失；一个已经带现代 `## Workflow Provenance`、但 state 被删除的损坏 session 也会被当作 legacy。只有缺 state 且 plan 不含 provenance 章节的旧格式才能机械认定为 legacy。

## 2026-07-26 第六轮特殊文件边界复审

- 28 项行为回归和 19 个 helper 内存 compile 已通过，新增的现代 provenance plan 缺 state 拒绝用例正常通过。
- 纯未跟踪 FIFO 不会被 `git ls-files --others --exclude-standard` 枚举，不会进入 source snapshot；但已跟踪普通文件被 FIFO 替换后仍位于 index 路径集合，Git porcelain 会报告工作区修改，而当前 `capture-source-snapshot.py` 仅按特殊节点类型生成 payload 并错误返回 `confirmed`。
- FIFO、socket、block/character device 等特殊节点没有可稳定、非阻塞读取的源码内容；只绑定节点类型不足以证明当前可审查源码状态。任何 Git-visible 路径解析为此类节点时，source snapshot 应降级为 `unverifiable`，并由既有 synthetic item 闸门禁止相关源码项 PASS。
- `find-latest-plan.py` 在候选扫描后重新调用 `state_kind(latest)` 但不检查结果；若 state 在两次读取间漂移，helper 可返回成功却输出 `SESSION_STATE=None`，首次扫描后出现的更晚 complete session 也可能被漏选。发现阶段应对“最新 canonical session + state kind”做有界双扫描稳定性确认；plan bytes 仍由紧随其后的 `capture-plan.py` 作为最终信任边界。
- `verify-plan-provenance.py` 对 `--research-script` 先调用 `resolve()` 再检查 `is_symlink()`，因此最终脚本 symlink 会被静默跟随，检查永远无法看到原始路径证据。应先检查 lexical 路径，再解析并要求目标为普通文件；生产 validator 仍使用仓库内固定 Research helper 路径。
- `find-latest-session.py` 的 fallback 与 Review discovery 有同类漂移窗口：单次扫描后直接把 latest 写回 `.active-session`，未证明候选在选择/写指针期间仍是同主题 `in_progress` session。应双扫描稳定候选，并在原子写回后复核 pointer 与 session；若失效则只清理自己刚写入且仍匹配的 pointer 后失败。
- fix-state 内容/hash/schema 已对齐，但时间审计仍只验证各字段可解析，并仅约束 `verified_at >= applied_at`；尚未机械证明 `summary.summarized_at <= approval.approved_at <= prepared/applied_at <= post-fix summary.summarized_at <= verified_at`。倒序时间不会伪造内容，却会形成自相矛盾的审计链，应由共享契约拒绝。
- Review validator 虽在最外层捕获 `ContractError/OSError/UnicodeError`，但对 `provenance.json` 的 `json.loads` 结果未先要求 object 就直接 `.get()`；合法 JSON array/string 会触发未捕获 `AttributeError` 和 traceback。所有外部/文件 JSON 在字段访问前都必须机械校验顶层 shape。
- Review 证据时间只对 time-sensitive Web 做 TTL/future 检查；`created_at`、stable Web、source route 和 summary 仅验证可解析。这样旧报告可伪装成本轮产物，summary 也可早于报告或位于未来。机械时间链应为 `source snapshot <= run created_at <= web/source evidence_captured_at <= summary.summarized_at <= validation now`，time-sensitive Web 另受 TTL 上限约束。
- `capture-source-snapshot.py` 在 Linux 上把 Git 路径中的字面 `\` 替换成 `/`；根目录 Git-visible 文件 `.workflows\visible.txt` 因而被误判为 `.workflows/` 内文件并排除。隔离复现中 Git 能枚举该文件，但 snapshot `file_count` 未包含它且内容变化 hash 不变。Ubuntu/Linux helper 必须保留 Git 返回的 POSIX 路径原文，只排除真实 `.workflows` 与 `.workflows/` 前缀。
- 12 个 no-follow reader 使用 `O_RDONLY | O_NOFOLLOW`；若目标在检查与 `open()` 间被替换成 FIFO，Linux 的只读 FIFO open 可永久等待 writer，`fstat` 永远无法执行。统一增加 `O_NONBLOCK` 对普通文件无行为影响，却能让 FIFO/特殊节点立即进入类型拒绝路径。
- `archive-review-run.py` 只用 `target.exists()` 判断 history run 是否占用；悬空 symlink 返回 false，最终 `os.rename(temp_dir, target)` 会替换该 symlink。`new-review-run-id.py` 也会把 broken symlink 当成可用 ID。所有审计目标必须用 `exists() or is_symlink()` 占用语义，发现 symlink 后拒绝而非覆盖。
- 写入异常仍有未收口路径：`capture-plan.py` 的 snapshot `open/replace`、`ensure-review-dir.py` 的 `mkdir()` 可直接抛 OSError traceback；多个 `finally` 中的 unguarded temp unlink/rmtree 还可能遮蔽原始写入错误。所有 helper 必须把预期文件系统失败转换为受控错误，并让 cleanup 错误作为附加信息而非新 traceback。

## 2026-07-26 第七轮最终复审结论

- 已完成写入异常收口：snapshot、pointer、state、approval、archive、backup 和 candidate plan 的写入失败均走受控错误；cleanup 失败作为附加诊断，不再覆盖原始异常。
- `record-review-decision.py` / `archive-review-run.py` 已补 lexical session symlink 拒绝；CLI 外围路径解析、Git 探测和 helper 子进程启动失败也不会产生 traceback。
- valid review bundle 清理中断后，只要完整 history 仍可信，prepare 可以用 manifest 精确验证当前剩余文件并幂等完成退休；`_run.md` 最后删除，保证失败重试仍能定位 run identity。
- history 可信性不能只验证 manifest 已列文件的 hash；目录中额外注入文件同样构成篡改。archive、prepare、base fix-state 和 post-fix verified binding 已统一要求目录项与 manifest 精确相等。
- 自动化回归最终为 37/37 pass，仓库源两个 Skill 均通过 quick_validate，19 个 helper 内存 compile、pyflakes 与 `git diff --check` 均通过。
- 最后一轮按相同标准扫描未发现新的逻辑问题、逻辑谬误或状态闭环缺口；下一信任边界是本机重新装载后的源/安装一致性与远端 commit 核验。

## 2026-07-27 Heavy Workflows 双宿主重新部署与验收

- 当前状态审计发现 Codex 的 `~/.agents/skills/heavy-research` / `heavy-review` 均为过期副本，缺少多项当前生产 helper；Claude Code 的两个全局路径也均不存在。仓库源 `projects/agent-workflows/skills/` 为当前权威版本。
- 已使用受控 `rsync --delete` 将两个仓库源目录同步到 Codex 全局实体目录；随后新建 Claude Code 全局 symlink，分别指向对应的 `.agents` 实体目录。两端共用同一份可验证内容，避免后续双副本漂移。
- 验收结果：完整 `unittest` 工作流契约回归 37/37 通过；源目录与安装目录的 `quick_validate.py` 共 4/4 通过；两个源/安装目录 `diff -qr` 无差异；安装 helper 内存编译通过，未产生 `__pycache__` / `.pyc`；`git diff --check` 通过。
- Codex `debug prompt-input` 已列出两个 Skill 并指向 `~/.agents/skills` 当前文件；真实只读精确触发探针进入 Heavy Research 阶段 A，正确要求调研澄清和可写工作区，未启动联网或写入。Claude Code 能沿 symlink 读取两份 `SKILL.md`，其正常 TTY 界面接受 `/heavy-research` Slash Skill；非交互模式的 Slash 调用不稳定，不作为功能失败判据。
- `tvly --status` 显示已通过 API key 认证，满足 Heavy Research 的 approved web-search fallback。初检时 `brv` CLI 不在本机；后续已从 npm 恢复历史一致的 `byterover-cli` 3.16.1，并用官方 SHA-256 已验证的用户级 Node 24.13.1 专用 wrapper 运行。`brv --version`、`brv query --help` 和 `brv status` 均通过；当前仓库的 context tree 仍未初始化，未在本轮越权初始化它。
- npm 安装 `byterover-cli` 时报告 35 个依赖漏洞（18 low、5 moderate、12 high）；未运行可能改变依赖树的 `npm audit fix`，应在独立的依赖维护任务中评估升级路径。
- 首次记录进度提交因本仓与全局都未配置 Git 作者身份而被 Git 拒绝，未生成 commit。核对最近五个提交后确认它们均使用 `kevinlasnh <kevinlasnh@users.noreply.github.com>`，已仅在当前仓库恢复同一身份后重试。
