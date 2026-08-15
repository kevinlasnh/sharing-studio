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

## 2026-08-16 上游重命名、规则收敛与 eco-sync

- 本机全局规则已升级为「三宿主」措辞（Claude Code / Codex / DSH 三份必须一致），但 08-12 添加的 Code Comments 规则当时只写入了双宿主镜像，本机三份反而缺失；收敛动作以本机三宿主版为基础补回 Code Comments，两边各取所长，避免丢失任一改动。
- 本机三份宿主规则与仓库三份镜像的对应关系：设备端 `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md`、`~/.dsh/AGENTS.md` 三份字节一致；仓库端 `global/CLAUDE.md`、`global/AGENTS.md`、`global/AGENTS.dsh.md` 三份字节一致，与本机版仅差占位符渲染（本机值 ↔ `<second-brain-path>` / `<your-username>`）。
- eco-sync 的三路比较基线是 pull 前后的两个 HEAD：只有「设备改过 + 仓库在 pull 中也改过」才判 CONFLICT，避免单基线比较静默覆盖远端改动；删除语义默认关闭（--prune 才删），防止多设备互删。
- Python `subprocess.run(text=True)` 会对 git show 输出做 universal newlines 转换，导致仓库侧 hash 与设备端原始字节不一致、status 全量误报 PUSH；hash 计算必须用字节口径（`stdout=PIPE` 无 text），规则文件文本渲染才用文本口径。
- eco-sync 本机值不硬编码：从任一宿主规则文件的 Path Guard 行正则提取 vault 路径、推导用户名，公开仓库内零本机信息，同一脚本在多设备通用。
