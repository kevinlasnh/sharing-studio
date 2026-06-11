---
name: second-brain-lint
description: Health-check the user's Second Brain vault. Use when the user asks "审计一下第二大脑", "健康检查", "lint", "检查知识库", "审查链接", "检查双链", or wants wiki quality, dead links, daily no-link checks, raw provenance link boundaries, content pages without content-page inbound links, frontmatter, index consistency, taxonomy/domain drift, forbidden scaffold, stale claims, or semantic content-page link audit. Reports first, fixes only after confirmation.
---

# Second Brain Lint

Audit the vault. Report first. Fix only after user confirmation.

This skill is a vault-specific fork of the prior upstream `wiki-lint` framework. Keep health checks; remove dashboards, canvas output, auto stub creation, and automatic cross-reference insertion.

## Execution Contract

Run lint as a full ordered audit. The user should not need to say "follow the skill carefully"; every lint request already includes that requirement.

For a health check or full audit, cover all Fifteen Checks before reporting the audit complete. The deterministic script is required evidence, but it does not replace manual review for stale claims, taxonomy/domain governance, semantic content-page links, semantic fidelity drift, or root/domain index description drift. Stop early only for a real blocker such as a script/tool failure that prevents the requested scope; report the blocker and what was not checked.

In Claude Code, use the `AskUserQuestion` tool for every fix-pass confirmation, semantic-change confirmation, report-save decision, or ambiguous scope question. Do not ask these workflow questions as plain assistant text unless the current host does not expose that tool.

## Required Skill Stack

For any fix pass that writes `wiki/**/*.md`, activate `obsidian-markdown` before editing.

For graph color issues, hand off to `second-brain-graph-manager`.

For findings that require adding new knowledge or web-verified updates, hand off to `second-brain-ingest`. Lint evidence is not itself a wiki write.

For taxonomy/domain placement questions, use `../second-brain-ingest/references/domain-routing.md` as the semantic review model. Lint remains report-only unless the user confirms a fix pass.

For semantic fidelity questions, use `../second-brain-ingest/references/semantic-fidelity.md` as the audit vocabulary. Lint can flag likely over-compression, unsupported additions, missing caveats, chain breaks, false merges, provenance loss, or unresolved conflicts in existing pages. Lint cannot claim complete source-to-note coverage for a past ingest unless the original source or ingest manifest is available; otherwise report the finding as an audit suspicion and hand substantive rewrites back to `second-brain-ingest`.

## Basic Memory Use

Use Basic Memory for broad semantic candidate discovery, not for deterministic mechanical checks.

Apply the Basic Memory-first freshness gate before taxonomy/domain governance, missing-page candidate discovery, stale-claim neighborhood review, and semantic content-page link candidate discovery:

1. Run `basic-memory status --project second-brain --json`.
2. If status is dirty, run `basic-memory reindex --project second-brain --search` once, then re-check status.
3. If status is clean, use Basic Memory MCP `search_notes(project: second-brain)` for semantic candidates.
4. If MCP is unavailable but CLI search works, use `basic-memory tool search-notes "<query>" --project second-brain --page-size <n>`.
5. Use Grep / `rg` fallback only when MCP/CLI search is unavailable, one-shot reindex remains dirty, or Basic Memory snippets contradict opened disk files.

Filter semantic candidates by `file_path` before judging. Use `wiki/{domain}/{slug}.md` content pages for semantic lint targets. Treat `_index.md` and root `index.md` as navigation or scope evidence only. Exclude `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.claude/**`, `.agents/**`, `.gemini/**`, `.claudian/**`, `.workflows/**`, `.brv/**`, `.obsidian/**`, `templates/**`, `daily/**`, `raw/**`, and deprecated scaffold paths as semantic candidates.

Always open candidate page bodies before judging semantic issues. Mechanical checks such as dead links, frontmatter, raw boundaries, JSON, PowerShell syntax, forbidden scaffold, and daily no-link policy remain script/file-system checks.

## Fifteen Checks

Run checks in this order:

1. Dead links: visible wikilinks that point to no existing note/file.
2. Daily internal links: `daily/*.md` must not contain any `[[wikilink]]` or local/relative Markdown link; http(s) web links are allowed.
3. Raw reference boundaries: raw references must come only from wiki content page body text. Non-image/evidence references must use explicit source/evidence/provenance sentences with canonical `[[raw/file.ext]]`; instructional images may use canonical `![[raw/image.ext|360]]` portrait embeds or `![[raw/image.ext|600]]` landscape/square embeds. No missing/incorrect raw image widths, non-image raw embeds, bare attachment basename targets, local Markdown provenance attachment links, relative/absolute/case variants, index links, daily links, frontmatter links, related/recommendation/navigation text, same-batch grouping, graph-connectivity edits, or `[[raw/*.md]]` Markdown targets. See `references/raw-link-policy.md`.
4. Graph config: `.obsidian/graph.json` must keep the six color groups in contract order and the attachment-node CSS snippet must color raw attachments; do not require or auto-add a global `search` filter.
5. Markdown image display config: `.obsidian/snippets/second-brain-markdown-images.css` must exist, center Obsidian image embeds / standalone Markdown images, and be enabled in `.obsidian/appearance.json`.
6. Stale claims: claims likely outdated by date, version, regulation, price, API, or other time-sensitive facts.
7. Missing pages: index entries or repeated concrete concepts that imply an absent page.
8. Frontmatter gaps: content pages missing `title`, `type`, `domain`, `created`, or `updated`.
9. Empty sections: headings with no substantive body.
10. Stale index entries: root `index.md` and domain `_index.md` entries inconsistent with files, including misleading copied root-index descriptions that no longer match the domain `_index.md` summary.
11. `_index.md` frontmatter compliance: no `source_type`, `source_date`, `confidence`, or `related`; required fields present.
12. Forbidden scaffold: `wiki/log.md`, `wiki/hot.md`, `wiki/ingest-log.md`, `wiki/sources/**`, `wiki/overview.md`, `.raw/**`, `raw/**/*.md`, `wiki/index.md`, `wiki/meta/dashboard.md`, `wiki/meta/overview.canvas`, and `wiki/**/*.canvas`.
13. Taxonomy/domain governance: root domain entries and domain `_index.md` summaries should describe stable scopes; flag suspicious one-off domains, overlapping domains, pages that appear likely misplaced, or missing/unclear domain summaries. Do not move pages automatically.
14. Content-page link audit: semantic review of wiki content page links using `references/content-page-link-audit.md`.
15. Semantic fidelity audit: report-only review for likely semantic drift, over-compression, unsupported additions, false merges, chain breaks, provenance loss, unresolved conflicts, and missing limitations/counterexamples/open questions. Do not claim full reconstruction of source coverage without the original source or ingest manifest.

