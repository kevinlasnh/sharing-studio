---
name: second-brain-journal
description: Write or append to the user's Second Brain daily journal at daily/YYYY-MM-DD.md. Use when the user says "写一下第二大脑日记", "second brain journal", "日记", when second-brain-ingest hands off an ingest manifest, or when second-brain-delete hands off a delete manifest. Enforces ingest/delete manifest coverage without creating Obsidian graph links from daily notes, then runs Basic Memory adaptive reindex closure and hands off to second-brain-hf-backup for full Git snapshot push with LFS/Xet object upload.
---

# Second Brain Journal

Write the daily reflection for this vault.

This skill is the renamed and tightened version of the old local `journal` skill.

## Execution Contract

Run the journal workflow completely before reporting done. The user should not need to say "follow the skill carefully"; every journal request already includes that requirement.

Do not stop after identifying the date or drafting text. Determine the path, read or create the file, append without overwriting, enforce the no-internal-link boundary, verify manifest coverage when an ingest or delete manifest is provided, then run the Basic Memory adaptive reindex closure and hand off to `second-brain-hf-backup` for full Git snapshot push with LFS/Xet object upload. Stop early only if the user has no substantive session activity to record, or if the target file/tool is unavailable; report that state explicitly.

In Claude Code, use the `AskUserQuestion` tool for every journal scope clarification or "ingest vs journal" clarification. Do not ask workflow questions as plain assistant text unless the current host does not expose that tool.

## File Location

Use `daily/YYYY-MM-DD.md`. This matches `.obsidian/daily-notes.json`:

```json
{ "folder": "daily", "format": "YYYY-MM-DD" }
```

## Timestamp Rule

Append headings must use real system time. Do not estimate.

Windows:

```powershell
Get-Date -Format HH:mm
```

POSIX:

```bash
date +%H:%M
```

If system time is unavailable, use `??:??` and state that the timestamp is missing.

## Workflow

1. Determine today's journal path.
2. Read `daily/YYYY-MM-DD.md` if it exists.
3. If missing, create it with the new-file skeleton.
4. If present, append with a separator and `## HH:MM · summary`.
5. If an ingest manifest is provided, cover every created/updated wiki content page and any domain-routing or new-domain decision.
6. If a delete manifest is provided, cover deleted paths, repaired refs, index updates, validation result, and Basic Memory closure status. Record `HF backup: pending journal closure` when the backup has not run yet.
7. Verify all manifest pages and paths appear at least once as plain text paths or slugs, not as daily wikilinks.
8. Run the Basic Memory adaptive reindex closure.
9. Hand off to `second-brain-hf-backup` for the Hugging Face full Git snapshot push closure.

## New File Skeleton

```yaml
---
date: YYYY-MM-DD
permalink: second-brain/daily/YYYY-MM-DD
weekday: Monday
mood: neutral
energy: neutral
tags:
- daily
- journal
---

# YYYY-MM-DD

<body>
```

Basic Memory does not add journal frontmatter in this vault. When creating a daily file, write `permalink: second-brain/daily/YYYY-MM-DD` using the final filename date. When appending to an existing daily file, preserve its `permalink`; repair it only if it does not match the filename.

## Append Format

```markdown

---

## HH:MM · <one-line summary>

<new content>
```

Never overwrite existing journal content.

## Manifest Coverage Rules

When called from `second-brain-ingest`, require the ingest manifest:

```text
created pages:
- wiki/domain/page-a.md
updated pages:
- wiki/domain/page-b.md
preflight status:
- confirmed | deferred | not provided
domain decisions:
- atom -> action -> domain/page
new domain rationale:
- none | domain slug + scope note + nearest-neighbor boundary reasons
domains:
- domain
semantic coverage summary:
- fidelity_level: Light | Standard | Full
- semantic_units: P0=N, P1=N, P2=N
- high_risk_items: N
- user_confirmed_items: N
- residual_risk: none | listed
journal status:
- pending | written | deferred
```

Every created or updated wiki content page must appear in the journal at least once as plain text. Prefer `wiki/{domain}/{slug}.md`; bare slugs such as `page-a` are acceptable only when unambiguous in context. If the manifest includes preflight/domain decisions, summarize them as plain text without wikilinks. If the manifest includes semantic coverage, record only the summary counts, confirmation count, and residual-risk status; do not copy the full semantic-unit matrix into the daily note. Do not rely on `source_date`, because existing pages preserve their original source date.

If no manifest is available, write only a normal session journal and do not claim ingest closure.

When called from `second-brain-delete`, require the delete manifest and validation result:

```text
delete manifest:
- target_type: note | domain | raw | daily | workflow
- target_path: wiki/domain/page.md | raw/file.ext | daily/YYYY-MM-DD.md | .workflows/session
- operation_scope: knowledge-delete | disposable-fixture-delete | workflow-artifact-delete
- deleted_paths:
  - path
- modified_reference_paths:
  - path
- index_paths:
  - path
- requires_pre_delete_backup: true | false
- pre_delete_backup_commit: commit | none
- validation_report_path: path
validation result:
- clean: true | false
- issues: none | listed
closure:
- Basic Memory: clean | residual-risk | deferred
- HF backup: pending journal closure | deferred
```

Every deleted path, modified reference path, and index path must appear in the journal at least once as plain text. Prefer exact vault-relative paths such as `wiki/{domain}/{slug}.md`, `raw/file.ext`, `daily/YYYY-MM-DD.md`, or `.workflows/session`. Record whether validation was clean. If the delete was a disposable fixture, say so plainly and do not imply user knowledge was removed. Do not copy the full JSON manifest into the daily note.

