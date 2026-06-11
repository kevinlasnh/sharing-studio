# Second Brain Delete Policy

This reference defines the safety policy for `second-brain-delete`.

## Target Classification

Use allowlist-first classification:

| Type | Allowed shape | Notes |
|---|---|---|
| `note` | `wiki/{domain}/{slug}.md` | Must not be `_index.md`. |
| `domain` | `wiki/{domain}` | Deletes the domain directory and removes the root index entry. |
| `raw` | `raw/{filename}` | Only explicit root raw attachments; no basename-only targets. |
| `daily` | `daily/YYYY-MM-DD.md` | Only explicit date files. |
| `workflow` | `.workflows/{timestamp}` | Only old workflow directories, never `.active-session` or the active session path. |

Reject wildcard targets, path escape, absolute paths outside the vault, router files, root `index.md`, host skill/config directories, Obsidian config, `.git`, `.brv`, `.claudian`, and current workflow output.

## Inbound Reference Policy

The manifest must list inbound refs before apply.

- `note`: apply is allowed only when no remaining wiki/daily/root page references the note. The operator should use lint or manual edits first when refs exist.
- `raw`: apply is allowed only when no remaining wiki content page references the raw file. Raw evidence is not silently removed from claims.
- `domain`: apply is allowed only when no page outside the domain links into the domain.
- `daily`: explicit date deletes do not rewrite other pages; daily files should not have graph links.
- `workflow`: no graph semantics; only current-workflow protection matters.

## Manifest Schema

Required top-level fields:

```json
{
  "manifest_version": 1,
  "generated_at": "YYYY-MM-DDTHH:mm:ssK",
  "vault_root": "<vault-path>",
  "target_input": "wiki/domain/page.md",
  "target_type": "note",
  "target_path": "wiki/domain/page.md",
  "operation_scope": "knowledge-delete",
  "allowed": true,
  "refusal_reasons": [],
  "requires_pre_delete_backup": true,
  "is_disposable_fixture": false,
  "pre_delete_head": "<sha>",
  "hf_remote_url": "<hf-private-dataset-url>",
  "hf_main_contains_head": true,
  "worktree_clean_or_explicitly_scoped_dirty_paths": {
    "clean": false,
    "dirty_paths": [".workflows/session/delete-manifest.json"],
    "explicitly_scoped_dirty_paths": [".workflows/session/delete-manifest.json"],
    "unscoped_dirty_paths": [],
    "acceptable": true
  },
  "pre_delete_backup_commit": "<sha>",
  "deleted_paths": ["wiki/domain/page.md"],
  "modified_reference_paths": ["wiki/domain/_index.md"],
  "index_paths": ["wiki/domain/_index.md"],
  "validation_report_path": ".workflows/session/delete-validation.json",
  "inbound_refs": [],
  "outbound_refs": [],
  "raw_refs": [],
  "confirmation_token": "DELETE:wiki/domain/page.md:<hash>"
}
```

For real knowledge deletes, `pre_delete_backup_commit` must be non-empty and recoverable locally or from the private HF remote, and the worktree must be clean outside explicitly scoped `.workflows/**` workflow artifacts. Disposable fixture targets and old workflow cleanup may set `requires_pre_delete_backup: false`.

## Apply Rules

`apply_delete.ps1` must:

- read only the manifest and explicit confirmation token,
- recheck target path and current active workflow,
- reject refused manifests,
- reject manifest/disk target mismatches,
- reject real knowledge deletes without the pre-delete gate,
- reject real knowledge deletes when non-`.workflows/**` dirty paths exist at apply time,
- perform only file deletes and mechanical index line removal explained by the manifest,
- write an apply result report.

No script should silently edit semantic prose to remove claims. If inbound refs exist, refuse and ask the user to use lint/manual cleanup first.

## Validation Rules

`validate_delete.ps1` must:

- confirm deleted paths are absent,
- scan remaining Markdown for refs to deleted note/raw/domain targets,
- confirm root/domain index entries are removed,
- run `deep_audit.ps1` when available,
- write a validation report path that can be cited by the journal.

Validation reports are evidence, not final closure. Basic Memory and HF backup still need their normal closure.
