# 任务计划：仓库改造为个人 AI 使用生态

## 目标
将 sharing-studio 仓库改造为个人 AI 使用生态：收录全局 agent markdown 脱敏镜像与全部全局 agent skills，重写仓库定位文档。

## 当前阶段
阶段 1

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
- **状态：** in_progress

## 已做决策
| 决策 | 理由 |
|------|------|
| 仓库保持公开 | 用户确认；全局规则继续使用 `<second-brain-path>` / `<your-username>` 占位符脱敏 |
| 旧 `projects/` 五个项目全部删除 | 用户确认；内容保留在 Git 历史中可回溯 |
| 保留现有 Git 历史 | 用户确认；采用增量提交，不重开历史 |
| 不需要部署脚本 | 用户确认；仓库以收录为主，本机部署保持手动 |
| PWF 收口后清空重开 | 用户确认；旧任务记录进入历史，新仓库从空白任务记忆开始 |
| 根 `AGENTS.md` / `CLAUDE.md` 放开跟踪 | 用户确认；重写为不含本机信息的公开安全仓库规则 |

## 备注
- 不记录任何 API key 或本机专属路径。
- 同步约定：全局 skill 本地改动 → 更新 `skills/` 副本；全局规则改动 → 同步更新 `global/` 两份镜像。
- 合并远端 `origin/master`（`53527ae`）时，其 2026-08-12 新增的 Code Comments 全局规则已自动并入 `global/` 两份镜像（字节一致）。
