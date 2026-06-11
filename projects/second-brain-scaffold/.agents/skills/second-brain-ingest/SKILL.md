---
name: second-brain-ingest
description: Ingest sources into the user's Second Brain vault. Use when the user asks to "整理进第二大脑", "ingest", "沉淀到第二大脑", or wants pasted text, URLs, Web AI image URLs, raw files, discussions, research, or original thoughts turned into wiki pages. Requires semantic fidelity pass and domain-routing preflight before any wiki write or new-domain proposal, then handles source reading, image URL analysis/download, atomization, semantic-unit planning, search-before-write, create-vs-update decisions, human confirmation, wiki page writing with semantic raw image embeds, coverage audit, domain index updates, manifest output, and journal handoff.
---

# Second Brain Ingest

Turn source material into durable wiki pages in `<vault-path>`.

This skill is a vault-specific fork of the prior upstream `wiki-ingest` framework. Keep the useful ingest workflow, but skip the upstream scaffold that conflicts with this vault.

## Execution Contract

Run this skill as a full ordered workflow, not as loose guidance. The user should not need to say "follow the skill carefully"; every ingest request already includes that requirement.

Semantic fidelity is a hard gate, not a post-hoc quality note. A valid ingest has a visible prewrite semantic unit ledger before domain routing and user confirmation, and a postwrite coverage audit before the final manifest. If any wiki/raw/index write happens before the confirmed Semantic Coverage Plan, treat the run as non-compliant: stop, report the ordering violation, reconstruct the missing semantic plan from the original source, ask the user to confirm the corrective plan, then audit and repair the written pages before journal handoff. Do not call the ingest complete until that corrective path has zero P0/P1 residual risk, or the remaining residual risk is explicitly reported.

Allowed pause points:

- The preflight manifest requires user confirmation before any wiki write.
- A new-domain proposal requires explicit user confirmation.
- The journal handoff requires a user yes/no unless the user already made the preference explicit.
- A source, tool, or permission is genuinely unavailable.

After a pause is resolved, continue from the next workflow step. Do not summarize early after only reading sources, atomizing, searching, or presenting preflight. Before the final response, compare the work against the Completion Criteria and report `blocked` or `deferred` instead of `complete` if any required closure item is missing.

In Claude Code, every pause point or user confirmation must use the `AskUserQuestion` tool. Do not ask preflight, create/update, new-domain, same-topic, or journal yes/no questions as plain assistant text unless the current host does not expose that tool.

## Required Skill Stack

Before writing any `wiki/**/*.md` file, activate `obsidian-markdown`.

Use `second-brain-lint`'s content-page link audit rules when creating or editing wikilinks. If the rules are not already loaded and you need to decide content-page links, read `../second-brain-lint/references/content-page-link-audit.md`.

Use `second-brain-lint`'s raw link rules when ingesting, embedding, or citing user-supplied files and downloaded image URL assets. Read `../second-brain-lint/references/raw-link-policy.md` before adding any raw provenance link, raw image embed, or local source/evidence/provenance attachment reference.

Use `second-brain-graph-manager` after new domain creation to verify graph color groups.

Offer `second-brain-journal` after every ingest. Ingest is not fully closed until journal coverage is written as plain text paths/slugs and the journal-triggered Basic Memory + Hugging Face backup closures finish, or the user explicitly defers the journal. Daily notes must not contain wikilinks.

Before deciding a target domain, page split, create/update action, or new-domain proposal, read and follow `references/domain-routing.md`. This preflight is mandatory for pasted text, URLs, raw files, and discussion-context ingest.

Before domain-routing preflight and after wiki writes, read and follow `references/semantic-fidelity.md`. Ingest is not summarization; it may refine, deduplicate, and reorganize sources only while preserving key meaning, reasoning chains, premises, constraints, counterexamples, decisions, self-corrections, and open questions. The prewrite Semantic Fidelity Pass must produce a visible Semantic Coverage Plan; the later Coverage Audit verifies that plan and cannot replace it.

