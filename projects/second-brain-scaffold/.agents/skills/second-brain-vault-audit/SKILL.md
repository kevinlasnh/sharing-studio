---
name: second-brain-vault-audit
description: External maintainer health-check and repair workflow for the user's Second Brain vault. Use when the user asks for repository-level health checks, "仓库健康度外部检查", full vault audit, Claude/Codex/Gemini router maintenance, local skill validation, hook/MCP/Obsidian scaffold checks, or an end-to-end clean/residual-risk verdict.
---

# Second Brain Vault Audit

Run the repository-level external audit for `<vault-path>`. This skill checks the router, local skills, deterministic hooks, MCP setup, Obsidian configuration, scaffold boundaries, Basic Memory sync, and cross-file rule consistency.

Use Simplified Chinese when replying to the user.

## Execution Contract

Run this audit workflow completely before reporting `clean`, `blocked`, or `residual-risk`. The user should not need to say "follow the skill carefully"; every vault-audit request already includes that requirement.

Start at the Scope Guard, continue through the applicable Audit Workflow steps, and compare the result against the Clean Standard before the final answer. Do not stop after reading router files, running only `deep_audit.ps1`, or validating only one host's skill directory. Stop early only for a real tool/source blocker, and report exactly which required checks were not completed.

## Scope Guard

This vault is an L2 personal Second Brain vault, not an L1 project-memory repository.

- Do not load `planning-with-files`.
- Do not create `task_plan.md`, `progress.md`, or `findings.md`.
- Treat `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md` as synchronized high-level router files.
- Treat this skill as the external maintainer audit protocol.
- In Claude Code, use the `AskUserQuestion` tool for every semantic-fix confirmation or scope clarification. Do not ask workflow questions as plain assistant text unless the current host does not expose that tool.

## Audit Workflow

### 1. Inspect the Contract Surface

Read enough of these files to check for contradictions:

- `CLAUDE.md`
- `AGENTS.md`
- `GEMINI.md`
- `index.md`
- `.claude/settings.json`
- `.claude/settings.local.json` if present
- `.claude/skills/*/SKILL.md`, `.agents/skills/*/SKILL.md`, and `.gemini/skills/*/SKILL.md`
- `.claude/skills/*/references/*.md`, `.agents/skills/*/references/*.md`, and `.gemini/skills/*/references/*.md` when relevant
- `.claude/scripts/*.ps1`
- `.obsidian/*.json`

Pay special attention to these invariants:

- `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md` must stay synchronized according to the project sync rule.
- `second-brain-ingest` must require domain-routing preflight before any wiki write or new-domain proposal.
- Router and skills must enforce the Basic Memory-first semantic retrieval contract: status gate, one search-only reindex before fallback, MCP/CLI Basic Memory before Grep, file_path filtering, and opened page bodies before decisions.
- Query/ingest candidate filters and journal no-link boundaries must exclude all three router files: `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md`.
- Ingest, query, lint, and domain-routing must not silently fall back to Grep when Basic Memory is merely dirty; they must attempt `basic-memory reindex --project second-brain --search` once first.
- Write workflows must not leave Basic Memory dirty, and journal writes must not skip remote backup: ingest with journal closes through `second-brain-journal`, whose final checkpoint runs CLI `basic-memory reindex --project second-brain` for search + embeddings and then calls `second-brain-hf-backup` for `git add -A`, commit, `git lfs push hf HEAD`, and `git push hf HEAD:main`; ingest with deferred journal, lint fix pass, router/skill maintenance, and Markdown file moves must run status/reindex/status before claiming clean.
- `wiki/*/_index.md` is navigation/scope evidence, not a wiki content page.
- Daily notes must not contain Obsidian wikilinks or local/relative Markdown links.
- Raw files are immutable source or instructional visual files, not graph/navigation nodes.
- Markdown image centering is a vault-level Obsidian CSS snippet concern; agents must not add per-page HTML or inline CSS to center images.
- Claude Code workflow confirmations must use `AskUserQuestion` rather than plain assistant questions.
- The allowed top-level hidden directories are `.git`, `.claude`, `.agents`, `.gemini`, `.claudian`, `.obsidian`, `.workflows`, `.brv`, and empty Obsidian `.trash`. `.claude`, `.agents`, and `.gemini` are host configuration/skill state; `.claudian` is host UI state only, `.workflows` is heavy workflow artifact state, and `.brv` is ByteRover local state; none of them are Second Brain knowledge content.

