# Deployment Plan

> Deploy a GTD-based Todoist management system for an AI agent runtime with a `td` CLI and a cron/reminder layer.
>
> The user interacts in the main chat session; cron only sends reminders. The agent never auto-mutates Todoist.

---

## 1. Architecture

### Core Principles

- `cron = reminder system`, only pings the user at fixed times to start a GTD flow.
- `main session = execution system`, all Inbox triage / Daily Review / Weekly Review discussions, confirmations, and mutations happen in the main chat.
- Do not let isolated cron sessions own approval state machines. The user may ask follow-ups, revise proposals, and negotiate placement — that context must live in the main session.
- The Todoist GUI is the user's read-only view; all Todoist changes go through the agent via the `td` CLI.
- Any destructive or batch operation must propose first, wait for confirmation, then execute.
- Mutating Todoist commands must use `id:<task_id>` or Todoist URL. Never mutate by title alone.

### Deployment Items

| # | Item | Type | Target path |
|---|---|---|---|
| 1 | Todoist GTD scaffold | Todoist projects / labels / filters | Todoist cloud |
| 2 | GTD section in `AGENTS.md` | appended to existing file | `<agent-workspace>/AGENTS.md` |
| 3 | `gtd-inbox-triage` skill | new workspace skill | `<agent-workspace>/skills/gtd-inbox-triage/SKILL.md` |
| 4 | `gtd-daily-review` skill | new workspace skill | `<agent-workspace>/skills/gtd-daily-review/SKILL.md` |
| 5 | `gtd-weekly-review` skill | new workspace skill | `<agent-workspace>/skills/gtd-weekly-review/SKILL.md` |
| 6 | 4 daily reminder crons | reminder-only | `<cron-config>` |
| 7 | 1 weekly reminder cron | reminder-only | `<cron-config>` |

Not modified: your agent's main config, model settings, proxy policy, chat delivery webhook, or other integrations.

---

## 2. Todoist GTD Scaffold

Back up your Todoist state before creating / verifying the structure below.

### Projects

- `🗂 Someday / Maybe` — items to keep but not act on now.
- `🌅 Horizons` — 1-2 year goals, directions, long-term focus.
- Keep all existing real projects — do not delete the user's prior projects to enforce GTD aesthetics.

### Labels

- `next` — next physical action.
- `waiting` — waiting on someone else.
- `电脑` — can be done at a computer.
- `家` — can be done at home.
- `外出` — can be done while out / running errands.
- `电话` — phone / message communication.
- `深度工作` — needs long focused blocks.
- `2min` — doable in under two minutes.

### Filters

- `GTD - Next Actions`: `@next & !@waiting`
- `GTD - Waiting For`: `@waiting`
- `GTD - Today Focus`: `today | overdue | p1`
- `GTD - Quick Wins`: `@2min | (p1 & today)`
- `GTD - Deep Work`: `@深度工作 & @next`
- `GTD - Context Computer`: `@电脑 & @next`
- `GTD - Context Home`: `@家 & @next`
- `GTD - Context Outside`: `@外出 & @next`
- `GTD - Context Phone`: `@电话 & @next`

---

## 3. `AGENTS.md` GTD Section

Drop `agents-section.md` into your agent workspace `AGENTS.md` (or `CLAUDE.md`). It covers:

- agent role and the cron-is-reminder-only contract
- daily / weekly rhythm
- trigger phrases
- Todoist scaffold reference
- permission tiers (direct / confirm / destructive)
- GTD principles

---

## 4. Workspace Skills

Three skills, each under `skills/<skill-name>/SKILL.md`:

| Skill | When it triggers | What it does |
|---|---|---|
| `gtd-inbox-triage` | user says "开始整理 Inbox" / "clean my inbox" | scans Inbox, proposes classification, waits for confirmation, executes with `id:<task_id>` |
| `gtd-daily-review` | user says "每日总结" / "收工" / "Daily Review" | reviews completed / unfinished / overdue / Inbox / tomorrow, proposes handling, waits for confirmation |
| `gtd-weekly-review` | user says "开始 Weekly Review" / "做周回顾" | guides Get Clear / Get Current / Get Creative step by step |

Full skill sources live in `skills/`. Each skill:

- waits for user confirmation before mutating
- uses `id:<task_id>` or Todoist URL
- preserves existing labels (read + merge before `td task update --labels`)
- closes with a status report

---

## 5. Reminder-only Cron Jobs

All cron commands only send a reminder message; they do not auto-triage Inbox, do not auto-run Daily Review, and do not auto-advance Weekly Review.