## Source Priority

When multiple source channels are present, set the page `source_type` from the highest-priority channel:

| Priority | Channel | Meaning | source_type |
|---|---|---|---|
| 1 | A | User-supplied files in `raw/`, or user-provided image URLs downloaded into `raw/` as primary source assets | `raw-file` |
| 2 | C | User-provided non-image URL fetched for this ingest | `url` |
| 3 | B | Pasted user text | `ai-chat` |
| 4 | D | Current user/agent discussion context | `ai-chat` |

Only channel A and user-provided image URL assets are stored in `raw/`. Non-image URLs, pasted text, and discussion context are not copied into `raw/`.

If a Web AI chat transcript plus dragged image URLs are ingested together, set the page `source_type` from the dominant knowledge source: usually `ai-chat` for the processed chat content, while the downloaded images remain `raw/` instructional assets embedded in the page.

Raw files are immutable source or visual material. Do not store generated summaries, fetched webpages, pasted text, or discussion context in `raw/`.

## Workflow

1. Read the source completely.
2. Detect user-provided image URLs in pasted text or terminal-dragged URL lists. For each image URL, fetch/read the image, perform multimodal analysis, decide whether it is an instructional image, evidence image, or irrelevant/unusable asset, and download usable images into `raw/` with English kebab-case names based on image semantics.
3. Atomize the source into candidate knowledge atoms before choosing files or domains. Treat analyzed image content as source material, not as decorative media.
4. Run the Semantic Fidelity Pass in `references/semantic-fidelity.md`: choose Light / Standard / Full, extract semantic units, assign id/type/importance/source_ref/loss_risk/proposed_target/proposed_action, and mark confirmation-required high-risk items. This is a stop gate: do not run domain-routing preflight, propose pages, or write files until the semantic unit ledger exists. Keep knowledge atoms for routing, but do not treat atomization as semantic coverage.
5. Run the domain-routing preflight in `references/domain-routing.md`: read root `index.md`, read all `wiki/*/_index.md`, search existing pages, and classify each atom as update, create in existing domain, split, ambiguous, or proposed new domain.
6. Present a preflight manifest with 3-5 core findings, knowledge atoms, Semantic Coverage Plan, image asset manifest, candidate domains, candidate pages, recommended actions, confidence, excluded domains, and open questions. The Semantic Coverage Plan must show the required semantic-unit rows for the chosen fidelity level, not only counts or a prose summary. Do not write before the user confirms the manifest.
7. After confirmation, decide per candidate topic: update existing page, create new page in an existing domain, split across domains, or execute the approved new-domain subworkflow.
8. Write or edit wiki pages using `obsidian-markdown` syntax and the schema in `references/page-schema.md`. Place instructional raw image embeds at the nearest semantically relevant paragraph; do not append all images to the end as a gallery unless the page topic is explicitly an image catalog.
9. Run the Coverage Audit Pass in `references/semantic-fidelity.md`: verify every P0/P1 unit has status `preserved`, `rewritten`, `merged`, `deferred`, `discarded`, or `superseded`; verify final-note key claims have source support or are explicitly marked as agent inference; report failure types; trigger confirmation for unresolved high-risk items. If the prewrite semantic unit ledger is missing, this audit is invalid as a substitute; follow the non-compliance recovery path instead of silently backfilling.
10. Update the relevant domain `_index.md`. Update root `index.md` only when creating a preflight-approved new domain.
11. Produce an ingest manifest listing preflight status, retrieval method, semantic fidelity level, Semantic Coverage Result, created pages, updated pages, domains, raw image assets, index changes, new-domain rationale if any, journal status, Basic Memory sync status, and Git/Hugging Face backup status when journal is written. Created/updated pages in the manifest should use `wiki/{domain}/{slug}.md` paths, not wikilinks.
12. Ask whether to write the journal. If yes, hand off to `second-brain-journal` with the manifest and let journal perform the final Basic Memory closure and `second-brain-hf-backup` handoff after the daily write. If no or later, report `Journal pending: <pages>`, then run the Basic Memory sync closure for the already-written wiki/raw/index changes before returning; mark ingest as deferred only for the journal and HF backup.

