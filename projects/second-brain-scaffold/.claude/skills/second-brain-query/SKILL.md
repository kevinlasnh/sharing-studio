---
name: second-brain-query
description: Query the user's Second Brain vault without writing files. Use when the user asks "检查下我的第二大脑", "查旧知识", "第二大脑里有没有", "what do I know about", or asks where a topic should live in the Second Brain. Uses Basic Memory search first, Grep fallback, indexes as navigation only, domain-placement mode for read-only routing advice, daily only for explicit journal/timeline evidence, synthesis with wikilink citations for wiki pages, and explicit handoff to ingest for any write or web expansion.
---

# Second Brain Query

Answer from the existing vault. Query is read-only.

This skill is a vault-specific fork of the prior upstream `wiki-query` framework. Keep strategic retrieval and synthesis; remove hot cache, query filing, auto web search, and writeback.

## Execution Contract

Run the retrieval workflow completely before answering. The user should not need to say "follow the skill carefully"; every query request already includes that requirement.

Do not answer from the first search snippet, title, or index entry alone. Read the needed source page bodies, apply path filters, use Grep fallback when Basic Memory is stale or unavailable, and only then synthesize. Stop early only when the query is ambiguous enough to require scope clarification, or when no retrieval channel can run; in those cases, report the blocker instead of giving a partial answer as complete.

In Claude Code, use the `AskUserQuestion` tool for every scope clarification, "open page vs ingest" decision, or same-topic confirmation. Do not ask these workflow questions as plain assistant text unless the current host does not expose that tool.

## Read-Only Boundary

Do not write any file.

Do not create pages, fix links, update indexes, append journals, or save answers. If the user wants to keep or expand the result, explicitly hand off to `second-brain-ingest`.

Do not use WebSearch/WebFetch inside Query. Web is an ingest source, not a query fallback.

## Retrieval Order

Default path:

1. Use Basic Memory `search_notes` with `project: second-brain` when available and synchronized. For CLI fallback, use `basic-memory tool search-notes "<query>" --project second-brain --page-size <n>`; do not rely on the current default project.
2. Filter results by `file_path`: use `wiki/{domain}/{slug}.md` content pages as answer sources, `_index.md` and root `index.md` as navigation only. Exclude `daily/**` by default; use daily notes only when the user explicitly asks for journal, timeline, or session-history evidence.
3. Ignore `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.obsidian/**`, `raw/**`, and deprecated scaffold paths as answer sources. Raw files are provenance/evidence/instructional visual attachments, not query answer nodes.
4. Read the top matching wiki pages needed to answer.
5. Follow only high-value wikilinks from wiki content pages that materially improve the answer. Do not use daily notes as graph traversal sources; when explicitly requested, daily notes are plain file/date evidence only.
6. Synthesize with wikilink citations.

Do not rely on Basic Memory's generic `type` field for page kind; use `file_path`.

Fallback when Basic Memory is unavailable or stale:

1. Grep `wiki/` and root `index.md`. Add `daily/` only for explicit journal, timeline, or session-history questions.
2. Classify results as `exact`, `related`, or `none`.
3. Do not invent hybrid search scores.

Daily results are not knowledge pages. When explicitly requested, cite them by plain file path and date only; do not return them as wikilinks, backlinks, or related-note edges.

Raw file paths may be mentioned only as provenance already cited by a wiki content page. Do not traverse from raw files or treat them as related notes.

Treat Basic Memory as stale when `basic-memory status --project second-brain --json` reports new/modified/deleted/moves, or when search snippets contradict the file on disk. Query remains read-only: do not repair or reindex from this skill; report the stale index and use Grep fallback.

Index-first path:

Use root `index.md -> wiki/{domain}/_index.md -> content page` only when the user explicitly asks to start from the index/catalog or when search results are too broad.

Domain-placement path:

Use this read-only mode when the user asks where a pasted topic belongs, whether a new domain is needed, or how to classify a future ingest. Read root `index.md` and all `wiki/*/_index.md`, then search candidate pages. Return candidate domains and likely actions, but do not create or update anything. If the user wants to write, hand off to `second-brain-ingest`, which must run its own domain-routing preflight before writing.

Domain-placement output should include:

- top 3 candidate domains with reasons,
- any exact or related existing pages,
- whether this looks like update, new page in existing domain, split, ambiguous, or possible new domain,
- what evidence is missing before ingest.

## Result Handling

If found:

- Return matching wiki pages as wikilinks.
- Return daily evidence, when explicitly requested, as plain paths/dates rather than wikilinks.
- Explain why each page is relevant.
- State what is still missing or uncertain.
- Ask whether the user wants to open a page or convert the topic into an ingest task.

If ambiguous:

- Show the top candidates.
- Ask the user to confirm the intended scope or whether candidate pages count as the same topic.

If not found:

- State that the vault has no relevant content.
- Ask whether the user wants to ingest this topic.
- End without writing if the user does not switch to ingest.

## Completion Criteria

Report blockage instead of answering as complete if any applicable item is missing:

- Query remained read-only.
- Basic Memory freshness was considered before trusting Basic Memory results, or Grep fallback was used.
- Results were filtered by `file_path` before use.
- Candidate wiki page bodies were opened before synthesis.
- `_index.md` and root `index.md` were used only as navigation/scope evidence.
- Daily notes were used only when explicitly requested, and cited as plain paths/dates.
- Raw files were not traversed as answer nodes.
- The final answer states matches, uncertainty, gaps, and whether ingest is needed for any write or web expansion.

## Output Shape

Use concise structure:

```markdown
## 结论
...

## 命中页面
- [[page]] — why it matches

## 缺口
...

<If a follow-up decision is needed in Claude Code, ask it with AskUserQuestion instead of plain text.>
```

Skip sections that do not apply.

## Forbidden Upstream Behavior

Never follow these upstream `wiki-query` behaviors in this vault:

- Read `wiki/hot.md`.
- Read `wiki/index.md`; root `index.md` is the index.
- Save answers under `wiki/questions/`.
- Append `wiki/log.md`.
- Automatically WebSearch.
- Turn a query answer into a wiki page without an explicit ingest transition.