Report wiki content pages with no inbound content-page links as informational only. Do not auto-add links to fix graph shape.

## Deterministic Audit

Use `scripts/deep_audit.ps1` for the deterministic pass:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .claude\skills\second-brain-lint\scripts\deep_audit.ps1 -VaultRoot .
```

The script reports JSON for mechanical checks: forbidden scaffold, filenames, frontmatter, graph config, Markdown image display config, dead links, daily internal links, raw reference boundary/context violations, invalid raw embeds, bare raw attachment basename targets, local Markdown provenance attachment links, noncanonical raw targets, raw Markdown files and raw Markdown link targets, link boundary violations, unsupported frontmatter-only `related`, content pages without content inbound links, duplicate basenames, standard markdown internal links, inline YAML arrays, bad callouts, root/domain index coverage, domain scope summaries, and Basic Memory sync cleanliness.

Use `scripts/export_links.ps1` when you need raw candidate wikilink edges for semantic review:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .claude\skills\second-brain-lint\scripts\export_links.ps1 -VaultRoot .
```

`export_links.ps1` outputs JSON rows containing source, target, line, context, same-domain, reciprocal, and frontmatter-only signals. Treat link rows as evidence, not as the final semantic judgment.

After the deterministic pass, manually compare each root `index.md` domain description with that domain's `_index.md` summary. Fix copied or misleading descriptions as stale index entries, then re-run the deterministic pass and Basic Memory status.

For taxonomy/domain governance, use the domain inventory pattern from `second-brain-ingest/references/domain-routing.md`: compare root `index.md`, all `wiki/*/_index.md`, page lists, and nearest-neighbor domains. Classify findings as `needs-confirmation` unless the issue is purely mechanical, such as a missing domain index.

## Report Categories

Report findings in three categories:

- `auto-fixable`: mechanical and low-risk after confirmation, such as stale index entry repair, dead link path correction, missing required frontmatter with known values, or forbidden scaffold deletion.
- `needs-confirmation`: semantic link deletion/addition, stale claim rewrite, domain merge/split/move decisions, new-domain scope changes, or anything that changes meaning.
- `informational`: risks, style drift, broad observations, pages with no inbound content-page links, or checks that need no action.

## Output Rules

Default output stays in the conversation. Do not create lint report files.

If the user asks to save a report, hand off to `second-brain-journal` and append a concise lint summary to `daily/YYYY-MM-DD.md`. The saved summary must use plain text paths and must not contain wikilinks or local/relative Markdown links.

Never create `wiki/meta/lint-report-YYYY-MM-DD.md`, `wiki/meta/dashboard.md`, or `.canvas` files.

## Fix Pass

Before fixing, ask for confirmation unless the user already gave explicit permission.

When fixing:

1. Activate `obsidian-markdown` before editing wiki markdown.
2. Apply only the confirmed changes.
3. Re-run the affected checks.
4. If the fix changed any Markdown under `wiki/`, `daily/`, root `index.md`, `CLAUDE.md`, `AGENTS.md`, or `GEMINI.md`, run Basic Memory sync closure: status, `basic-memory reindex --project second-brain --search` if dirty, then status again.
5. End as `clean` or `residual-risk`.

`clean`: no unresolved issues in the rerun scope.

`residual-risk`: list remaining issues, why they remain, and the next action.

## Completion Criteria

Report blockage or `residual-risk` instead of `clean` if any applicable item is missing:

- `scripts/deep_audit.ps1` ran successfully, or its failure was reported as a blocker.
- All Fifteen Checks were covered in the requested scope.
- Manual semantic checks were performed where the deterministic script is insufficient.
- Basic Memory freshness was considered when it affects lint evidence.
- Broad semantic lint candidate discovery used the Basic Memory-first freshness gate, with Grep fallback reported only when Basic Memory could not be trusted.
- Findings are categorized as `auto-fixable`, `needs-confirmation`, or `informational`.
- No fix was applied before user confirmation.
- Any fix pass re-ran the affected checks.
- Any Markdown-changing fix pass ran Basic Memory sync closure or reported residual-risk.
- Pages without inbound content-page links are reported as informational, not errors.

## Forbidden Upstream Behavior

Never follow these upstream `wiki-lint` behaviors in this vault:

- Create Dataview dashboards.
- Generate canvas maps.
- Automatically create stub pages.
- Automatically add missing cross-references from unlinked mentions or from pages with no inbound content-page links.
- Add raw links for navigation, recommended reading, same-batch grouping, or Graph View connectivity.
- Save reports under `wiki/meta/`.
- Treat Graph View connectivity as a reason to add links.
