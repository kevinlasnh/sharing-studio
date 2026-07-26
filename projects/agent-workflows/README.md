# agent-workflows

Heavy research and review skills for deployment plans that need evidence, traceability, and a human approval gate.

<p>
  <img alt="Heavy research" src="https://img.shields.io/badge/heavy-research-0f766e?style=flat-square">
  <img alt="Heavy review" src="https://img.shields.io/badge/heavy-review-7c3aed?style=flat-square">
  <img alt="File backed" src="https://img.shields.io/badge/evidence-file--backed-2563eb?style=flat-square">
</p>

<!-- README-I18N:START -->
<p>
  <strong>English</strong> | <a href="./README.zh-CN.md">简体中文</a>
</p>
<!-- README-I18N:END -->

> [!NOTE]
> This project publishes the workflow skills and redacted contracts only. Real `.workflows/` sessions and private deployment evidence must not be published. Repository planning files follow the target repository's Agent Markdown, `.gitignore`, sensitivity rules, and explicit user authorization rather than a universal "never commit" rule.

## What It Solves

Complex deployments often fail because research, source evidence, risk review, and user approval are scattered across chat history. These skills force that work into explicit files, hashes, run IDs, and review gates.

## What's Included

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

| Skill | Trigger | Role | Output |
| :--- | :--- | :--- | :--- |
| `heavy-research` | `准备开始进行重型调研` / `准备开始进行 Heavy Research` | Planner | `.workflows/<session>/deployment-plan.md` |
| `heavy-review` | `准备开始进行重型审查` / `准备开始进行 Heavy Review` | Reviewer | Inline fixes back into the same deployment plan after user approval |

## Workflow

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
  M -->|Approve| N[Transactional inline fixes]
  N --> O[New plan/source/provenance snapshots]
  O --> P[Full post-fix review with a new review_run_id]
  P --> K
```

## Core Contracts

- Both skills trigger only on exact phrases.
- File contracts are the source of truth; chat summaries are not.
- Research reports are tied to `run_id`; stale reports are ignored.
- Review reports are tied to `review_run_id` and `plan_sha256`; old reports cannot be reused after the plan changes.
- Source-code research is included only when `_run.md` explicitly enables `source`.
- Review routes bind a safe summary to exact plan bytes through `statement_sha256` and `plan_locator`, plus route, risk, and freshness fields.
- Review aggregation treats `FAIL > UNVERIFIABLE > PASS`; unverified work never silently passes.
- Review summaries, exact fix specifications, and user decisions are persisted and hash-bound.
- `fix-state: prepared` is not proof that the plan was changed; resume the transactional apply helper idempotently before any post-fix review.
- An inline fix never ends the workflow: the modified plan must pass a new full review before the fix state becomes verified.

## Dependencies

- An agent runtime that can read local skills and write repository files.
- Web search/fetch tooling for the web route.
- Local read/search tooling for source routes.
- Optional ByteRover/PWF context for memory-backed research.

## Privacy Boundary

Do not publish:

- Real `.workflows/` session directories.
- Real deployment plans or review reports from private projects.
- Project-specific source excerpts that are not already public.
- Local planning files or ByteRover context trees unless the target repository explicitly requires them to be tracked and they have passed sensitivity checks.
