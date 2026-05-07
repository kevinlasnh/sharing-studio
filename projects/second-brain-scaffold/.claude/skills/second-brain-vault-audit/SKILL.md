---
name: second-brain-vault-audit
description: External maintainer health-check and repair workflow for the user's Second Brain vault. Use when the user asks for repository-level health checks, "仓库健康度外部检查", full vault audit, Codex/agent maintenance of CLAUDE.md or AGENTS.md, local skill validation, hook/MCP/Obsidian scaffold checks, or an end-to-end clean/residual-risk verdict.
---

# Second Brain Vault Audit

Run the repository-level external audit for `<vault-path>`. This skill checks the router, local skills, deterministic hooks, MCP setup, Obsidian configuration, scaffold boundaries, Basic Memory sync, and cross-file rule consistency.

Use Simplified Chinese when replying to the user.

## Scope Guard

This vault is an L2 personal Second Brain vault, not an L1 project-memory repository.

- Do not load `planning-with-files`.
- Do not create `task_plan.md`, `progress.md`, or `findings.md`.
- Treat `CLAUDE.md` and `AGENTS.md` as synchronized high-level router files.
- Treat this skill as the external maintainer audit protocol.
- In Claude Code, use the `AskUserQuestion` tool for every semantic-fix confirmation or scope clarification. Do not ask workflow questions as plain assistant text unless the current host does not expose that tool.

## Audit Workflow

### 1. Inspect the Contract Surface

Read enough of these files to check for contradictions:

- `CLAUDE.md`
- `AGENTS.md`
- `index.md`
- `.claude/settings.json`
- `.claude/settings.local.json` if present
- `.claude/skills/*/SKILL.md`
- `.claude/skills/*/references/*.md` when relevant
- `.claude/scripts/*.ps1`
- `.obsidian/*.json`

Pay special attention to these invariants:

- `CLAUDE.md` and `AGENTS.md` must stay synchronized according to the project sync rule.
- `second-brain-ingest` must require domain-routing preflight before any wiki write or new-domain proposal.
- `wiki/*/_index.md` is navigation/scope evidence, not a wiki content page.
- Daily notes must not contain Obsidian wikilinks or local/relative Markdown links.
- Raw files are immutable source or instructional visual files, not graph/navigation nodes.
- Markdown image centering is a vault-level Obsidian CSS snippet concern; agents must not add per-page HTML or inline CSS to center images.
- Claude Code workflow confirmations must use `AskUserQuestion` rather than plain assistant questions.
- The only allowed top-level hidden directories are `.claude` and `.obsidian`.

### 2. Run Required Commands

Run the deterministic vault audit:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.claude\skills\second-brain-lint\scripts\deep_audit.ps1 -VaultRoot .
```

Validate all local skills:

```powershell
python <user-home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-ingest
python <user-home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-query
python <user-home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-lint
python <user-home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-journal
python <user-home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-graph-manager
python <user-home>\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\.claude\skills\second-brain-vault-audit
```

Check MCP and Basic Memory:

```powershell
claude mcp list
basic-memory status --project second-brain --json
```

### 3. Run Mechanical Scans

Run these additional checks:

- PowerShell parser check for `.claude/**/*.ps1`.
- JSON parse check for `.claude/*.json`, `.obsidian/*.json`, `~/.claude.json`, `~/.mcp.json`, and `~/.gemini/settings.json`.
- Hidden directory scan: only `.claude` and `.obsidian` are allowed.
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
- Config scan for stale MCP names:
  - `web-search-prime`
  - `web_search_prime`
  - `open.bigmodel.cn/api/mcp/web_search_prime`
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
- Valid instructional raw image embed such as `![[raw/diagram.png|600]]` from a wiki content page is allowed.
- Valid `wiki/*/_index.md` navigation links are allowed.
- Raw links from `wiki/*/_index.md` are blocked.

### 5. Manual Semantic Review

Do not rely only on deterministic scripts. Also review:

- Root `index.md` domain descriptions vs each `wiki/*/_index.md` scope summary.
- Domain taxonomy: suspicious one-off domains, overlapping domains, misplaced pages, unclear scope summaries.
- Content-page body links using weak markers such as `详见`, `参见`, `推荐`, `相关`, `See also`, or cross-domain links.
- Time-sensitive claims involving versions, prices, policies, regulations, salaries, release dates, model capabilities, API behavior, job markets, or market data.

Classify pages without inbound content-page links as informational unless another rule is violated. Do not add graph links merely to improve graph shape.

## Fix Policy

Apply safe mechanical fixes directly:

- Broken JSON syntax.
- PowerShell syntax errors.
- Forbidden scaffold deletion.
- Hook path mismatch.
- Clear contradiction between `CLAUDE.md`, `AGENTS.md`, local skills, and scripts.
- Missing mandatory ingest preflight wording.
- Stale `web-search-prime` MCP residue.
- `CLAUDE.md` / `AGENTS.md` sync drift when the project sync rule says they must match.

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
- All local skills validate.
- PowerShell scripts parse.
- JSON configs parse.
- Obsidian Markdown image centering snippet exists and is enabled.
- `basic-memory` is connected in Claude MCP and no forbidden web-search-prime server exists.
- `basic-memory status --project second-brain --json` is clean.
- Hidden directories are only `.claude` and `.obsidian`.
- No forbidden scaffold paths exist.
- Hook dry-runs prove both blocking and allowed examples.
- Router files, local skills, references, hooks, MCP behavior, Basic Memory behavior, and Obsidian config do not contradict each other.

If only informational items remain, report `clean` with an informational note.

## Windows Encoding

When reading or writing files with Chinese content in PowerShell, always specify UTF-8:

```powershell
Get-Content -Raw -Encoding UTF8 <path>
Set-Content -Encoding UTF8 <path>
```

Prefer `apply_patch` for manual edits. Use mechanical copy/write commands only for purely mechanical synchronization, and still use UTF-8.
