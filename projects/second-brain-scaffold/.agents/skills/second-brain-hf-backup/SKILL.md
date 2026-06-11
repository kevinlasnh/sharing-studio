---
name: second-brain-hf-backup
description: Back up the user's Second Brain vault to the private Hugging Face dataset remote. Use after second-brain-journal finishes Basic Memory adaptive reindex closure, and whenever the user asks to sync, backup, commit, push, or restore the Second Brain via Hugging Face. Performs a full Git snapshot with git add -A, git commit, git lfs push, and git push to the hf remote main branch, then reports the commit or residual risk.
---

# Second Brain HF Backup

Create a full Git snapshot of `<vault-path>` and push it to the private Hugging Face dataset remote.

This skill is the vault's remote backup closure. It is called after `second-brain-journal` completes its Basic Memory adaptive reindex closure. It can also be run directly when the user asks to back up, sync, commit, or push the Second Brain to Hugging Face.

## Execution Contract

Run this skill as an execution step, not as advice. The user has chosen full-repo backup after journal writes.

When called from `second-brain-journal`, do not ask for a second confirmation before committing or pushing. The confirmation already lives in the repository operating policy. If the user calls this skill directly and the request is ambiguous, clarify only the target remote or branch.

`git add -A` means the full Git worktree according to Git rules. It stages modifications, additions, and deletions, while still respecting `.gitignore`. Do not use shell tricks to bypass `.gitignore`.

This skill is not a privacy purge mechanism. Git history and the remote may retain previous versions. If the user wants sensitive content permanently removed from history, stop and discuss a separate purge workflow instead of running this backup.

## Defaults

- Vault root: `<vault-path>`
- Remote: `hf`
- Remote URL: `<hf-private-dataset-url>`
- Branch target: `main`
- Commit message prefix: `second-brain: hf backup`
- Initial bootstrap: enabled with `--force-with-lease` only when the local repository had no `HEAD` before the new backup commit, or when retrying after a failed first bootstrap left a single local root commit

## Workflow

1. Confirm the current directory is the vault root or a path inside the vault, then run the script from the vault root.
2. Verify Git remote `hf` exists.
3. Run the full snapshot push script for the active host copy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .agents\skills\second-brain-hf-backup\scripts\git_full_snapshot_push.ps1 -VaultRoot . -Remote hf -Branch main
```

Equivalent host-local paths are valid:

- Claude Code: `.claude\skills\second-brain-hf-backup\scripts\git_full_snapshot_push.ps1`
- Codex / cross-agent: `.agents\skills\second-brain-hf-backup\scripts\git_full_snapshot_push.ps1`
- Gemini CLI: `.gemini\skills\second-brain-hf-backup\scripts\git_full_snapshot_push.ps1`

4. Read the JSON result.
5. Report the Git closure status:
   - `pushed`: include commit, remote, branch, and action.
   - `skipped`: include the reason.
   - failure: report `residual-risk` with the failing command summary.

## Script Behavior

The script performs:

```powershell
git add -A
git commit -m "second-brain: hf backup YYYY-MM-DD HH:mm:ss"
git lfs push hf HEAD
git push hf HEAD:main
```

The explicit `git lfs push` step uploads Hugging Face Xet/LFS objects before the Git ref update, preventing remote rejection for missing LFS pointer targets.

If there are no staged changes but a local `HEAD` exists, the script pushes existing `HEAD` to `hf/main`. If there are no staged changes and no local `HEAD`, it returns `skipped`.

If the remote rejects a normal push after an existing local `HEAD`, the script fails and the calling workflow must report `residual-risk`, except for the single-root retry case below. Do not silently retry with force push for ordinary non-fast-forward rejections.

For one-time initial bootstrap only, when the local repository had no `HEAD` before the backup commit, or when a previous bootstrap attempt failed after leaving a single local root commit, and the remote branch already exists, the script may retry with `--force-with-lease=<observed-remote-sha>`. This preserves safety against concurrent remote changes while allowing the local vault to replace the Hugging Face auto-initialized commit. The vault keeps the Hugging Face `.gitattributes` patterns locally so this bootstrap does not drop large-file handling rules.

If a local pre-push hook blocks protected agent/vault paths, it must still allow this exact private backup target: remote name `hf` with URL `<hf-private-dataset-url>`. Other remotes should remain blocked for protected local agent/vault files.

## Completion Criteria

Report blockage or `residual-risk` instead of `complete` if any item is missing:

- The command ran from the vault root.
- `git add -A` completed successfully.
- A commit was created, an existing `HEAD` was pushed, or a no-change skip was reported.
- LFS/Xet objects were uploaded before the Git ref push when tracked LFS files exist.
- `git push hf HEAD:main` completed successfully when a push was needed.
- Initial no-HEAD or single-root bootstrap retry, if needed, used `--force-with-lease` against the observed remote SHA rather than unconditional force push.
- The final response includes the commit hash or skip reason.
- Failures include enough detail for the user to decide whether to bootstrap the remote, fix credentials, or retry.
