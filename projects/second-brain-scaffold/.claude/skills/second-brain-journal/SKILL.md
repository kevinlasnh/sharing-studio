---
name: second-brain-journal
description: Write or append to the user's Second Brain daily journal at daily/YYYY-MM-DD.md. Use when the user says "写一下第二大脑日记", "second brain journal", "日记", or when second-brain-ingest hands off an ingest manifest. Enforces manifest coverage for preflight decisions and created/updated wiki pages without creating Obsidian graph links from daily notes.
---

# Second Brain Journal

Write the daily reflection for this vault.

This skill is the renamed and tightened version of the old local `journal` skill.

## Execution Contract

Run the journal workflow completely before reporting done. The user should not need to say "follow the skill carefully"; every journal request already includes that requirement.

Do not stop after identifying the date or drafting text. Determine the path, read or create the file, append without overwriting, enforce the no-internal-link boundary, and verify manifest coverage when an ingest manifest is provided. Stop early only if the user has no substantive session activity to record, or if the target file/tool is unavailable; report that state explicitly.

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
6. Verify all manifest pages appear at least once as plain text paths or slugs, not as daily wikilinks.

## New File Skeleton

```yaml
---
date: YYYY-MM-DD
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

Basic Memory may add `permalink`; do not hand-write or edit it.

## Append Format

```markdown

---

## HH:MM · <one-line summary>

<new content>
```

Never overwrite existing journal content.

## Manifest Coverage Rule

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
journal status:
- pending | written | deferred
```

Every created or updated wiki content page must appear in the journal at least once as plain text. Prefer `wiki/{domain}/{slug}.md`; bare slugs such as `page-a` are acceptable only when unambiguous in context. If the manifest includes preflight/domain decisions, summarize them as plain text without wikilinks. Do not rely on `source_date`, because existing pages preserve their original source date.

If no manifest is available, write only a normal session journal and do not claim ingest closure.

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
- `[[CLAUDE]]`, `[[CLAUDE.md]]`, `[[AGENTS]]`, or `[[AGENTS.md]]`
- `[[raw/...]]`
- Any Obsidian wikilink

External `http(s)` links are allowed. Mention raw files only as plain text paths such as `raw/file.pdf`, preferably in backticks; do not use raw links as journal provenance edges.

## Completion Criteria

Report blockage instead of done if any applicable item is missing:

- The daily path is exactly `daily/YYYY-MM-DD.md`.
- Existing journal content was preserved.
- New content was appended under a real `HH:mm` heading, or missing time was explicitly marked.
- Any ingest manifest pages are mentioned as plain text paths or unambiguous slugs.
- No `[[wikilink]]`, local Markdown link, or raw wikilink was added.
- The written file was rechecked for manifest coverage and daily link policy before returning.

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
