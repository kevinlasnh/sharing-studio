# Content Page Link Audit

Use this reference when creating, reviewing, deleting, or adding wikilinks between wiki content pages. For links to `raw/` files, use `raw-link-policy.md` instead.

## Core Model

A wiki content-page wikilink is a semantic dependency edge, not a tag, navigation shortcut, recommendation, ingest batch marker, raw provenance pointer, or Graph View decoration.

Explicit bidirectional body wikilinks are two independent semantic assertions:

- `A -> B`: A's body explains why B helps understand A.
- `B -> A`: B's body explains why A helps understand B.

Obsidian already provides backlink discovery. Do not add reverse body links merely to create backlinks or graph symmetry.

## Allowed Relationship Types

Allow a content-page link only when it fits at least one type:

- `prerequisite`: target is necessary background or a premise.
- `mechanism`: target explains a mechanism, cause, or consequence.
- `part-of`: target is a component, subproblem, or deeper decomposition.
- `contrast`: current page explicitly distinguishes or compares target.
- `evidence`: target is a representative case, counterexample, or evidence.
- `interpretation`: current page synthesizes, reinterprets, or personalizes target.

## Relationship Sentence Test

Before creating a link, write the relationship sentence:

```markdown
[[target]] 通过 <relationship type> 帮助解释当前页的 <specific paragraph/claim>.
```

If the sentence sounds like "also related", "possible application", "same batch", "same tag", "same emotion", or "both mention X", do not link.

The relationship sentence must appear in the body near the first wikilink. `related:` may only list links already supported in the body.

## Candidate Discovery

During ingest:

1. Run search-before-write.
2. Keep only 3-7 candidate pages for link judgment.
3. Open each candidate body. Do not judge from titles, tags, `_index.md`, or search snippets.
4. If the candidate is the same topic, update the existing page instead of creating a duplicate plus links.

During lint:

1. Use the Basic Memory-first freshness gate for broad semantic candidate discovery.
2. Use Grep / `rg` only as fallback when Basic Memory MCP/CLI cannot be trusted after one search-only reindex, or as a narrow mechanical aid for locating existing links.
3. Open the source and target page bodies before classifying an edge.

## Cross-Domain Rule

Cross-domain links require a stronger test:

```text
Understanding target changes or improves understanding of this page's actual argument.
```

Reject cross-domain links based only on shared vocabulary, application scenario, source batch, mood, or broad theme.

## Explicit Reverse Link Rule

Add a reverse body link only when all are true:

- The reverse direction has independent explanatory value for readers of the old page.
- The old page can naturally include its own relationship sentence.
- The relationship is symmetric or inverse, such as contrast, mutual components, reciprocal cases, or concept-confusion clarification.

Do not add reverse links when:

- The new page is a personal interpretation or synthesis of the old page.
- The old page is only background, prerequisite, or upper-level concept.
- The reverse link would turn the old page into a related-pages directory.

## Ten-Link Generality Test

If the same reason could justify links to 10 or more pages, the reason is too broad.

Use tags, `_index.md`, or a future overview/MOC page instead.

## Audit Classification

Classify candidate edges as:

- `keep`: body relationship sentence exists, type is clear, and target helps explain a specific claim.
- `delete`: frontmatter-only, naked "参见", common word, common tag, same ingest batch, emotion association, application-only relation, transitive补链, or weak reverse direction.
- `add`: current body already states a concept/mechanism/contrast/case that an existing page directly explains, and a natural relationship sentence can be inserted.
- `needs-user-confirmation`: relationship may be meaningful but requires domain judgment, merge/split decision, or personal preference.

For every `delete` or `add`, give one concrete reason. Do not say only "related" or "not related".

## Audit Boundary

Link audit is semantic. Basic Memory and Grep can find candidates but cannot decide validity.

Default behavior is report-only. Do not perform large-scale body rewrites without user confirmation.