The daily note records delete/ingest manifest coverage and, when the backup has not run yet, records `HF backup: pending journal closure`. The actual `second-brain-hf-backup` result is reported in this workflow's final response after the handoff; do not append a post-backup result to the same daily note unless a separate later journal and backup cycle is intentionally started.

If a delete manifest is unavailable, write only a normal session journal and do not claim delete closure.

## No Internal Link Boundary

Daily notes are timeline records, not graph edges. They must not create Obsidian internal links.

Allowed:

- `content-page`
- `wiki/domain/content-page.md`
- Chinese or English page title as ordinary prose

Forbidden:

- `[[content-page]]`
- `[[wiki/domain/content-page|display]]`
- `[display](../wiki/domain/content-page.md)` or any local/relative Markdown link
- `[[index]]`
- `[[wiki/domain/_index]]`
- `[[daily/...]]`
- `[[CLAUDE]]`, `[[CLAUDE.md]]`, `[[AGENTS]]`, `[[AGENTS.md]]`, `[[GEMINI]]`, or `[[GEMINI.md]]`
- `[[raw/...]]`
- Any Obsidian wikilink

External `http(s)` links are allowed. Mention raw files only as plain text paths such as `raw/file.pdf`, preferably in backticks; do not use raw links as journal provenance edges.

## Basic Memory Adaptive Reindex Closure

After a journal file is successfully created or appended and rechecked, close Basic Memory sync from this skill. For normal ingest workflows that write a journal, this is the final Basic Memory sync point after wiki/raw/index and daily changes, immediately before the mandatory Hugging Face backup handoff. Because journal is the end-of-work checkpoint, this closure rebuilds both the full-text search index and vector embeddings. Basic Memory 0.20.3 does not expose explicit reindex as an MCP tool; run the CLI command below for this checkpoint. Other workflows that change Markdown without writing a journal must run their own status/reindex/status closure; they may use search-only closure when they are not the final journal checkpoint.

1. Run:

```powershell
basic-memory status --project second-brain --json
```

2. Always run the default full Basic Memory reindex after a journal write, even when the first status is already clean:

```powershell
basic-memory reindex --project second-brain
```

This intentionally runs both search and embeddings. In Basic Memory 0.20.3, embeddings reindex scans the project but uses chunk hashes to skip unchanged chunks, so it is appropriate for the journal checkpoint after a batch of work.

3. Run `basic-memory status --project second-brain --json` again and verify it is clean.
4. If the second status is still dirty, or either command fails, report `residual-risk` with the status details and do not claim full closure. If embeddings fail because sqlite-vec or the embedding provider is unavailable while search sync succeeded, report search clean plus embedding residual-risk explicitly.

If no journal entry was written because there was no substantive session activity, do not run this closure. If ingest already wrote wiki/raw/index changes but the user deferred the journal, ingest must still run Basic Memory sync closure for those written files before returning; a later journal call will run closure again for the daily file and then hand off to `second-brain-hf-backup`.

## Hugging Face Backup Handoff

After the Basic Memory adaptive reindex closure attempt finishes, call `second-brain-hf-backup` from the same vault root. This is mandatory after any successful journal write or append.

The backup handoff performs full Git snapshot backup according to Git rules:

```powershell
git add -A
git commit -m "second-brain: hf backup YYYY-MM-DD HH:mm:ss"
git lfs push hf HEAD
git push hf HEAD:main
```

The backup skill owns the exact script path, remote verification, JSON result parsing, and residual-risk reporting. This journal skill must include the backup result in its final response: commit hash, pushed remote/branch, skip reason, or failure summary.

If Basic Memory reports residual-risk, still run the backup handoff after the Basic Memory commands finish, then report both Basic Memory status and Git backup status separately. If no journal entry was written, do not run the backup handoff.

## Completion Criteria

Report blockage instead of done if any applicable item is missing:

- The daily path is exactly `daily/YYYY-MM-DD.md`.
- Existing journal content was preserved.
- New daily files include deterministic `permalink: second-brain/daily/YYYY-MM-DD`; existing daily files preserve or repair that path-matching permalink.
- New content was appended under a real `HH:mm` heading, or missing time was explicitly marked.
- Any ingest manifest pages and delete manifest paths are mentioned as plain text paths or unambiguous slugs.
- No `[[wikilink]]`, local Markdown link, or raw wikilink was added.
- The written file was rechecked for manifest coverage and daily link policy before returning.
- Basic Memory adaptive reindex closure ran after the journal write, or the no-journal/deferred-journal reason was explicitly reported.
- After any journal write, `basic-memory reindex --project second-brain` ran regardless of the first status result, and the second status check verified clean; otherwise residual-risk was reported.
- After any journal write, `second-brain-hf-backup` ran after the Basic Memory closure attempt, uploaded LFS/Xet objects before updating the Git ref, and reported a pushed commit, an existing-HEAD push, a no-change skip, or residual-risk.

## Body Guidance

Do not use a rigid template. Prefer a concise record of:

- what changed,
- key findings or decisions,
- created/updated pages,
- unresolved follow-up,
- reflection only when it is concrete.

Avoid generic diary filler.

## Non-Triggers

If there was no substantive session activity, say a journal entry is unnecessary.

If the user says "记一下" without "日记" or "第二大脑", clarify whether they want ingest or journal.
