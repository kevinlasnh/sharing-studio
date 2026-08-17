# 任务计划：仓库改造为个人 AI 使用生态

## 目标
将仓库（kevin-AI-studio）维护为个人 AI 使用生态中心：收录全局 agent markdown 脱敏镜像与全部全局 agent skills，并提供 eco-sync skill 实现多设备双向同步。

## 当前阶段
阶段 4

## 各阶段

### 阶段 1：仓库改造与内容收录
- [x] 收口旧 PWF 三件套未提交修改（commit `f273698`）
- [x] 全局规则脱敏镜像收录到 `global/`（与远端 `2d60470` 内容一致）
- [x] 10 个全局 skills 收录到 `skills/`，逐目录校验与全局副本完全一致
- [x] 删除五个旧 `projects/` 项目（gtd-todoist / second-brain-scaffold / agent-memory-stack / sharing-studio-sync / agent-workflows）
- [x] 重写根 `AGENTS.md` / `CLAUDE.md` 为公开安全的个人生态仓库规则，并从 `.gitignore` 放开跟踪
- [x] 重写 `.gitignore`（保留 secrets 与运行时目录规则、新增 Python 缓存规则）与 `.gitattributes`（补充 `.py` / `.sh`）
- [x] 重写双语 README 为个人 AI 使用生态定位
- [x] 清空重开 PWF 三件套
- [ ] 清理 `.workflows/` 运行产物，全仓敏感扫描，提交并 push
- **状态：** complete

### 阶段 2：上游重命名、全局规则收敛与 eco-sync 双向同步 skill
- [x] `gh repo rename` 把 GitHub 上游从 `sharing-studio` 重命名为 `kevin-AI-studio`，更新本地 remote URL 并验证
- [x] 收敛全局规则为「三宿主 + Code Comments」版：本机三份（Claude / Codex / DSH）与仓库三份镜像（`global/CLAUDE.md`、`global/AGENTS.md`、`global/AGENTS.dsh.md`）各自字节一致
- [x] 更新仓库内引用：双语 README（标题、三份镜像结构、同步模型）、LICENSE 版权行、根 `AGENTS.md`/`CLAUDE.md` 的 global/ 描述
- [x] 编写 `skills/eco-sync`：SKILL.md + `scripts/sync.py`（status / push / pull 三模式，三路冲突检测、脱敏渲染、安全扫描、快进 pull）
- [x] 部署 eco-sync 到 `~/.agents/skills/` 并创建 `~/.claude/skills/` symlink，宿主已识别
- [x] 修复 hash 口径 bug（git show 用字节口径，避免 universal newlines 转换造成全量误报）
- [x] 测试 status：仅剩本会话的 5 项真实差异，其余 skill 全部一致
- [x] 提交全部改动并 push 到新远端 `origin/master`
- [x] 重命名本地目录为 `kevin-AI-studio` 并更新 `.brv/config.json` cwd
- [x] 最终验证：status 全量一致 + push dry-run 无变更
- **状态：** complete

### 阶段 3：eco-sync 转为仓库级 skill
- [x] 修改 `sync.py`：移除 `--repo` 参数，改为从当前目录向上定位 git 仓库根并验证身份（remote origin 含 kevin-AI-studio 或目录名匹配），其他仓库/目录拒绝执行
- [x] 更新 `SKILL.md`：标注仓库级、新用法（`.agents/skills/eco-sync/scripts/sync.py`）、新设备部署步骤
- [x] 在仓库内创建 `.agents/skills/eco-sync` 与 `.claude/skills/eco-sync` 两份未跟踪运行时实体副本（与权威源 `skills/eco-sync` 逐字节一致）
- [x] 删除全局部署 `~/.agents/skills/eco-sync` 与 `~/.claude/skills/eco-sync` symlink，宿主全局技能目录已确认移除 eco-sync
- [x] 修复设计矛盾：`compare_skills` 排除 eco-sync 自身，避免 pull 把它复制回设备全局目录、push --prune 删除仓库权威源
- [x] 验证：仓库内 `status` 输出「生态副本完全一致」；仓库外运行被拒绝退出
- [x] 更新双语 README（skills 表格加 eco-sync 并标注仓库级、布局树、新设备部署说明）与根 `AGENTS.md`/`CLAUDE.md` Sync Conventions
- **状态：** complete

### 阶段 4：把最新生态部署到本机
- [x] 部署 eco-sync 仓库级运行时副本到 `.agents/skills/eco-sync`（Codex）与 `.claude/skills/eco-sync`（Claude Code），与权威源逐字节一致
- [x] 修复 `sync.py` vault 提取正则：按反引号/空白/斜杠边界截取完整目录名，修复带后缀 vault（如 second-brain-private）被截断的 bug
- [x] 渲染仓库三份镜像为本机值（磁盘实况 vault + username）写入三宿主：更新 `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`，新建 `~/.dsh/AGENTS.md`
- [x] 同步 10 个全局 skills 到 `~/.agents/skills`（清理设备端 `__pycache__`）并补全 `~/.claude/skills/` 至 10 个 symlink
- [x] 验证：三宿主规则逐字节一致、skills 全部 identical、`sync.py status` 输出「生态副本完全一致，没有差异」
- [x] 更新 PWF 三件套并 commit + push 到 `origin/master`
- **状态：** complete

## 已做决策
| 决策 | 理由 |
|------|------|
| 仓库保持公开 | 用户确认；全局规则继续使用 `<second-brain-path>` / `<your-username>` 占位符脱敏 |
| 旧 `projects/` 五个项目全部删除 | 用户确认；内容保留在 Git 历史中可回溯 |
| 保留现有 Git 历史 | 用户确认；采用增量提交，不重开历史 |
| 不需要部署脚本 | 用户确认；仓库以收录为主，本机部署保持手动 |
| PWF 收口后清空重开 | 用户确认；旧任务记录进入历史，新仓库从空白任务记忆开始 |
| 根 `AGENTS.md` / `CLAUDE.md` 放开跟踪 | 用户确认；重写为不含本机信息的公开安全仓库规则 |
| eco-sync 支持双向 push+pull | 用户确认；多设备间生态变动需要互通，任何设备都可先拉最新再推自己改动 |
| 保留 Code Comments 规则并收敛为三宿主版 | 用户确认；本机三份与仓库镜像统一为「三宿主 + Code Comments」 |
| `global/` 平铺三份镜像（含 `AGENTS.dsh.md`） | 用户确认；与设备端文件名一一对应最直观 |
| 本地目录名一并改为 `kevin-AI-studio` | 用户确认；与上游仓库名保持一致，需同步更新 `.brv` cwd |
| eco-sync 改为仓库级 skill | 用户确认；只允许在 kevin-AI-studio 仓库内改动 AI 生态副本，全局部署已移除 |
| 部署渲染的 vault 值以磁盘实况为准 | `/home/kevinlasnh/Documents/second-brain` 目录实际存在且 vault 自身规则引用一致；旧全局规则文件中的 `second-brain-private` 是 08-12 陈迹（vault 已改名），不沿用 |

## 备注
- 不记录任何 API key 或本机专属路径。
- 同步约定：全局 skill 本地改动 → 更新 `skills/` 副本；全局规则改动 → 同步更新 `global/` 两份镜像。
- 合并远端 `origin/master`（`53527ae`）时，其 2026-08-12 新增的 Code Comments 全局规则已自动并入 `global/` 两份镜像（字节一致）。