## Semantic Fidelity Levels

All levels must identify P0/P1 semantic units. Light mode may compress P1 reporting only after confirming P1 has a disposition; it may not skip P1 coverage.

- `Light`: short material or one simple concept. List P0 semantic units explicitly. If P1 units exist, summarize their disposition and confirm no P1 residual-risk remains. Audit P0 and P1 summary coverage.
- `Standard`: default. List P0/P1 semantic units and audit P0/P1 coverage.
- `Full`: long text, multi-turn discussion, user asks for maximum completeness, or material contains decisions, counterexamples, constraints, self-corrections, or many P0/P1 units. Segment the source, list P0/P1/P2, and run full coverage audit.

Upgrade when the user asks for completeness, the source is long or multi-topic, there are counterexamples/constraints/decisions/self-corrections, or the agent identifies many P0/P1 units.

## Semantic Coverage Manifest Fields

Preflight manifests must include:

```text
semantic fidelity level: Light | Standard | Full

semantic coverage plan:
| id | type | importance | source_ref | proposed_target | proposed_action | loss_risk | confirmation |
|----|------|------------|------------|-----------------|-----------------|-----------|--------------|
```

Preflight semantic coverage must be inspectable before the user confirms the write:

- `Light`: explicit P0 rows; P1 may be summarized only when every P1 has a disposition and no P1 residual-risk remains.
- `Standard`: explicit rows for every P0 and P1 unit.
- `Full`: explicit rows for every P0, P1, and P2 unit selected by the source segmentation.
- Counts alone, such as "25 P0 / 18 P1", are not a valid Semantic Coverage Plan.

Final ingest manifests must include:

```text
semantic coverage result:
| id | status | target_page | target_section | failure_type | residual_risk |
|----|--------|-------------|----------------|--------------|---------------|
```

Field constraints:

- `importance` must be `P0`, `P1`, or `P2`.
- `loss_risk` must be `HIGH`, `MED`, or `LOW`.
- `status` must be `preserved`, `rewritten`, `merged`, `deferred`, `discarded`, or `superseded`.
- P0 `deferred`, P0 `discarded`, unresolved high-risk `merged`, ambiguous `meta-correction`, and source support gaps must trigger user confirmation or residual-risk reporting.

## Semantic Fidelity Non-Compliance Handling

Use this recovery path only when the normal gate order was violated:

1. Stop before any further wiki/raw/index writes or journal handoff.
2. Report the exact missing gate: skipped prewrite ledger, counts-only preflight, missing user confirmation, or missing postwrite audit.
3. Reopen the original source material and rebuild the Semantic Coverage Plan from source, not from the already-written wiki pages.
4. Ask the user to confirm the corrective Semantic Coverage Plan before treating the written pages as accepted.
5. Audit the already-written pages against that confirmed plan and repair omissions, unsupported additions, over-compression, false merges, chain breaks, provenance loss, or unresolved conflicts.
6. The final manifest and journal handoff must label the run as corrected after semantic non-compliance and include any residual-risk.

Do not use this recovery path as the default workflow. A normal ingest must pass the prewrite gate before writing.

## Search-Before-Write Decision Rules

Use Basic Memory-first retrieval for every atom before creating or updating pages.

Freshness gate:

1. Run `basic-memory status --project second-brain --json` before semantic page search.
2. If status is clean, use Basic Memory MCP `search_notes` with `project: second-brain`.
3. If status reports `new`, `modified`, `deleted`, `moves`, or `skipped_files`, run `basic-memory reindex --project second-brain --search` once, then run status again.
4. If the second status is clean, use Basic Memory MCP `search_notes`.
5. If MCP is unavailable but Basic Memory CLI works, use `basic-memory tool search-notes "<query>" --project second-brain --page-size <n>` before any Grep fallback.
6. Use Grep / `rg` fallback only when MCP and CLI search are unavailable, the one-shot reindex fails or remains dirty, or Basic Memory snippets contradict the opened disk file.
7. Record the actual retrieval method in the preflight and ingest manifest: `Basic Memory MCP clean`, `Basic Memory MCP after reindex`, `Basic Memory CLI`, or `Grep fallback: <reason>`.

Grep fallback is an exception path, not the normal ingest path. When used, report the fallback reason and Basic Memory residual-risk; do not silently create pages as if semantic search had succeeded.

Filter Basic Memory results by `file_path` before deciding. Only `wiki/{domain}/{slug}.md` content pages are create/update candidates. `_index.md` and root `index.md` are navigation evidence only. Ignore `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.claude/**`, `.agents/**`, `.gemini/**`, `.claudian/**`, `.workflows/**`, `.brv/**`, `.obsidian/**`, `templates/**`, `daily/**`, `raw/**`, and deprecated scaffold paths as ingest candidates. Do not rely on Basic Memory's generic `type` field for page kind; use the file path.

Basic Memory scores:

| Score | Decision |
|---|---|
| `>= 0.75` | Update the existing page unless the body proves it is a different concept. |
| `0.50-0.75` | Show candidates to the user and ask whether this is the same topic. |
| `< 0.50` | Treat as a new concept after checking obvious exact-title conflicts. |

Grep fallback has no score. Classify only as `exact`, `related`, or `none`. `exact` and `related` require user confirmation before updating; only `none` may proceed to new-page creation after domain-routing preflight confirms the domain decision.

Always open candidate page bodies before deciding. Do not decide from title, tag, `_index.md`, or search snippet alone.

## Basic Memory Sync Closure

If journal is written in the same ingest workflow, `second-brain-journal` owns the final Basic Memory adaptive reindex closure after the daily file write, and then must hand off to `second-brain-hf-backup` for full Git snapshot push.

If the user defers the journal after wiki/raw/index changes were already written, run an interim search-only sync closure before returning. This prevents Basic Memory from staying file-index dirty. The final search + embeddings checkpoint and Hugging Face backup remain owned by `second-brain-journal` when the journal is later written.

```powershell
basic-memory status --project second-brain --json
basic-memory reindex --project second-brain --search
basic-memory status --project second-brain --json
```

Skip the search-only reindex command when the first status is already clean. If the final status is dirty or any command fails, report `residual-risk` and include the status details. The final ingest response must not say Basic Memory file sync is clean unless the post-write status check proves it. If the journal is deferred, also report that the full embeddings checkpoint and Hugging Face backup are deferred until the journal write.

## New Page vs Update Existing Page

Update an existing page when the new material is the same core concept, entity, comparison, or problem. Preserve the page's original `source_type` and `source_date`; update only `updated: YYYY-MM-DD`.

Create a new page when the material is an independent concept, subproblem, comparison, case, evidence page, or personal interpretation that should be independently queried later, and the preflight manifest has assigned it to an existing or approved new domain.

Do not create duplicate pages and connect them with links to hide duplication.

## Raw File Handling

For user-supplied raw files and user-provided image URLs:

