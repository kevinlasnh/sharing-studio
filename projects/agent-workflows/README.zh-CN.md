# agent-workflows

面向部署方案的重型调研和重型审查 skills，用文件证据、可追踪契约和人工批准闸门提高可靠性。

<p>
  <img alt="Heavy research" src="https://img.shields.io/badge/heavy-research-0f766e?style=flat-square">
  <img alt="Heavy review" src="https://img.shields.io/badge/heavy-review-7c3aed?style=flat-square">
  <img alt="File backed" src="https://img.shields.io/badge/evidence-file--backed-2563eb?style=flat-square">
</p>

<!-- README-I18N:START -->
<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong>
</p>
<!-- README-I18N:END -->

> [!NOTE]
> 本项目只发布工作流 skills 和脱敏契约。真实项目中的 `.workflows/` session、部署计划、审查报告和本地 planning 文件都留在 Git 之外。

## 解决什么问题

复杂部署经常失败，是因为调研、源码证据、风险审查和用户确认散落在聊天历史里。这两个 skills 会把这些工作固化到明确的文件、hash、run ID 和 review gate 中。

## 包含内容

```text
agent-workflows/
└── skills/
    ├── heavy-research/
    │   ├── SKILL.md
    │   ├── references/
    │   └── scripts/
    └── heavy-review/
        ├── SKILL.md
        ├── references/
        └── scripts/
```

| Skill | 触发词 | 角色 | 输出 |
| :--- | :--- | :--- | :--- |
| `heavy-research` | `准备开始进行重型调研` | Planner | `.workflows/<session>/deployment-plan.md` |
| `heavy-review` | `准备开始进行重型审查` | Reviewer | 用户批准后 inline 修复同一份部署计划 |

## 工作流

```mermaid
flowchart TD
  A[Clarify target and constraints] --> B[heavy-research]
  B --> C[_run.md + run_id]
  C --> D[web / memory / optional source reports]
  D --> E[Validated research summary]
  E --> F{User accepts summary or key gaps?}
  F -->|No| A
  F -->|Yes| G[deployment-plan.md]
  G --> H[heavy-review]
  H --> I[_run.md + review_run_id + plan_sha256]
  I --> J[web / source evidence reports]
  J --> K{FAIL or UNVERIFIABLE?}
  K -->|No| L[Plan passes heavy review]
  K -->|Yes| M[User reviews fix proposal]
  M -->|Reject| H
  M -->|Approve| N[Inline fixes into deployment-plan.md]
```

## 核心契约

- 两个 skills 只响应精确触发词。
- 文件契约是真源；聊天摘要不是。
- 调研报告绑定 `run_id`；陈旧报告会被忽略。
- 审查报告绑定 `review_run_id` 和 `plan_sha256`；计划变更后旧报告不能复用。
- 只有 `_run.md` 显式启用 `source` 时，才纳入源码调研。
- 审查路线通过 `statement`、`evidence_route`、`risk_dimensions`、`risk_hint` 字段化。
- 审查聚合遵守 `FAIL > UNVERIFIABLE > PASS`；无法验证的工作不会被静默当作通过。

## 依赖

- 能读取本地 skills 并写入仓库文件的 agent 运行时。
- 用于 web 路线的 Web search/fetch 工具。
- 用于 source 路线的本地 read/search 工具。
- 可选的 ByteRover/PWF 上下文，用于记忆支撑的调研。

## 隐私边界

不要发布：

- 真实 `.workflows/` session 目录。
- 私有项目的真实部署计划或审查报告。
- 尚未公开的项目源码摘录。
- 本地 planning 文件或 ByteRover context tree。
