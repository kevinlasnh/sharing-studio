# Domain Routing Preflight

Use this reference before creating, updating, splitting, or proposing any wiki page or domain during ingest.

## Invariant

Never decide a target domain from the pasted source alone. First compare the source against the current vault structure, then ask the user to confirm the preflight manifest. In Claude Code, this confirmation must use `AskUserQuestion`. Writing before this confirmation is incomplete ingest.

## Domain Inventory

Build the inventory from disk, not memory:

1. Read root `index.md`.
2. Read every `wiki/*/_index.md`.
3. For each domain, capture:
   - domain slug,
   - index summary or scope sentence,
   - listed page titles/slugs,
   - recurring entities or methods,
   - nearest neighbor domains when obvious.
4. Treat `wiki/{domain}/_index.md` as navigation and scope evidence, not as a content page candidate.

If Basic Memory search returns index pages, keep them only as domain evidence. Page create/update decisions still require content page candidates or explicit `none`.

## Knowledge Atomization

Split the source before routing. A knowledge atom is the smallest unit that could independently be searched or placed.

Use these atom types:

- `concept`: reusable idea or theory.
- `entity`: person, tool, organization, product, protocol, project, or named object.
- `comparison`: A vs B, taxonomy, trade-off, ranking, or boundary.
- `procedure`: workflow, checklist, command sequence, operational playbook.
- `reference`: factual table, glossary, benchmark, protocol details, external standard.
- `original-thought`: user's personal synthesis, reflection, interpretation, or opinion.
- `evidence`: case, source excerpt, raw file, example, measurement, or anecdote supporting another atom.

Do not create a new domain for a single atom unless it also passes the new-domain gate.

## Retrieval Channels

For each atom, run enough retrieval to defend the placement:

1. Domain-level retrieval:
   - compare against root `index.md` descriptions,
   - compare against every domain `_index.md` summary and page list.
2. Page-level retrieval:
   - Basic Memory MCP `search_notes` with `project: second-brain` when synchronized,
   - CLI fallback: `basic-memory tool search-notes "<query>" --project second-brain --page-size 10`,
   - Grep fallback over `wiki/` and root `index.md` when Basic Memory is unavailable, stale, or contradictory.
3. Exact collision checks:
   - likely English slug,
   - Chinese title,
   - English title,
   - acronym,
   - aliases or near synonyms from the source.

Use 2-3 keyword combinations per atom. Include at least one broad domain phrase and one exact entity/title phrase.

## Decision States

Assign exactly one state per atom:

- `update-existing-page`: an existing page is the same core concept, entity, comparison, or problem.
- `create-page-in-existing-domain`: no existing page matches, but an existing domain clearly contains the atom.
- `split-across-existing-domains`: the source contains multiple atoms that belong in different existing domains.
- `ambiguous-ask-user`: two or more domains/pages are plausible, or confidence is weak.
- `propose-new-domain`: the atom set passes the new-domain gate below.

Do not use `propose-new-domain` because a topic is new to the current conversation. Use it only when the current vault taxonomy lacks a durable home.

## Confidence Labels

- `high`: one domain/page clearly dominates, and nearest alternatives are easy to reject.
- `medium`: one recommendation is better, but a neighboring domain has plausible overlap.
- `low`: sparse retrieval, unclear taxonomy boundary, or source contains mixed concepts.

`medium` and `low` decisions should be shown to the user with a concrete question.

## New-Domain Gate

A proposed new domain must satisfy all conditions:

1. Existing domains cannot reasonably contain the atom set.
2. The topic is not just a subpage, subheading, glossary entry, or evidence page inside an existing domain.
3. The domain is expected to hold multiple future pages, not a single isolated note.
4. A one-sentence scope note can be written.
5. At least two nearest existing domains are named with boundary reasons.
6. The user explicitly confirms creation after seeing the rejected alternatives.

If any condition fails, route to an existing domain or ask the user.

## Preflight Manifest

Before writing, present a concise manifest:

```text
preflight status: pending confirmation
source summary:
- <3-5 core findings>

domain inventory checked:
- root index: yes
- domain indexes checked: <N>
- search method: Basic Memory clean | Basic Memory stale + Grep | Grep only

knowledge atoms:
- atom: <short name>
  type: concept | entity | comparison | procedure | reference | original-thought | evidence
  candidate domains:
  - <domain> — <why>
  - <domain> — <why>
  candidate pages:
  - wiki/domain/page.md — exact | related | none
  recommendation: update-existing-page | create-page-in-existing-domain | split-across-existing-domains | ambiguous-ask-user | propose-new-domain
  confidence: high | medium | low
  excluded domains:
  - <domain> — <why not>
  question: <only if confirmation needed>

proposed writes:
- create/update: wiki/domain/slug.md
- index changes: wiki/domain/_index.md
- new domain: none | <domain + scope note + nearest-neighbor boundaries>
```

The user may confirm all, override a domain, ask for a split/merge, or defer ingest. Treat the user's confirmation as part of the ingest manifest.

## Write Rules After Confirmation

- Update existing pages before creating duplicates.
- Create a new page in an existing domain before proposing a new domain.
- Split across existing domains when the source has independent atoms for different reader contexts.
- Preserve original `source_type` and `source_date` when updating existing pages.
- Keep relationship wikilinks subject to `second-brain-lint/references/content-page-link-audit.md`.