- Keep files only under root `raw/`.
- Do not create `wiki/sources/**`, `.raw/**`, or domain-local raw folders.
- Do not add raw links to root `index.md`, domain `_index.md`, daily notes, or frontmatter `related`.
- For terminal-dragged or pasted image URLs, fetch/read the image, perform multimodal analysis, name it by visual semantics, and download it to `raw/{english-kebab-case}.{ext}`. Use the response `Content-Type` or URL extension to preserve `.png`, `.jpg`, `.jpeg`, `.webp`, or `.gif`; avoid opaque names such as `image-1.png` unless no semantic name is possible.
- Use raw image embeds only for images that materially explain the page: diagrams, screenshots, architecture figures, numerical examples, visual comparisons, or other instructional visuals. Always include a numeric display width: use `![[raw/file.png|360]]` for portrait images where the real width is smaller than the height, and `![[raw/file.png|600]]` for landscape or square images.
- Place raw image embeds near the paragraph they clarify, usually after the explanatory sentence or before a detailed walkthrough. Do not put every image at the bottom.
- Do not wrap image embeds in HTML, `<style>`, or inline CSS for centering. The vault's global `.obsidian/snippets/second-brain-markdown-images.css` snippet centers image embeds in Obsidian display; keep Markdown content canonical.
- Cite non-image raw files, and image files used only as evidence/provenance, from wiki content page body text in an explicit source/evidence/provenance sentence using plain `[[raw/file.ext]]`.
- Do not embed non-image raw files with `![[raw/...]]`.
- Do not use `[[Raw/...]]`, `[[./raw/...]]`, `[[../raw/...]]`, `[[/raw/...]]`, URL-encoded raw paths, or other relative/absolute variants. Use canonical vault-root `[[raw/file.ext]]` only.
- Do not link raw attachments by bare filename, such as `[[source.pdf]]`; Obsidian may resolve that to `raw/source.pdf` while hiding the provenance boundary.
- Do not use local Markdown attachment links such as `[source](source.pdf)` or `[source](../raw/source.pdf)` for provenance. If a sentence says source/evidence/provenance, the local attachment target must be canonical `[[raw/file.ext]]`, even before the file exists.
- Use raw references only as source/evidence/provenance or instructional visual embeds for a specific nearby explanation, never as navigation, recommendation, same-batch marker, or graph-connectivity edge.
- Do not store Markdown under `raw/`; if the user's original is Markdown, use `.txt`, `.pdf`, another original attachment format, or direct ingest into `wiki/`.
- Do not create raw Markdown targets such as `[[raw/source.md]]`, even as unresolved placeholders.

## New Domain Subworkflow

This subworkflow is reachable only from a confirmed preflight manifest whose decision state is `propose-new-domain`. Pause the main ingest and execute all steps:

1. Show why the nearest existing domains cannot contain the material, using the new-domain gate in `references/domain-routing.md`.
2. Ask the user to confirm the domain slug, scope note, nearest-neighbor boundaries, and creation.
3. Create `wiki/{domain}/`.
4. Trigger `second-brain-graph-manager` to verify graph color groups.
5. Create `wiki/{domain}/_index.md`.
6. Add one root index entry to `index.md` using `[[wiki/{domain}/_index|{domain}]] — description`.
7. Remind the user to write a journal entry for the structural change without daily wikilinks.

Self-check before returning to ingest:

- `wiki/{domain}/_index.md` exists with the exact filename `_index.md`.
- Root `index.md` has the domain entry.
- The preflight manifest records the rejected existing domains and the approved scope note.
- Graph manager verification was performed.
- Journal reminder was issued and must not require daily wikilinks.

## Filename and Basic Memory Rules

Basic Memory is the preferred MCP for `search_notes`, `write_note`, and `move_note` when available and synchronized, but it is not the only valid writer for this vault. Always pass `project: second-brain` to Basic Memory MCP calls. For CLI fallback, use `basic-memory tool search-notes "<query>" --project second-brain --page-size <n>` and `basic-memory tool write-note ... --project second-brain`; do not rely on the current default project. Basic Memory CLI fallback remains preferred over Grep for semantic retrieval. Basic Memory 0.20.3 CLI does not expose `move-note`; filename correction should use MCP `move_note` when possible, or an explicit file/Obsidian move followed by `basic-memory reindex --project second-brain` and status verification.