### 2. Run Required Commands

Run Basic Memory CLI commands serially on Windows. Do not put `basic-memory status`, `basic-memory tool search-notes`, `basic-memory project info`, or `basic-memory reindex` into the same parallel tool batch; Basic Memory 0.20.3 can otherwise trip a transient log-file cleanup race and produce a false FileNotFoundError.

Run the deterministic vault audit:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.claude\skills\second-brain-lint\scripts\deep_audit.ps1 -VaultRoot .
```

Validate all local skills:

```powershell
python <home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-ingest
python <home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-query
python <home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-lint
python <home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-journal
python <home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-hf-backup
python <home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-delete
python <home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-graph-manager
python <home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-vault-audit
```

Then verify `.agents/skills` and `.gemini/skills` are exact mirrors of `.claude/skills`.

- The eight local second-brain skill directory names must match across `.claude/skills`, `.agents/skills`, and `.gemini/skills`.
- For each skill, the recursive file-content hash must match across all three host directories.
- `.claude/skills` is the canonical validation target because the PowerShell hard-defense scripts and audit entry commands live under `.claude`; identical mirror hashes make the `.agents` and `.gemini` copies validated by equivalence.

Check MCP and Basic Memory:

```powershell
claude mcp list
codex mcp list
basic-memory status --project second-brain --json
basic-memory tool search-notes "second brain" --project second-brain --page-size 5
```

If `basic-memory status` is dirty during the audit, run `basic-memory reindex --project second-brain --search` once and check status again before reporting residual-risk. Do not run full embeddings reindex as part of routine audit closure unless the user explicitly asks for embedding maintenance or the audit is validating the journal checkpoint after an actual journal write.

If `basic-memory project info second-brain` reports sqlite-vec unavailable or `0/<N>` embeddings while `status` and search are clean, run a short vector sanity probe before treating it as residual-risk:

```powershell
@'
import sqlite3, sqlite_vec
from pathlib import Path
db = Path.home() / ".basic-memory" / "memory.db"
con = sqlite3.connect(str(db))
con.enable_load_extension(True)
con.load_extension(sqlite_vec.loadable_path())
print("vec_version", con.execute("select vec_version()").fetchone()[0])
print("vector_embeddings", con.execute("select count(*) from search_vector_embeddings").fetchone()[0])
print("vector_chunks", con.execute("select count(*) from search_vector_chunks").fetchone()[0])
con.close()
'@ | <home>\AppData\Roaming\uv\tools\basic-memory\Scripts\python.exe -
```

When the same Basic Memory uv tool environment imports `sqlite_vec`, vector rows exist, search probes return current disk content, and active config/router scans show no stale MCP residue, classify the `project info` warning as an informational Basic Memory 0.20.3 status-display false positive. Do not switch core workflows to Grep on that basis alone.

### 3. Run Mechanical Scans

Run these additional checks:

- PowerShell parser check for `.claude/**/*.ps1`.
- JSON parse check for `.claude/*.json`, `.obsidian/*.json`, `~/.claude.json`, `~/.mcp.json`, and `~/.gemini/settings.json`.
- Hidden directory scan: only `.git`, `.claude`, `.agents`, `.gemini`, `.claudian`, `.obsidian`, `.workflows`, `.brv`, and empty `.trash` are allowed; `.claude`, `.agents`, `.gemini`, `.claudian`, `.workflows`, and `.brv` must not be treated as knowledge sources.
- Forbidden scaffold scan for:
  - `wiki/log.md`
  - `wiki/hot.md`
  - `wiki/ingest-log.md`
  - `wiki/sources/**`
  - `.raw/**`
  - `raw/**/*.md`
  - `wiki/overview.md`
  - `wiki/index.md`
  - `wiki/meta/dashboard.md`
  - `wiki/meta/overview.canvas`
  - `wiki/**/*.canvas`
- Active config/router scan for stale MCP names. Scan `.claude/settings*.json`, `.obsidian/*.json`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `index.md`, `~/.claude.json`, `~/.mcp.json`, and `~/.gemini/settings.json`; do not count this audit checklist itself as stale residue:
  - `web-search-prime`
  - `web_search_prime`
  - `open.bigmodel.cn/api/mcp/web_search_prime`
- Basic Memory-first rule scan:
  - router contains `Basic Memory-first Semantic Retrieval Contract`
  - ingest Search-Before-Write attempts one `--search` reindex before Grep fallback
  - ingest/query filters exclude `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.claude/**`, `.agents/**`, and `.gemini/**` as content candidates or answer sources
  - journal no-link boundary forbids wikilinks to `CLAUDE`, `AGENTS`, and `GEMINI`
  - domain-routing retrieval channels list status gate, one-shot reindex, MCP, CLI, then Grep fallback
  - query permits one search-only reindex while remaining vault-file read-only
  - lint uses Basic Memory for semantic candidate discovery and runs closure after Markdown-changing fixes
  - journal says it is the final Basic Memory sync point for ingest-with-journal, runs CLI `basic-memory reindex --project second-brain` after every journal write, and then calls `second-brain-hf-backup`
  - non-journal Markdown writers run their own closure and may use search-only reindex when they are not the final journal checkpoint
  - `second-brain-delete` exists in all three local skill directories, validates with `quick_validate.py`, and its scripts parse with PowerShell.
  - `second-brain-delete` enforces a plan/apply/validate workflow: manifest first, exact confirmation token, infrastructure refusal, current workflow refusal, pre-delete backup gate for real knowledge deletes, clean worktree outside explicitly scoped `.workflows/**` artifacts, validation report, Basic Memory closure, and journal/HF backup handoff.
  - `second-brain-journal` accepts delete manifests and records deleted paths, repaired refs, index updates, validation result, Basic Memory closure, and `HF backup: pending journal closure` without daily wikilinks; the actual HF backup result is reported in the journal workflow final response after handoff.
  - `second-brain-hf-backup` exists in all three local skill directories and its script performs `git add -A`, commit, `git lfs push hf HEAD`, and `git push hf HEAD:main`
  - Hugging Face bootstrap safety exists: root `.gitattributes` preserves the Hub large-file patterns, the backup script explicitly uploads LFS/Xet objects before Git ref updates, and the backup script uses `--force-with-lease` only for initial no-HEAD or single-root bootstrap retry cases
  - Local pre-push protection, if present, blocks protected agent/vault files for non-HF remotes but allows the exact private `hf` remote URL `<hf-private-dataset-url>` for full-vault backup
- Obsidian Markdown image display scan:
  - `.obsidian/snippets/second-brain-markdown-images.css` exists
  - it contains centering rules for `.image-embed` and standalone image-only paragraphs
  - `.obsidian/appearance.json` enables `second-brain-markdown-images`

### 4. Dry-Run Hooks

Prove both blocking and allowed paths:

- Deprecated wiki scaffold path is blocked.
- Wiki full-file content without frontmatter is blocked.
- `daily/YYYY-MM-DD.md` with internal wikilinks is blocked.
- Raw weak context such as "see also raw" is blocked.
- Non-image raw embeds such as `![[raw/source.pdf]]` are blocked.
- Valid wiki content-page markdown is allowed.
- Valid raw provenance sentence from a wiki content page is allowed.
- Valid instructional raw image embed such as `![[raw/diagram.png|600]]` from a wiki content page is allowed, and an existing portrait image must use `|360`.
- Valid `wiki/*/_index.md` navigation links are allowed.
- Raw links from `wiki/*/_index.md` are blocked.

### 5. Manual Semantic Review

Do not rely only on deterministic scripts. Also review:

- Root `index.md` domain descriptions vs each `wiki/*/_index.md` scope summary.
- Domain taxonomy: suspicious one-off domains, overlapping domains, misplaced pages, unclear scope summaries.
- Content-page body links using weak markers such as `详见`, `参见`, `推荐`, `相关`, `See also`, or cross-domain links.
- Time-sensitive claims involving versions, prices, policies, regulations, salaries, release dates, model capabilities, API behavior, job markets, or market data.
- Basic Memory contract consistency:
  - Grep is never documented as the first semantic retrieval channel.
  - Dirty Basic Memory leads to one `basic-memory reindex --project second-brain --search` before fallback.
  - Any fallback must be reported in manifests or final answers.
  - Embedding `reindex_recommended` is not treated as routine ingest/query blocker when status and search are clean, but journal checkpoint still runs default CLI reindex to refresh embeddings after batch work and then hands off to `second-brain-hf-backup`.
  - Basic Memory 0.20.3 `project info` sqlite-vec false positives are judged against direct uv tool `sqlite_vec` import, vector row counts, active config/router stale-MCP scans, and search probe behavior.

Classify pages without inbound content-page links as informational unless another rule is violated. Do not add graph links merely to improve graph shape.

## Fix Policy

Apply safe mechanical fixes directly:

- Broken JSON syntax.
- PowerShell syntax errors.
- Forbidden scaffold deletion.
- Hook path mismatch.
- Clear contradiction between `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, local skills, and scripts.
- Missing mandatory ingest preflight wording.
- Missing Basic Memory-first freshness gate, one-shot reindex before fallback, file_path filtering, journal-to-HF-backup handoff, or closure wording in router/local skills.
- Stale `web-search-prime` MCP residue.
- `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` sync drift when the project sync rule says they must match.

