# 发现

## 2026-08-16 仓库改造为个人 AI 使用生态

- 全局 skills 实体目录共 10 个，总量约 1MB；其中 `skill-creator` 携带上游 Apache-2.0 `LICENSE.txt` 与 eval 资产（`agents/` 三个子 agent、`assets/eval_review.html`），收录时保留。
- `~/.claude/skills/` 现有 3 个 symlink（heavy-research / heavy-review / obsidian-markdown）指向 `~/.agents/skills/` 实体目录，符合"Claude Code 通过 symlink 复用 Codex 实体"的部署布局。
- 全局 skills 敏感扫描结果：无真实 API key、无本机路径泄漏；`skill-creator/scripts/improve_description.py` 中的 `ANTHROPIC_API_KEY` 只是"复用会话鉴权、无需单独 key"的文档说明。
- `git mv` 迁移保留了 `global/` 两份镜像与 heavy skills 的文件历史；删除旧项目采用增量 `git rm`，整体历史未重写。
- 复制全局 skill 时会带入 `__pycache__` 缓存（本机运行时产物），已在收录时删除并通过 `.gitignore` 的 `__pycache__/` 规则长期防护。
