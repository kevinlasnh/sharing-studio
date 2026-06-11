# Raw Link Policy

Use this reference when creating, reviewing, deleting, or auditing references to `raw/` files.

## Core Model

`raw/` stores user-supplied immutable source material and user-provided image URL downloads. A raw file is provenance, evidence, or instructional visual material, not a concept note, navigation page, recommendation, or graph-connectivity device.

The knowledge node is the processed wiki content page. The raw file supports that page.

```text
wiki/{domain}/_index.md
  -> wiki/{domain}/{content-page}.md
       -> raw/source-file.ext
       -> ![[raw/instructional-image.png|600]]
```

For Web AI learning sessions, dragged browser image URLs are treated as user-provided image source assets: analyze the image, download it to `raw/`, name it by visual semantics, and embed it only where it explains the surrounding wiki content.

## Allowed Raw References

Allow raw references only from `wiki/{domain}/{content-page}.md` body text.

Use plain canonical `[[raw/file.ext]]` for non-image files and evidence/provenance-only images. The nearby sentence must make the source role explicit, such as:

```markdown
The source report is preserved as [[raw/source-file.pdf]] and supports the claim above.
```

The deterministic hook and audit expect plain raw link lines to contain explicit source/evidence/provenance language. Raw image embeds do not need provenance wording, but they still must not appear in weak reference, related reading, navigation, graph cleanup, or same-batch grouping context.

Use raw links for:

- primary source material supplied by the user,
- evidence for a specific claim,
- provenance for a page created from a file,
- reproducibility when a reader needs to inspect the original.

Use canonical image embeds for instructional visuals:

```markdown
![[raw/portrait-example.png|360]]
![[raw/cnn-convolution-numerical-example.png|600]]
```

Raw image embeds must include a numeric display width. Use `|360` for portrait images where the real width is smaller than the height; use `|600` for landscape and square images.

Image embeds are allowed only when the image materially explains the nearby content: diagrams, screenshots, architecture figures, numerical examples, visual comparisons, or other visual walkthroughs. Place the embed near the paragraph it clarifies instead of collecting all images at the bottom.

Do not add HTML wrappers, `<style>` blocks, or inline CSS solely to center raw image embeds. Obsidian display alignment is handled by the vault-level `.obsidian/snippets/second-brain-markdown-images.css` snippet, which centers standalone Markdown images and Obsidian image embeds globally.

## Link Syntax Contract

Use canonical vault-root raw targets:

```markdown
The source report is preserved as [[raw/source-file.pdf]] and supports the claim above.
![[raw/architecture-diagram.png|600]]
```

Do not embed non-image raw files:

```markdown
![[raw/source-file.pdf]]
```

Do not use relative, absolute, encoded, or differently cased raw targets such as `[[Raw/file.pdf]]`, `[[./raw/file.pdf]]`, `[[../raw/file.pdf]]`, `[[/raw/file.pdf]]`, or URL-encoded raw paths.

Do not link a raw attachment by bare filename, such as `[[source-file.pdf]]`; Obsidian can resolve that to `raw/source-file.pdf` while hiding that this is a raw provenance edge.

Do not use local Markdown attachment links such as `[source](source-file.pdf)` or `[source](../raw/source-file.pdf)` for provenance. If a sentence says source/evidence/provenance, the local attachment target must be canonical `[[raw/source-file.pdf]]`, even before the raw file exists.

## Forbidden Raw References

Do not link raw files from:

- root `index.md`,
- domain `_index.md`,
- `daily/*.md`,
- frontmatter `related:`,
- related/recommended-reading sections,
- graph cleanup or connectivity edits.

Do not add raw links merely because the raw file is in the same ingest batch or shares broad vocabulary with a page.

Do not use local Markdown links to raw files, such as `[source](../raw/file.pdf)`. Use canonical Obsidian raw references only from wiki content page bodies.

Do not create raw Markdown targets such as `[[raw/source.md]]`, even as unresolved placeholders. Raw Markdown targets can become unintended graph nodes; convert the original to `.txt`, `.pdf`, another attachment format, or ingest it into `wiki/`.

## Raw Markdown Boundary

Do not store Markdown notes under `raw/`. Raw Markdown can contain wikilinks and become an unintended graph participant.

If the user's original source is Markdown, use one of these:

- store it as `.txt` if preserving plain text is enough,
- store it as `.pdf` or another original attachment format,
- ingest it into `wiki/` as processed content instead of preserving it as raw Markdown.

## Audit Classification

- `keep`: content page body cites raw in an explicit source/evidence/provenance sentence for a specific claim, or embeds a raw image as nearby instructional visual content.
- `delete`: raw link appears in index, daily, frontmatter, related/recommendation text, or graph-connectivity edits.
- `needs-user-confirmation`: raw file identity, source ownership, or conversion format is unclear.