Basic Memory `ensure_frontmatter_on_sync` is disabled for this Google DriveFS vault. Do not rely on the daemon to add or repair frontmatter. The daemon indexes files; the vault schema owns deterministic frontmatter.

Do not freely invent `permalink`. When creating or repairing Markdown, write or correct it by path formula:

- `wiki/{domain}/{slug}.md` -> `permalink: second-brain/wiki/{domain}/{slug}`
- `wiki/{domain}/_index.md` -> `permalink: second-brain/wiki/{domain}/index`

After any create, move, or filename correction, verify the file exists, is non-empty, has readable frontmatter, and the `permalink` matches the final path.

Use English titles with `write_note`; Chinese belongs in H1/body. After every `write_note`, verify the actual filename. If it is not lowercase English kebab-case, or if `_index.md` was generated as another name, immediately fix it with `move_note`.

Known filename hazards: Chinese titles, `and`/`or`, numbers, punctuation, and `_index.md`.

## Forbidden Upstream Scaffold

Never create or update these upstream `wiki-ingest` artifacts:

- `wiki/log.md`, `wiki/hot.md`, `wiki/ingest-log.md`
- `wiki/sources/**`
- `.raw/**`, `.raw/.manifest.json`, `.raw/articles/**`
- `raw/**/*.md`
- `wiki/overview.md`, `wiki/index.md`
- `wiki/meta/dashboard.md`, `wiki/meta/overview.canvas`

Use root `raw/`, page frontmatter, daily journal, root `index.md`, and Obsidian Graph View instead.

## Completion Criteria

Report blockage instead of claiming completion if any item is missing:

- Source material was fully read, or unsupported/damaged/unfetchable sources were reported.
- Semantic Fidelity Pass ran before domain-routing preflight, with P0/P1 semantic units identified for the chosen fidelity level.
- The preflight manifest exposed the required Semantic Coverage Plan rows for the chosen fidelity level, and the user confirmed that plan before any wiki/raw/index write.
- The semantic fidelity process was not only performed retroactively. If recovery was needed, the final manifest labels the run as corrected after semantic non-compliance and reports any residual-risk.
- Domain-routing preflight ran over root `index.md`, all `wiki/*/_index.md`, and page search results before any write or new-domain proposal.
- The user confirmed the preflight manifest, including domain placement, split granularity, create/update decisions, Semantic Coverage Plan, high-risk semantic confirmation items, and any new-domain rationale.
- Search-before-write ran through the Basic Memory-first freshness gate; if dirty, one `--search` reindex was attempted before any Grep fallback.
- Grep fallback, if used, was reported with the reason and residual-risk.
- User-provided image URLs, if any, were analyzed, downloaded to `raw/` with semantic English kebab-case filenames, or explicitly reported as unusable.
- All written wiki page filenames are English kebab-case.
- Required frontmatter is present, source fields are semantically correct, and `permalink` matches the deterministic path formula.
- No forbidden scaffold was created.
- Domain `_index.md` was synchronized.
- New domains updated root `index.md` and graph color verification ran.
- Coverage Audit Pass ran after wiki writes and before the final ingest manifest; every P0/P1 unit has a status or residual-risk.
- Manifest was generated with plain page paths rather than wikilinks and included retrieval method, semantic fidelity level, Semantic Coverage Result, Basic Memory sync status, and Git/Hugging Face backup status when journal is written.
- Any raw references are wiki content page body references: non-image/evidence references use explicit source/evidence/provenance sentences, and instructional image references use canonical `![[raw/image.ext|360]]` or `![[raw/image.ext|600]]` embeds at semantically relevant positions.
- Image centering was left to the global Obsidian CSS snippet, not implemented with per-page HTML or inline CSS.
- Journal was written and completed its Basic Memory + Hugging Face backup closures, or was explicitly deferred while Basic Memory sync closure still ran for already-written wiki/raw/index changes.
