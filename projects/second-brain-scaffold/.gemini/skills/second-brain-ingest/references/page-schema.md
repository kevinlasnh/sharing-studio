# Second Brain Page Schema

Load this reference when creating or repairing wiki pages or domain indexes.

## Content Page Path

`wiki/{domain}/{english-kebab-case}.md`

Rules:

- Filename: lowercase English kebab-case only.
- H1: human-readable title; Chinese is allowed.
- Cross-domain notes live in the main reader domain; add other domains as tags.
- Do not freely invent `permalink`; write or repair it by the deterministic path formula.
- Use multiline YAML lists. Both indented and unindented list items are acceptable because Basic Memory may dump unindented YAML.

## Content Page Frontmatter

```yaml
---
title: Page Title
type: concept | entity | comparison | procedure | reference
permalink: second-brain/wiki/ai-tools/page-title
domain: ai-tools
source_type: ai-chat
source_date: YYYY-MM-DD
related:
- '[[related-page]]'
created: YYYY-MM-DD
updated: YYYY-MM-DD
confidence: high | medium | low
tags:
- domain
- topic
---
```

Required fields: `title`, `type`, `permalink`, `domain`, `created`, `updated`.

Required on new ingest pages: `source_type`, `source_date`, `confidence`, `tags`.

Allowed `type`: `concept`, `entity`, `comparison`, `procedure`, `reference`.

Allowed `source_type`: `ai-chat`, `url`, `raw-file`, `original`.

Preserve `source_type` and `source_date` when updating an existing page. They anchor the original source, not the latest edit.

Use `confidence: low` when the page contains meaningful LLM inference, uncertain classification, or weak source coverage.

`related:` may include only core links already supported by a body relationship sentence. Never use frontmatter-only weak links.

`permalink` must equal `second-brain/wiki/{domain}/{slug}`, where `{slug}` is the filename without `.md`. Example: `wiki/robot-navigation-planning/hybrid-astar-path-planning.md` -> `permalink: second-brain/wiki/robot-navigation-planning/hybrid-astar-path-planning`.

## Domain Index Path

`wiki/{domain}/_index.md`

The filename must be exactly `_index.md`.

## Domain Index Frontmatter

```yaml
---
title: Domain Name Domain Index
type: index
permalink: second-brain/wiki/domain-name/index
domain: domain-name
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

Required fields: `title`, `type`, `permalink`, `domain`, `created`, `updated`.

`permalink` must equal `second-brain/wiki/{domain}/index`.

Forbidden on `_index.md`: `source_type`, `source_date`, `confidence`, `related`.

The body must include a scope summary line near the top:

```markdown
# Domain Name

> One-sentence scope note defining what belongs in this domain.
```

For a new domain, the scope note must match the approved domain-routing preflight and clarify the boundary from nearest neighbor domains when the boundary is easy to confuse.

Domain indexes link only to same-domain content pages. They do not link root `index.md`, daily notes, other `_index.md`, or cross-domain content pages as standalone entries.

## Root Index Entry

Root `index.md` is updated only for a new domain:

```markdown
- [[wiki/{domain}/_index|{domain}]] — one-sentence description
```

## Raw File References

Wiki content pages may cite user-supplied raw files with plain wikilinks such as `[[raw/file.pdf]]` when the raw file is source, evidence, or provenance for a specific claim. The same line should make the source/evidence/provenance role explicit.

Raw links must stay in content page body text. Do not place raw links in root `index.md`, domain `_index.md`, daily notes, or frontmatter `related`.

Wiki content pages may embed raw image files when the image is instructional content, such as a diagram, architecture figure, screenshot walkthrough, numerical example, visual comparison, or other visual explanation. Use Obsidian embed syntax near the paragraph the image clarifies:

```markdown
![[raw/example-portrait.png|360]]
![[raw/example-diagram.png|600]]
```

Raw image embeds must include a numeric display width. Use `|360` when the real image width is smaller than its height, and `|600` when the image is landscape or square.

Do not add HTML wrappers, `<style>` blocks, or inline CSS to center images. Image centering is a display concern handled globally by `.obsidian/snippets/second-brain-markdown-images.css`.

Do not embed non-image raw files. Cite PDFs, text files, datasets, reports, and evidence-only images as plain provenance links.

Use canonical vault-root `[[raw/file.ext]]` syntax only. Do not use `[[Raw/...]]`, `[[./raw/...]]`, `[[../raw/...]]`, `[[/raw/...]]`, URL-encoded raw paths, or other relative/absolute variants.

Do not link raw attachments by bare filename, such as `[[source.pdf]]`; the raw boundary must be visible in the link target.

Do not use local Markdown attachment links such as `[source](source.pdf)` or `[source](../raw/source.pdf)` for provenance. If a sentence says source/evidence/provenance, the local attachment target must be canonical `[[raw/file.ext]]`, even before the file exists.

Do not use raw links for navigation, recommended reading, same-batch grouping, or Graph View connectivity.

Do not store Markdown notes in `raw/`. Use `.txt`, `.pdf`, another original attachment format, or direct ingest into `wiki/`.

Do not create raw Markdown targets such as `[[raw/source.md]]`; unresolved raw Markdown links can still create graph clutter.

Daily notes must mention raw files and wiki pages as plain text paths, not wikilinks or local/relative Markdown links.