Ask for explicit confirmation before semantic changes:

- Moving wiki pages between domains.
- Merging or splitting domains.
- Deleting content-page wikilinks for semantic reasons.
- Rewriting time-sensitive knowledge claims.
- Changing a domain's intended scope.

Never delete user knowledge content just because it is isolated, informational, or low-link.

## Clean Standard

Report `clean` only when all are true:

- `deep_audit.ps1` reports no mechanical issues.
- All canonical `.claude/skills` validate, and `.agents/skills` plus `.gemini/skills` are exact mirrors of `.claude/skills`.
- PowerShell scripts parse.
- JSON configs parse.
- Obsidian Markdown image centering snippet exists and is enabled.
- `basic-memory` is connected in Claude MCP; Codex MCP is checked when `codex` is installed; no forbidden web-search-prime server exists.
- A Basic Memory search probe works through MCP or CLI fallback with `--project second-brain`.
- `basic-memory status --project second-brain --json` is clean.
- Basic Memory vector sanity is acceptable: either `project info` shows embeddings healthy, or a direct uv tool vector probe proves `sqlite_vec` loads and vector rows exist while search probes return current disk content.
- Hidden directories are only `.git`, `.claude`, `.agents`, `.gemini`, `.claudian`, `.obsidian`, `.workflows`, `.brv`, and empty `.trash`; `.claude`, `.agents`, `.gemini`, `.claudian`, `.workflows`, and `.brv` remain local state only.
- No forbidden scaffold paths exist.
- Hook dry-runs prove both blocking and allowed examples.
- Router and local skills consistently enforce Basic Memory-first semantic retrieval, Basic Memory clean-closure invariants, journal-triggered Hugging Face backup invariants, LFS/Xet object upload before Git ref push, and the private-HF-only pre-push exception.
- `second-brain-delete` is present in the router and all three local skill mirrors; its plan/apply/validate scripts parse, fixture dry-runs cover note/raw/domain/daily/workflow/infra refusal, real knowledge deletes require clean worktree outside explicitly scoped `.workflows/**` artifacts, and delete manifest coverage is reflected in `second-brain-journal`.
- Router files, local skills, references, hooks, MCP behavior, Basic Memory behavior, and Obsidian config do not contradict each other.

If only informational items remain, report `clean` with an informational note.

## Windows Encoding

When reading or writing files with Chinese content in PowerShell, always specify UTF-8:

```powershell
Get-Content -Raw -Encoding UTF8 <path>
Set-Content -Encoding UTF8 <path>
```

Prefer `apply_patch` for manual edits. Use mechanical copy/write commands only for purely mechanical synchronization, and still use UTF-8.
