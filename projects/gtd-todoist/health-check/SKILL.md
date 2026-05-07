---
name: gtd-todoist-health
description: Read-only audit for a GTD-over-Todoist agent harness. Use when verifying that the GTD AGENTS section, three GTD workspace skills (gtd-inbox-triage, gtd-daily-review, gtd-weekly-review), reminder-only cron jobs, and Todoist scaffold stay consistent with the deployment plan in this repo. Does not read real task content.
---

# GTD Todoist Health

## Overview

Use this skill to audit a live GTD-over-Todoist agent harness without reading the user's real Todoist task content. The audit covers:

- the `AGENTS.md` GTD section
- three GTD workspace skills
- reminder-only cron jobs
- runtime skill visibility
- optional Todoist scaffold name drift

## Scope Guard

- Target is an agent runtime host reachable over SSH and a workspace directory (e.g. `~/.openclaw`). Both are passed in at invocation time; nothing is hard-coded.
- Always run read-only checks.
- Do not restart the agent runtime, edit files, disable cron, clear sessions, or mutate Todoist during a health check.
- Do not run `td inbox`, `td today`, or `td task list` by default.
- Treat Todoist scaffold inspection as opt-in only. Use `-IncludeTodoistScaffold` only when the user explicitly wants scaffold verification and still avoid task content.
- Do not inspect other agent profiles unless the user explicitly changes scope.

## Workflow

1. Read local project context before touching the server:
   - `AGENTS.md`
   - any local planning or findings notes
2. Run the wrapper from the repository root:

   ```powershell
   .\scripts\run-gtd-health.ps1 -HostName "<user>@<host>" -StateDir "~/.openclaw"
   ```

3. If the wrapper is unavailable, stream the probe script over SSH directly:

   ```powershell
   Get-Content -Raw -Encoding UTF8 .\scripts\gtd_health_check.sh | ssh <user>@<host> "tr -d '\r' | bash -s"
   ```

4. Interpret the output by layers:
   - P0: main state, workspace files, `openclaw config validate` (or your runtime's equivalent)
   - P1: `AGENTS.md` GTD contract
   - P1: three GTD workspace skills and runtime visibility
   - P1: five GTD reminder-only cron jobs
   - P2: stale scaffold residue, unsafe Todoist command examples, optional Todoist scaffold drift
   - P2: manual semantic GTD review that deterministic scans cannot prove
5. Report with:
   - Overall status: `clean`, `issues`, or `residual-risk`
   - Blocking red flags
   - Evidence by layer
   - Manual GTD semantic review notes
   - Recommended next action

## Required Checks

Always include these checks:

- `<workspace>/AGENTS.md` exists.
- These workspace skills exist:
  - `gtd-inbox-triage`
  - `gtd-daily-review`
  - `gtd-weekly-review`
- The agent runtime config validates (e.g. `openclaw config validate`).
- Runtime skill visibility shows all three GTD skills as `eligible=true`, `modelVisible=true`, `commandVisible=true`, and sourced from the workspace.
- `AGENTS.md` includes GTD Capture, Clarify, Organize, Reflect, Engage.
- GTD mutation rules require `id:<task_id>` or Todoist URL and warn that `td task update --labels` replaces all labels.
- GTD skills require proposal / confirmation before mutation.
- `gtd-inbox-triage` covers clarify classification, waiting-for, project routing, hard due dates, label preservation, and MIT confirmation.
- `gtd-daily-review` covers hard landscape, no soft-date drift, label preservation, and closing suggestions.
- `gtd-weekly-review` covers Get Clear, Get Current, Get Creative, Next Actions, Waiting For, Someday/Maybe, and Horizons.
- Five GTD cron jobs are reminder-only:
  - `gtd-inbox-reminder-0900`
  - `gtd-inbox-reminder-1300`
  - `gtd-inbox-reminder-1900`
  - `gtd-daily-review-reminder-2200`
  - `gtd-weekly-review-reminder-sun-1315`
- Each GTD cron is `enabled=true`, `sessionTarget=isolated`, `delivery.mode=announce`, delivery target matches the configured Telegram user / bot, `payload.thinking=off`, `payload.lightContext=true`, `payload.toolsAllow=["read"]`, and `payload.timeoutSeconds` within a safe window (default 600).
- Stale scaffold scans find no invalid `td` mutation examples and no soft-date drift.

## Manual Semantic Review

The script provides evidence, not the final judgment. After running it, manually review whether:

- Clarify still means deciding what an item is before organizing it.
- Calendar dates are reserved for hard landscape items, not wishful "do this someday" dates.
- Reference is treated as non-actionable material, not as an orphaned task bucket.
- Waiting For items include who, what, and follow-up context.
- Projects are multi-step outcomes with at least one next action.
- Weekly Review reviews the whole action system, not only projects.
- Engage recommendations are limited and context-aware, not a raw task dump.
- The harness avoids automated GTD decisions from cron and keeps user discussion in the main chat session.

## Optional Todoist Scaffold Check

Use only when the user explicitly asks to include Todoist scaffold, and do not inspect task content:

```powershell
.\scripts\run-gtd-health.ps1 -HostName "<user>@<host>" -IncludeTodoistScaffold
```

This checks only the project, label, and filter **names** expected by the GTD scaffold defined in `../deployment-plan.md`.

## Clean Standard

Report `clean` only when all required checks pass, the script exits cleanly, and the manual semantic review finds no contradictions. Report `residual-risk` when deterministic checks pass but semantic uncertainty remains. Report `issues` when any required check fails.

## Fix Policy

- Apply no fixes during the first health pass.
- For mechanical fixes, propose exact files and changes first.
- For live workspace changes, back up remote files before editing and validate after editing.
- Restart the agent runtime only when a workspace or config change needs to be loaded, and only after the user asks for the fix.

## Resources

- `scripts/run-gtd-health.ps1`: Windows wrapper that finds `gtd_health_check.sh`, sends it to the remote host over SSH, and runs it read-only.
- `scripts/gtd_health_check.sh`: remote read-only GTD harness probe.
