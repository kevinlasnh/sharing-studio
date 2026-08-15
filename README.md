<h1 align="center">kevin-AI-studio</h1>

<p align="center">
  <strong>Personal AI usage ecosystem: desensitized mirrors of my global agent markdown and authoritative copies of my global agent skills.</strong>
</p>

<p align="center">
  <img alt="Personal AI ecosystem" src="https://img.shields.io/badge/personal-ai--ecosystem-0f766e?style=for-the-badge">
  <img alt="Agent skills" src="https://img.shields.io/badge/agent-skills-2563eb?style=for-the-badge">
  <img alt="Privacy first" src="https://img.shields.io/badge/privacy-first-7c3aed?style=for-the-badge">
</p>

<!-- README-I18N:START -->
<p align="center">
  <strong>English</strong> | <a href="./README.zh-CN.md">简体中文</a>
</p>
<!-- README-I18N:END -->

> [!NOTE]
> This repository publishes reusable rules and skills only. Machine usernames, local paths, credentials, and private content never enter tracked files. Global rule mirrors keep `<second-brain-path>` / `<your-username>` placeholders.

## What's Inside

| Directory | Contents |
| :--- | :--- |
| [`global/`](./global/) | Desensitized mirrors of my global agent rule files `CLAUDE.md` (Claude Code), `AGENTS.md` (Codex), and `AGENTS.dsh.md` (DeepSeek Harness). The three files are byte-identical and share the H1 `# Global Agent Markdown`. |
| [`skills/`](./skills/) | Authoritative copies of all my global agent skills. Each local change to a global skill must be reflected here. |

## Skills

| Skill | Purpose |
| :--- | :--- |
| [`baoyu-format-markdown`](./skills/baoyu-format-markdown/) | Formats plain text or Markdown into structured articles with frontmatter, headings, lists, and code blocks. |
| [`brv-curate`](./skills/brv-curate/) | Curates PWF task knowledge into ByteRover long-term repository memory (L2 → L3 sedimentation). |
| [`brv-query`](./skills/brv-query/) | Queries ByteRover long-term repository memory through the read-only `brv query` interface. |
| [`find-skills`](./skills/find-skills/) | Discovers and installs agent skills from the community. |
| [`heavy-research`](./skills/heavy-research/) | Trigger-phrase-gated heavy research that produces file-backed, evidence-bound deployment plans. |
| [`heavy-review`](./skills/heavy-review/) | Trigger-phrase-gated heavy review that validates deployment plans with provenance-bound snapshots. |
| [`obsidian-markdown`](./skills/obsidian-markdown/) | Creates and edits Obsidian Flavored Markdown with wikilinks, embeds, callouts, and properties. |
| [`planning-with-files-zh`](./skills/planning-with-files-zh/) | Manus-style planning with persistent `task_plan.md` / `findings.md` / `progress.md` files. |
| [`skill-creator`](./skills/skill-creator/) | Creates, edits, and evaluates agent skills (Apache-2.0, based on the upstream skill-creator). |
| [`tavily-search`](./skills/tavily-search/) | LLM-optimized web search via the Tavily CLI; used only as an approved fallback to the host's built-in web search. |
| [`eco-sync`](./skills/eco-sync/) | **Repo-level skill.** Bidirectionally syncs the AI ecosystem (global rules + global skills) with this repository's desensitized copies. Only runs inside this repo. |

## Repository Layout

```text
kevin-AI-studio/
├── global/
│   ├── AGENTS.md          # desensitized mirror of the global Codex rules
│   ├── AGENTS.dsh.md      # desensitized mirror of the global DSH rules
│   └── CLAUDE.md          # desensitized mirror of the global Claude Code rules
├── skills/                # authoritative copies of all global skills
│   ├── baoyu-format-markdown/
│   ├── brv-curate/
│   ├── brv-query/
│   ├── find-skills/
│   ├── heavy-research/
│   ├── heavy-review/
│   ├── obsidian-markdown/
│   ├── planning-with-files-zh/
│   ├── skill-creator/
│   ├── tavily-search/
│   └── eco-sync/           # repo-level sync skill (authoritative source)
├── AGENTS.md              # repository rules (tracked, public-safe)
├── CLAUDE.md              # repository rules (identical to AGENTS.md)
├── task_plan.md           # PWF task memory (tracked)
├── progress.md            # PWF session log (tracked)
├── findings.md            # PWF findings store (tracked)
├── README.md
├── README.zh-CN.md
└── LICENSE
```

## Sync Model

Local truth → desensitized mirror:

1. A global skill changes locally → update the matching copy under `skills/` → commit.
2. Global rule files change locally → apply the same change to the three mirrors in `global/` (keep them byte-identical) → commit.
3. Deployment back to a machine is manual: copy `skills/` entities into the local global skills directory and let Claude Code reuse them via symlinks; render the `global/` mirrors into the local `CLAUDE.md` / `AGENTS.md` by substituting the two placeholders.

### eco-sync (repo-level skill)

`skills/eco-sync/` automates the sync flows above, but intentionally runs only inside this repository. Runtime entities live at `.agents/skills/eco-sync/` and `.claude/skills/eco-sync/` (untracked, identical copies). On a fresh clone, deploy once:

```bash
cp -a skills/eco-sync .agents/skills/
cp -a skills/eco-sync .claude/skills/
```

## Publishing Boundary

Tracked files must stay free of:

```text
secrets / API keys          (.env, .env.*, *.key, *.pem)
machine usernames           (kept as <your-username>)
machine-specific paths      (kept as <second-brain-path>)
account IDs / private IPs / personal content
```

Before publishing changes, scan for secrets, real local paths, account IDs, and private IPs.
