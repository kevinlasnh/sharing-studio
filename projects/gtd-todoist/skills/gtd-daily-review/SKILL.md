---
name: gtd-daily-review
description: GTD Daily Review for Todoist. Use when the user says "每日总结", "今天回顾", "收工", "Daily Review", or wants to review today's completed, unfinished, overdue, Inbox, and tomorrow tasks. Produces a review and executes changes only after confirmation.
---

# GTD Daily Review

## Ground Rules

- Work in the main conversation session; the 22:00 cron only reminds the user.
- Do not mutate Todoist until the user confirms the handling plan.
- Use `id:<task_id>` or Todoist URLs for all mutating commands.
- Do not process Inbox items here. Report Inbox count and suggest running `gtd-inbox-triage` if needed.
- Preserve existing labels unless the user asks to replace them.

## Workflow

1. Gather the day:

   ```bash
   td completed list --since today --json --full
   td today --json --full
   td inbox --json --full
   td upcoming 1 --json --full
   ```

2. Produce the Daily Review:

   ```text
   Daily Review
   Completed today: <count>
   Key wins: <p1/p2 completed items>
   Unfinished today / overdue: <count>
   Inbox remaining: <count>
   Tomorrow preview: <count>
   ```

3. For each unfinished item, propose one action:

   - keep for today if still relevant
   - reschedule to tomorrow or a concrete date
   - lower priority
   - move to `🗂 Someday / Maybe`
   - delete if obsolete
   - convert into a clearer next action

4. Ask the user to confirm or revise the plan.

5. Execute confirmed actions with safe commands:

   ```bash
   td task reschedule id:<id> tomorrow
   td task update id:<id> --priority p3
   td task move id:<id> --project "🗂 Someday / Maybe"
   td task delete id:<id> --yes
   ```

6. Close with tomorrow's focus suggestions. Do not set MIT priorities unless the user confirms.

## Output Style

- Keep the report compact enough for Telegram.
- Do not use Markdown tables; Telegram displays table source literally.
- Use numbered lists and short sections.
