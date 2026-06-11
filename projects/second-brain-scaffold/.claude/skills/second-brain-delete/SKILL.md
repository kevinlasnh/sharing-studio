---
name: second-brain-delete
description: Safely delete explicit items from the user's Second Brain vault. Use when the user asks to delete/remove a wiki note, whole wiki domain, raw attachment, explicit daily file, or old .workflows artifact from the Second Brain. Always plan first, require a manifest/token confirmation before destructive apply, protect infrastructure paths, validate links/indexes after deletion, then close Basic Memory and journal/HF backup as applicable.
---

# Second Brain Delete

Delete explicit targets from `<vault-path>` while preserving the vault schema, link graph, Basic Memory sync, and Git/HF recovery path.

Use Simplified Chinese when replying to the user.

## Execution Contract

Run this workflow as a destructive-change protocol, not as advice. Start with a deletion manifest, make the user-facing impact visible, apply only after explicit confirmation, validate afterward, and do not report clean until the deletion, validation, Basic Memory closure, journal entry, and HF backup status are all accounted for.

In Claude Code, use `AskUserQuestion` for confirmation gates. In other hosts, use the host's equivalent interaction mechanism; if none is exposed, ask a concise plain-text confirmation and require the exact confirmation token from the manifest.

## Scope

Allowed explicit target types:

- `note`: `wiki/{domain}/{slug}.md` content page, excluding `_index.md`.
- `domain`: `wiki/{domain}` whole domain directory.
- `raw`: `raw/{filename}` attachment.
- `daily`: explicit `daily/YYYY-MM-DD.md` file.
- `workflow`: old `.workflows/{timestamp}` directory.

Protected by default:

- `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `index.md`.
- `.claude/**`, `.agents/**`, `.gemini/**`, `.obsidian/**`, `.git/**`, `.brv/**`, `.claudian/**`.
- Current workflow output from `.workflows/.active-session`.
- Any wildcard, path escape, drive-root, or implicit basename target.

Read `references/delete-policy.md` before handling unusual targets, domain deletes, raw attachments with inbound refs, or any request that asks to bypass backup/validation.

## Workflow

### 1. Plan

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\second-brain-delete\scripts\plan_delete.ps1 -VaultRoot . -Target "<explicit target>" -TargetType auto -OutputManifest ".workflows\<session>\delete-manifest.json"
```

Equivalent host-local script paths are valid:

- Claude Code: `.claude\skills\second-brain-delete\scripts\plan_delete.ps1`
- Codex / cross-agent: `.agents\skills\second-brain-delete\scripts\plan_delete.ps1`
- Gemini CLI: `.gemini\skills\second-brain-delete\scripts\plan_delete.ps1`

Review the manifest. If `allowed` is false, stop and report the refusal reasons. Do not apply a refused manifest.

### 2. Confirm

Show the user the target, target type, inbound references, index impact, delete paths, modified-reference paths, and backup gate status. Require the exact `confirmation_token` from the manifest before apply.

For real `note`, `domain`, `raw`, and `daily` deletes, the manifest must have a pre-delete recovery gate:

- `pre_delete_head`
- `hf_remote_url`
- `hf_main_contains_head`
- `worktree_clean_or_explicitly_scoped_dirty_paths`
- `pre_delete_backup_commit`

Real knowledge deletes are only eligible when the worktree is clean outside explicitly scoped `.workflows/**` workflow artifacts. If any wiki, daily, raw, router, skill, Obsidian, or other non-workflow path is dirty, stop and back it up or resolve it before destructive apply.

Disposable test fixtures and old `.workflows` cleanup may skip the HF gate when the manifest explicitly says `requires_pre_delete_backup: false`.

### 3. Apply

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\second-brain-delete\scripts\apply_delete.ps1 -VaultRoot . -ManifestPath "<manifest.json>" -ConfirmationToken "<token>" -OutputResult "<apply-result.json>"
```

Use `-DryRun` for previews and test matrix coverage that must not modify the vault.

### 4. Validate

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\second-brain-delete\scripts\validate_delete.ps1 -VaultRoot . -ManifestPath "<manifest.json>" -OutputReport "<validation-report.json>"
```

Validation must confirm:

- deleted targets are gone,
- remaining pages do not reference deleted note/raw/domain targets,
- root/domain indexes no longer point at deleted targets,
- daily no-link policy still holds,
- `deep_audit.ps1` returns clean or reports residual risk.

### 5. Basic Memory Closure

If apply changed Markdown or raw files, run the non-journal closure:

```powershell
basic-memory status --project second-brain --json
basic-memory reindex --project second-brain --search
basic-memory status --project second-brain --json
```

Report residual risk if status remains dirty or any command fails.

### 6. Journal And Backup

Write or append `daily/YYYY-MM-DD.md` through `second-brain-journal`, providing the delete manifest and validation report. The journal entry must use plain paths/slugs only, never wikilinks. `second-brain-journal` then runs full Basic Memory reindex and hands off to `second-brain-hf-backup`.

If the user explicitly defers the journal, still run the search-only Basic Memory closure for the deletion changes and report `Journal pending`, embeddings checkpoint deferred, and HF backup deferred until journal.

## Completion Criteria

Report blockage or `residual-risk` instead of done if any applicable item is missing:

- The target was explicit and classified as one allowed type.
- Infrastructure and current workflow protections were enforced.
- A manifest was written and rechecked.
- Destructive apply used the exact confirmation token.
- Real knowledge deletes had a usable pre-delete recovery gate, unless the target was a disposable fixture.
- Validation report exists and is clean, or residual risk is listed.
- Basic Memory closure ran after file changes.
- A daily journal entry and HF backup ran, or the user explicitly deferred them and the deferral is reported.
