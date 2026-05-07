---
name: second-brain-ingest
description: Ingest sources into the user's Second Brain vault. Use when the user asks to "整理进第二大脑", "ingest", "沉淀到第二大脑", or wants pasted text, URLs, Web AI image URLs, raw files, discussions, research, or original thoughts turned into wiki pages. Requires domain-routing preflight before any wiki write or new-domain proposal, then handles source reading, image URL analysis/download, atomization, search-before-write, create-vs-update decisions, human confirmation, wiki page writing with semantic raw image embeds, domain index updates, manifest output, and journal handoff.
---

# Second Brain Ingest

Turn source material into durable wiki pages in `<vault-path>`.

This skill is a vault-specific fork of the prior upstream `wiki-ingest` framework. Keep the useful ingest workflow, but skip the upstream scaffold that conflicts with this vault.

## Execution Contract

Run this skill as a full ordered workflow, not as loose guidance. The user should not need to say "follow the skill carefully"; every ingest request already includes that requirement.

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

Offer `second-brain-journal` after every ingest. Ingest is not fully closed until journal coverage is written as plain text paths/slugs, or the user explicitly defers it. Daily notes must not contain wikilinks.

Before deciding a target domain, page split, create/update action, or new-domain proposal, read and follow `references/domain-routing.md`. This preflight is mandatory for pasted text, URLs, raw files, and discussion-context ingest.

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
4. Run the domain-routing preflight in `references/domain-routing.md`: read root `index.md`, read all `wiki/*/_index.md`, search existing pages, and classify each atom as update, create in existing domain, split, ambiguous, or proposed new domain.
5. Present a preflight manifest with 3-5 core findings, knowledge atoms, image asset manifest, candidate domains, candidate pages, recommended actions, confidence, excluded domains, and open questions. Do not write before the user confirms the manifest.
6. After confirmation, decide per candidate topic: update existing page, create new page in an existing domain, split across domains, or execute the approved new-domain subworkflow.
7. Write or edit wiki pages using `obsidian-markdown` syntax and the schema in `references/page-schema.md`. Place instructional raw image embeds at the nearest semantically relevant paragraph; do not append all images to the end as a gallery unless the page topic is explicitly an image catalog.
8. Update the relevant domain `_index.md`. Update root `index.md` only when creating a preflight-approved new domain.
9. Produce an ingest manifest listing preflight status, created pages, updated pages, domains, raw image assets, index changes, new-domain rationale if any, and journal status. Created/updated pages in the manifest should use `wiki/{domain}/{slug}.md` paths, not wikilinks.
10. Ask whether to write the journal. If yes, hand off to `second-brain-journal` with the manifest. If no or later, report `Journal pending: <pages>` and mark ingest as deferred.

## Search-Before-Write Decision Rules

Before using Basic Memory scores, verify the search result is not stale. When possible, check `basic-memory status --project second-brain --json`; if it reports new/modified/deleted/moves, or snippets contradict the file on disk, ignore Basic Memory scores and use the Grep fallback.

Filter Basic Memory results by `file_path` before deciding. Only `wiki/{domain}/{slug}.md` content pages are create/update candidates. `_index.md` and root `index.md` are navigation evidence only. Ignore `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.obsidian/**`, `daily/**`, `raw/**`, and deprecated scaffold paths as ingest candidates. Do not rely on Basic Memory's generic `type` field for page kind; use the file path.

Basic Memory scores:

| Score | Decision |
|---|---|
| `>= 0.75` | Update the existing page unless the body proves it is a different concept. |
| `0.50-0.75` | Show candidates to the user and ask whether this is the same topic. |
| `< 0.50` | Treat as a new concept after checking obvious exact-title conflicts. |

Grep fallback has no score. Classify only as `exact`, `related`, or `none`. `exact` and `related` require user confirmation before updating; only `none` may proceed to new-page creation after domain-routing preflight confirms the domain decision.

Always open candidate page bodies before deciding. Do not decide from title, tag, `_index.md`, or search snippet alone.

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
- Use raw image embeds only for images that materially explain the page: diagrams, screenshots, architecture figures, numerical examples, visual comparisons, or other instructional visuals. Syntax: `![[raw/file.png]]` or `![[raw/file.png|600]]`.
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

Basic Memory is the preferred MCP for `search_notes`, `write_note`, and `move_note` when available and synchronized. Always pass `project: second-brain` to Basic Memory MCP calls. For CLI fallback, use `basic-memory tool search-notes "<query>" --project second-brain --page-size <n>` and `basic-memory tool write-note ... --project second-brain`; do not rely on the current default project. Basic Memory 0.20.3 CLI does not expose `move-note`; filename correction should use MCP `move_note` when possible, or an explicit file/Obsidian move followed by `basic-memory reindex --project second-brain` and status verification.

Do not write or edit `permalink`; Basic Memory daemon owns it.

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
- Domain-routing preflight ran over root `index.md`, all `wiki/*/_index.md`, and page search results before any write or new-domain proposal.
- The user confirmed the preflight manifest, including domain placement, split granularity, create/update decisions, and any new-domain rationale.
- Search-before-write ran from either clean Basic Memory search or Grep fallback, and create/update/confirm decisions were made per topic.
- User-provided image URLs, if any, were analyzed, downloaded to `raw/` with semantic English kebab-case filenames, or explicitly reported as unusable.
- All written wiki page filenames are English kebab-case.
- Required frontmatter is present and source fields are semantically correct.
- No forbidden scaffold was created.
- Domain `_index.md` was synchronized.
- New domains updated root `index.md` and graph color verification ran.
- Manifest was generated with plain page paths rather than wikilinks.
- Any raw references are wiki content page body references: non-image/evidence references use explicit source/evidence/provenance sentences, and instructional image references use canonical `![[raw/image.ext]]` embeds at semantically relevant positions.
- Image centering was left to the global Obsidian CSS snippet, not implemented with per-page HTML or inline CSS.
- Journal was written or explicitly deferred.
