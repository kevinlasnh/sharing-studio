# 发现

## 2026-08-12 全局规则新增：代码修改自适应中文注释

- 决策：全局 agent markdown 的 `Interaction Defaults` 新增 `Code Comments` 规则——编写或修改代码时必须根据本次修改内容自适应添加详细中文注释（改了什么、为什么、影响范围），避免模板化或空泛注释。
- 动因：用户人工阅读代码时需要理解 agent 每次改动的意图，仅靠简短注释难以看懂。
- 同步：新增规则同时写入本机全局 `~/.claude/CLAUDE.md` / `~/.codex/AGENTS.md` 与 sharing 镜像两份；本机全局与镜像保持仅两处脱敏占位符差异。

## 2026-08-16 仓库改造为个人 AI 使用生态

- 全局 skills 实体目录共 10 个，总量约 1MB；其中 `skill-creator` 携带上游 Apache-2.0 `LICENSE.txt` 与 eval 资产（`agents/` 三个子 agent、`assets/eval_review.html`），收录时保留。
- `~/.claude/skills/` 现有 3 个 symlink（heavy-research / heavy-review / obsidian-markdown）指向 `~/.agents/skills/` 实体目录，符合"Claude Code 通过 symlink 复用 Codex 实体"的部署布局。
- 全局 skills 敏感扫描结果：无真实 API key、无本机路径泄漏；`skill-creator/scripts/improve_description.py` 中的 `ANTHROPIC_API_KEY` 只是"复用会话鉴权、无需单独 key"的文档说明。
- `git mv` 迁移保留了 `global/` 两份镜像与 heavy skills 的文件历史；删除旧项目采用增量 `git rm`，整体历史未重写。
- 复制全局 skill 时会带入 `__pycache__` 缓存（本机运行时产物），已在收录时删除并通过 `.gitignore` 的 `__pycache__/` 规则长期防护。
- 合并远端 `origin/master` 时，Git 正确识别了 rename/modify：远端 08-12 对旧路径 `projects/agent-memory-stack/global/` 的 Code Comments 修改自动合并到新路径 `global/`，两份镜像仍逐字节一致；PWF 三件套因双方重写产生冲突，已以本地重开版为基础解决并补记远端摘要。