Each cron must be invoked with the following delivery contract (substitute `<TELEGRAM_USER_ID>` and `<BOT_ACCOUNT>` for your own values):

- `--agent main`
- `--announce`
- `--channel telegram`
- `--account <BOT_ACCOUNT>`
- `--to <TELEGRAM_USER_ID>`
- `--best-effort-deliver`
- `--timeout-seconds 120`

### Daily Reminders

```bash
openclaw cron add --name "gtd-inbox-reminder-0900" --cron "0 9 * * *" --tz "Asia/Shanghai" \
  --session isolated --agent main \
  --message "GTD Inbox reminder: it is 09:00. Reply '开始整理 Inbox' in the main session to clarify together and pick up to 3 MITs." \
  --announce --channel telegram --account <BOT_ACCOUNT> --to <TELEGRAM_USER_ID> \
  --best-effort-deliver --timeout-seconds 120

openclaw cron add --name "gtd-inbox-reminder-1300" --cron "0 13 * * *" --tz "Asia/Shanghai" \
  --session isolated --agent main \
  --message "GTD Inbox reminder: it is 13:00. Reply '开始整理 Inbox' to clarify morning captures." \
  --announce --channel telegram --account <BOT_ACCOUNT> --to <TELEGRAM_USER_ID> \
  --best-effort-deliver --timeout-seconds 120

openclaw cron add --name "gtd-inbox-reminder-1900" --cron "0 19 * * *" --tz "Asia/Shanghai" \
  --session isolated --agent main \
  --message "GTD Inbox reminder: it is 19:00. Reply '开始整理 Inbox' to clarify afternoon captures." \
  --announce --channel telegram --account <BOT_ACCOUNT> --to <TELEGRAM_USER_ID> \
  --best-effort-deliver --timeout-seconds 120

openclaw cron add --name "gtd-daily-review-reminder-2200" --cron "0 22 * * *" --tz "Asia/Shanghai" \
  --session isolated --agent main \
  --message "GTD Daily Review reminder: it is 22:00. Reply '每日总结' or '收工' to finish today's review." \
  --announce --channel telegram --account <BOT_ACCOUNT> --to <TELEGRAM_USER_ID> \
  --best-effort-deliver --timeout-seconds 120
```

### Weekly Reminder

```bash
openclaw cron add --name "gtd-weekly-review-reminder-sun-1315" --cron "15 13 * * 0" --tz "Asia/Shanghai" \
  --session isolated --agent main \
  --message "GTD Weekly Review reminder: today is Sunday. Reply '开始 Weekly Review' for the weekly system check. If Inbox is not empty, run '开始整理 Inbox' first." \
  --announce --channel telegram --account <BOT_ACCOUNT> --to <TELEGRAM_USER_ID> \
  --best-effort-deliver --timeout-seconds 120
```

> Using another runtime? Port the reminder-only contract to your cron of choice (systemd timer, GitHub Actions, n8n, etc). The **content** matters: cron pings, agent in main session acts.

---

## 6. Deployment Order

1. Back up current Todoist state to `<backup-path>/todoist-gtd-before-<timestamp>/`.
2. Create / verify the Todoist GTD scaffold.
3. Initialize the 3 workspace skills under `skills/`.
4. Update `<agent-workspace>/AGENTS.md` with the GTD section (see `agents-section.md`).
5. Add 5 reminder-only cron jobs.
6. List skills to confirm the 3 new skills are `ready`.
7. List cron jobs to confirm the 5 GTD reminders exist and target the right Telegram user.
8. Run the read-only smoke test:
   - `td label list --json`
   - `td filter list --json`
   - `td project list --json`
   - agent runtime skills list
   - agent cron list

If the skills do not hot-reload, restart your agent runtime and re-verify.

Optionally run the health check in `health-check/` to verify the contract end-to-end (read-only).

---

## 7. Rollback

Prefer recoverable steps. Do not hard-delete user data.

```bash
# Remove GTD workspace skills
rm -rf <agent-workspace>/skills/gtd-inbox-triage
rm -rf <agent-workspace>/skills/gtd-daily-review
rm -rf <agent-workspace>/skills/gtd-weekly-review

# Remove GTD reminder cron
openclaw cron rm <job-id>

# AGENTS.md rollback
# Remove the "## GTD Todoist Management" section.
```

Todoist rollback: using your backup JSON, manually remove newly added labels / filters / empty projects. Never auto-delete projects that contain user tasks.
