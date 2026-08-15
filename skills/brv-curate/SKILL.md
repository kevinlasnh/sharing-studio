---
name: brv-curate
description: Curate PWF task knowledge into ByteRover long-term repository memory via brv curate. Use when the user says 沉淀长期记忆 or explicitly requests brv curate; follow the L2 to L3 sedimentation flow and protect PWF files on failure.
---

# BRV Curate

## Overview

Use this skill to move selected knowledge from L2 planning-with-files into L3 ByteRover long-term memory. This is a write operation: be conservative, use small focused entries, and do not clean PWF files unless every selected `brv curate` operation succeeds.

## Preconditions

Before curating, verify all of the following:

1. The current directory is the intended repository root or inside that repository.
2. This is the main worktree where L3 writes are allowed. If this is an auxiliary Git worktree, stop and tell the user to merge back first.
3. `task_plan.md`, `progress.md`, and `findings.md` all exist and are readable. If any are missing or unreadable, stop and do not edit or recreate PWF files.
4. `brv status` succeeds for the repository.
5. `brv review pending` has no pending review items before starting a new batch. If pending items exist, stop and ask the user to approve or reject them first.

## Select Knowledge

Read the PWF files and use the current session context. Curate only knowledge that is likely to be useful in future tasks:

- Reusable architecture or implementation decisions.
- Non-obvious bug root causes, especially cross-module or timing/state issues.
- API contracts, domain rules, or technical trade-offs with a meaningful why.
- Stable repository conventions that future agents should know.

Do not curate ephemeral progress, raw logs, obvious typos, secrets, credentials, or large unfiltered chat/file dumps.

## Shape Entries

Create one entry per topic. Keep each entry small enough that ByteRover can reason over it without broad context.

Use this template for every entry:

```text
Decision/Finding: <one-sentence conclusion>
Why: <1-3 sentences with the reason, evidence, or trade-off>
Where: <file path, module, command, or subsystem>
Source: <session context | task_plan.md | progress.md | findings.md>
Sedimented: <YYYY-MM-DD HH:MM>
```

Rules:

- One `brv curate` call should cover one topic.
- Use `--files` only for critical supporting files, with at most 5 file references.
- Prefer explicit file paths over broad folders. Do not use `--folder` unless the user intentionally asks for folder-level onboarding.
- If the source content is large, summarize it first and curate the summary.
- Do not use `--timeout`; current `brv` keeps it only for compatibility and it has no effect.
- If curate feels too slow or too broad, reduce the entry scope instead of increasing timeout.

## Curate

Run entries serially:

```bash
brv curate "<entry text>" --files <path-1> --files <path-2>
```

If no file references are needed:

```bash
brv curate "<entry text>"
```

Do not use `--detach` for the normal L2 to L3 sedimentation flow because PWF cleanup depends on knowing whether every curate operation succeeded.

## Failure Handling

If any `brv curate` command fails, times out, or returns an unclear result:

1. Stop immediately.
2. Report which entries succeeded and which entry failed.
3. Do not clear `findings.md`.
4. Do not delete or rebuild `task_plan.md`.
5. Do not append a successful sedimentation log to `progress.md`.

## Success Cleanup

Only after every selected entry has been curated successfully:

1. Clear `findings.md`.
2. Append a sedimentation log to `progress.md`:

   ```markdown
   ## Sedimentation Log - YYYY-MM-DD HH:MM
   Sedimented N items to ByteRover (pending review)
   - <topic 1>
   - <topic 2>
   ```

3. In `task_plan.md`, remove only completed phases or completed task blocks. Preserve all `in_progress` and `pending` work.
4. Add or update a `Sedimentation Checkpoint` near the top of `task_plan.md`:

   ```markdown
   ## Sedimentation Checkpoint
   Last sedimented: YYYY-MM-DD HH:MM
   Sedimented items: N (see brv review pending)
   Project journal: progress.md
   ```

5. Run `brv review pending` and report the pending review list. Tell the user that they must approve the pending items before the knowledge is fully accepted into the main context tree.

## Output

Finish with:

```markdown
沉淀结果：
- 成功沉淀：<N>
- 跳过：<N，原因>
- PWF 清理：<已执行或未执行，原因>
- ByteRover 审核：<pending 条目摘要>
```
