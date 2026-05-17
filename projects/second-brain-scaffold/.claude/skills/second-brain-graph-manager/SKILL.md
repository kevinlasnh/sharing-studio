---
name: second-brain-graph-manager
description: Manage Obsidian graph colors for <your-username>'s Second Brain vault. Use when the user says "重刷图谱颜色", "graph colors", "图谱色组", when second-brain-ingest creates a new domain, or when .obsidian/graph.json / graph CSS snippets must be verified or repaired. Maintains the vault's 5 colorGroups plus the raw attachment node color, and closes Graph View before writes.
---

# Second Brain Graph Manager

Maintain `.obsidian/graph.json` color groups and the graph attachment-node CSS snippet.

This skill is the renamed version of the old local graph color manager.

## Execution Contract

Run the graph workflow completely before reporting clean or repaired. The user should not need to say "follow the skill carefully"; every graph-manager request already includes that requirement.

Do not stop after reading `.obsidian/graph.json`. Validate the graph color groups, attachment color snippet, and snippet enablement, close Graph View before writing when repair is needed, write only if needed, then re-read and verify. Stop early only when Obsidian CLI or file access blocks a safe repair; report the limitation instead of claiming completion.

## Color Group Contract

Do not enforce a global graph `search` filter. The default Graph View may show all vault nodes. Daily notes remain visually distinct through the daily color group below, but their isolation is enforced by daily no-link rules rather than by hiding them from the graph.

`colorGroups` must contain these 5 entries in this order:

| Order | Query | Hex | Decimal rgb | Meaning |
|---|---|---|---|---|
| 1 | `file:index -file:_index` | `#56B4E9` | `5682409` | root index |
| 2 | `file:CLAUDE OR file:AGENTS OR file:GEMINI` | `#D55E00` | `13983232` | agent config (`CLAUDE.md`, `AGENTS.md`, and `GEMINI.md`) |
| 3 | `file:_index` | `#0072B2` | `29362` | domain indexes |
| 4 | `path:"daily/"` | `#F0E442` | `15787074` | daily journal |
| 5 | `path:"wiki/"` | `#009E73` | `40563` | wiki content pages |

The order is semantic. Obsidian uses first match; `file:_index` must stay before `path:"wiki/"`. `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md` must stay in the same agent config color group. Keep folder path queries slash-terminated so content files with names like `gtd-daily-workflow.md` do not match the daily journal group.

## Raw Attachment Color Contract

Do not add a `path:"raw"` color group. Obsidian Graph treats image/PDF/other raw files as `attachment` nodes; those nodes do not reliably take a path color group. Raw visual color is controlled by the global attachment node CSS variable.

Maintain `.obsidian/snippets/second-brain-graph-colors.css` with:

```css
/* Keep raw attachments visually distinct from daily notes in graph view. */
body {
  --graph-node-attachment: #CC79A7;
}
```

Maintain `.obsidian/appearance.json` so `enabledCssSnippets` includes `second-brain-graph-colors`. This intentionally colors all attachment nodes as raw source or instructional visual nodes; the vault policy keeps user-supplied attachments under `raw/`.

## New Domain Behavior

New domains do not need new color groups. All wiki content remains green and `_index.md` remains blue by the generic rules.

When called after new domain creation, verify the 5 color group entries plus the attachment color snippet and report whether graph config was already valid or repaired.

## Manual Refresh Workflow

1. Read `.obsidian/graph.json`.
2. Read `.obsidian/appearance.json` and `.obsidian/snippets/second-brain-graph-colors.css`.
3. Validate the 5 color group entries, order, alpha, and rgb values. Do not modify `search` unless the user explicitly asks.
4. Validate that the CSS snippet sets `--graph-node-attachment: #CC79A7` and is enabled in `appearance.json`.
5. If no change is needed, report clean.
6. If repair is needed, close Graph View before writing.
7. Write only the needed graph, appearance, or snippet files.
8. Re-read and verify. If Obsidian CLI is available, verify runtime `getComputedStyle(document.body).getPropertyValue('--graph-node-attachment')` is `#CC79A7`.

## Close Graph View Before Write

Use Obsidian CLI when available:

```powershell
obsidian eval code="app.workspace.getLeavesOfType('graph').forEach(l => l.detach())"
```

If Obsidian CLI is unavailable, report the limitation before editing. Prefer not to write graph config while Graph View is open.

## Entry Format

```json
{
  "query": "path:\"wiki/\"",
  "color": {
    "a": 1,
    "rgb": 40563
  }
}
```

## Attachment Snippet Format

```css
body {
  --graph-node-attachment: #CC79A7;
}
```

## Boundaries

Do not edit wiki pages, daily notes, or indexes.

Do not create per-domain graph colors.

Do not reintroduce `path:"raw"` as a graph color group unless the user explicitly asks to abandon attachment-node coloring.

Do not alter unrelated graph display settings unless the user explicitly asks.

When editing `.obsidian/appearance.json`, preserve unrelated enabled CSS snippets such as `second-brain-markdown-images`; this skill owns graph colors, not Markdown image alignment.

## Completion Criteria

Report blockage instead of clean/repaired if any applicable item is missing:

- `.obsidian/graph.json` was read.
- All 5 `colorGroups` were validated for query, order, alpha, and rgb.
- `.obsidian/snippets/second-brain-graph-colors.css` was validated.
- `.obsidian/appearance.json` was validated for snippet enablement.
- No global `search` filter was added unless explicitly requested.
- Graph View was closed before writing, or inability to do so was reported.
- Any write was followed by a re-read verification.
