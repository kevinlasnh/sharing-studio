#!/usr/bin/env bash
#
# GTD Todoist Health — read-only audit for a GTD-over-Todoist agent harness.
#
# Environment variables (all optional except as noted):
#
#   OPENCLAW_STATE_DIR          default: $HOME/.openclaw
#   OPENCLAW_CONFIG_PATH        default: $OPENCLAW_STATE_DIR/openclaw.json
#   OPENCLAW_WORKSPACE_DIR      default: $OPENCLAW_STATE_DIR/workspace
#   OPENCLAW_AGENT_ID           default: main
#   INCLUDE_TODOIST_SCAFFOLD    default: 0 (set to 1 to check project/label/filter names only)
#   GTD_EXPECTED_CRON_DELIVERY  optional JSON match for delivery.to/accountId when running cron checks
#
# The script does not read user task content. It inspects file presence, file
# contract text (grep), runtime skill / cron listings (JSON), and optional
# Todoist scaffold names — never task bodies.

set -uo pipefail

HOST_STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
HOST_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$HOST_STATE_DIR/openclaw.json}"
WORKSPACE_DIR="${OPENCLAW_WORKSPACE_DIR:-$HOST_STATE_DIR/workspace}"
AGENT_ID="${OPENCLAW_AGENT_ID:-main}"
INCLUDE_TODOIST_SCAFFOLD="${INCLUDE_TODOIST_SCAFFOLD:-0}"

ISSUES=()
INFO=()

section() {
  printf '\n===== %s =====\n' "$1"
}

issue() {
  ISSUES+=("$1")
  printf 'ISSUE: %s\n' "$1"
}

info() {
  INFO+=("$1")
  printf 'INFO: %s\n' "$1"
}

ok() {
  printf 'OK: %s\n' "$1"
}

require_file() {
  local path="$1"
  local label="$2"
  if [ -f "$path" ]; then
    ok "$label exists: $path"
  else
    issue "$label missing: $path"
  fi
}

require_contains() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  if [ ! -f "$file" ]; then
    issue "$label cannot be checked because file is missing: $file"
    return
  fi
  if grep -Eiq -- "$pattern" "$file"; then
    ok "$label"
  else
    issue "$label not found in $file"
  fi
}

require_not_found() {
  local pattern="$1"
  local label="$2"
  shift 2
  local files=("$@")
  local matches
  matches="$(grep -RInE -- "$pattern" "${files[@]}" 2>/dev/null || true)"
  if [ -n "$matches" ]; then
    issue "$label"
    printf '%s\n' "$matches" | sed -n '1,40p'
  else
    ok "$label"
  fi
}

section "summary"
printf 'generated_at=%s\n' "$(date -Is 2>/dev/null || date)"
printf 'host=%s\n' "$(hostname 2>/dev/null || true)"
printf 'user=%s\n' "$(id -un 2>/dev/null || true)"
printf 'state_dir=%s\n' "$HOST_STATE_DIR"
printf 'config_path=%s\n' "$HOST_CONFIG_PATH"
printf 'workspace_dir=%s\n' "$WORKSPACE_DIR"
printf 'agent_id=%s\n' "$AGENT_ID"
printf 'include_todoist_scaffold=%s\n' "$INCLUDE_TODOIST_SCAFFOLD"

section "p0_workspace_files"
AGENTS_FILE="$WORKSPACE_DIR/AGENTS.md"
INBOX_SKILL="$WORKSPACE_DIR/skills/gtd-inbox-triage/SKILL.md"
DAILY_SKILL="$WORKSPACE_DIR/skills/gtd-daily-review/SKILL.md"
WEEKLY_SKILL="$WORKSPACE_DIR/skills/gtd-weekly-review/SKILL.md"
GTD_FILES=("$AGENTS_FILE" "$INBOX_SKILL" "$DAILY_SKILL" "$WEEKLY_SKILL")

require_file "$HOST_CONFIG_PATH" "agent runtime config"
require_file "$AGENTS_FILE" "workspace AGENTS.md"
require_file "$INBOX_SKILL" "gtd-inbox-triage skill"
require_file "$DAILY_SKILL" "gtd-daily-review skill"
require_file "$WEEKLY_SKILL" "gtd-weekly-review skill"

printf '\n-- file sizes and hashes --\n'
for file in "${GTD_FILES[@]}"; do
  if [ -f "$file" ]; then
    wc -c "$file" 2>/dev/null || true
    sha256sum "$file" 2>/dev/null || true
  fi
done

section "p0_agent_runtime_config"
if command -v openclaw >/dev/null 2>&1; then
  if OPENCLAW_STATE_DIR="$HOST_STATE_DIR" OPENCLAW_CONFIG_PATH="$HOST_CONFIG_PATH" timeout 30s openclaw config validate; then
    ok "openclaw config validate passed"
  else
    issue "openclaw config validate failed"
  fi
else
  info "openclaw command not found; skipping runtime config validation (port this check to your runtime's equivalent)"
fi

section "p1_agents_gtd_contract"
require_contains "$AGENTS_FILE" 'Capture|收集|捕获' "AGENTS.md covers Capture"
require_contains "$AGENTS_FILE" 'Clarify|澄清' "AGENTS.md covers Clarify"
require_contains "$AGENTS_FILE" 'Organize|组织|归位' "AGENTS.md covers Organize"
require_contains "$AGENTS_FILE" 'Reflect|回顾' "AGENTS.md covers Reflect"
require_contains "$AGENTS_FILE" 'Engage|执行选择|今天做什么' "AGENTS.md covers Engage"
require_contains "$AGENTS_FILE" 'id:<task_id>|Todoist URL' "AGENTS.md requires id:<task_id> or Todoist URL for mutation"
require_contains "$AGENTS_FILE" 'td task update --labels.*replace|--labels.*替换' "AGENTS.md warns that label updates replace labels"

section "p1_skill_content_contract"
require_contains "$INBOX_SKILL" 'confirm|确认|explicitly confirms' "Inbox triage waits for confirmation"
require_contains "$INBOX_SKILL" 'id:<task_id>|Todoist URL' "Inbox triage requires id or URL for mutation"
require_contains "$INBOX_SKILL" 'title alone' "Inbox triage forbids title-only mutation"
require_contains "$INBOX_SKILL" 'Waiting For|waiting for|waiting' "Inbox triage handles Waiting For"
require_contains "$INBOX_SKILL" 'merge current labels|Preserve existing labels|read.*labels' "Inbox triage preserves labels"
require_contains "$INBOX_SKILL" 'MIT|p1' "Inbox triage requires MIT priority care"

require_contains "$DAILY_SKILL" 'confirm|确认' "Daily review waits for confirmation"
require_contains "$DAILY_SKILL" 'id:<task_id>|Todoist URL' "Daily review requires id or URL for mutation"
require_contains "$DAILY_SKILL" 'Preserve existing labels|read.*labels' "Daily review preserves labels"

require_contains "$WEEKLY_SKILL" 'Get Clear' "Weekly review includes Get Clear"
require_contains "$WEEKLY_SKILL" 'Get Current' "Weekly review includes Get Current"
require_contains "$WEEKLY_SKILL" 'Get Creative' "Weekly review includes Get Creative"
require_contains "$WEEKLY_SKILL" 'Next Action' "Weekly review checks Next Actions"
require_contains "$WEEKLY_SKILL" 'Waiting For' "Weekly review checks Waiting For"
require_contains "$WEEKLY_SKILL" 'Someday' "Weekly review checks Someday/Maybe"
require_contains "$WEEKLY_SKILL" 'Horizons' "Weekly review checks Horizons"

section "p1_runtime_skill_visibility"
if command -v openclaw >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  skills_json="/tmp/gtd-skills-$$.json"
  if OPENCLAW_STATE_DIR="$HOST_STATE_DIR" OPENCLAW_CONFIG_PATH="$HOST_CONFIG_PATH" timeout 30s openclaw skills list --agent "$AGENT_ID" --json >"$skills_json" 2>/tmp/gtd-skills.err &&
    python3 - "$AGENT_ID" "$skills_json" <<'PY'
import json
import sys

agent = sys.argv[1]
json_path = sys.argv[2]
expected = {
    "gtd-inbox-triage",
    "gtd-daily-review",
    "gtd-weekly-review",
}

with open(json_path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
if isinstance(data, dict):
    for key in ("skills", "items", "entries"):
        if isinstance(data.get(key), list):
            rows = data[key]
            break
    else:
        rows = []
elif isinstance(data, list):
    rows = data
else:
    rows = []

by_name = {row.get("name"): row for row in rows if isinstance(row, dict)}
failed = False
for name in sorted(expected):
    row = by_name.get(name)
    if not row:
        print(f"ISSUE runtime skill missing: {name}")
        failed = True
        continue
    checks = {
        "eligible": row.get("eligible") is True,
        "modelVisible": row.get("modelVisible") is True,
        "commandVisible": row.get("commandVisible") is True,
    }
    if all(checks.values()):
        print(f"OK runtime skill ready: {name}")
    else:
        print(f"ISSUE runtime skill not ready: {name} checks={checks} row={row}")
        failed = True

sys.exit(1 if failed else 0)
PY
  then
    ok "all GTD runtime skills are ready for agent $AGENT_ID"
  else
    issue "GTD runtime skill visibility check failed"
    if [ -s /tmp/gtd-skills.err ]; then
      sed -n '1,80p' /tmp/gtd-skills.err
    fi
  fi
else
  info "cannot check runtime skills because openclaw or python3 is missing"
fi

section "p1_gtd_cron_reminders"
if command -v openclaw >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  cron_json="/tmp/gtd-cron-$$.json"
  if OPENCLAW_STATE_DIR="$HOST_STATE_DIR" OPENCLAW_CONFIG_PATH="$HOST_CONFIG_PATH" timeout 30s openclaw cron list --json >"$cron_json" 2>/tmp/gtd-cron.err &&
    python3 - "$cron_json" <<'PY'
import json
import sys

json_path = sys.argv[1]
expected = {
    "gtd-inbox-reminder-0900",
    "gtd-inbox-reminder-1300",
    "gtd-inbox-reminder-1900",
    "gtd-daily-review-reminder-2200",
    "gtd-weekly-review-reminder-sun-1315",
}

with open(json_path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
jobs = data.get("jobs", []) if isinstance(data, dict) else data if isinstance(data, list) else []
by_name = {job.get("name"): job for job in jobs if isinstance(job, dict)}
failed = False
for name in sorted(expected):
    job = by_name.get(name)
    if not job:
        print(f"ISSUE cron missing: {name}")
        failed = True
        continue
    payload = job.get("payload") or {}
    delivery = job.get("delivery") or {}
    checks = {
        "enabled": job.get("enabled") is True,
        "sessionTarget": job.get("sessionTarget") == "isolated",
        "thinking": payload.get("thinking") == "off",
        "lightContext": payload.get("lightContext") is True,
        "toolsAllow": payload.get("toolsAllow") == ["read"],
        "timeoutSeconds": isinstance(payload.get("timeoutSeconds"), int) and payload["timeoutSeconds"] > 0,
        "delivery.mode": delivery.get("mode") == "announce",
        "delivery.bestEffort": delivery.get("bestEffort") is True,
    }
    if all(checks.values()):
        print(f"OK cron reminder-only: {name}")
    else:
        print(f"ISSUE cron drift: {name} checks={checks}")
        failed = True

sys.exit(1 if failed else 0)
PY
  then
    ok "all GTD cron jobs match reminder-only contract"
  else
    issue "GTD cron reminder-only check failed"
    if [ -s /tmp/gtd-cron.err ]; then
      sed -n '1,80p' /tmp/gtd-cron.err
    fi
  fi
else
  info "cannot check GTD cron because openclaw or python3 is missing"
fi

section "p2_stale_scaffold_scan"
require_not_found 'reschedule tomorrow|tomorrow.*soft|soft date' "soft-date examples must not appear" "${GTD_FILES[@]}"
require_not_found 'td task quickadd .*--project|td task move .*--label' "invalid td mutation examples must not appear" "${GTD_FILES[@]}"

section "p2_optional_todoist_scaffold"
if [ "$INCLUDE_TODOIST_SCAFFOLD" = "1" ]; then
  if ! command -v td >/dev/null 2>&1; then
    issue "td command not found for optional Todoist scaffold check"
  else
    printf '%s\n' "This optional check reads only Todoist project, label, and filter scaffolding. It does not list tasks."
    if command -v python3 >/dev/null 2>&1; then
      projects_json="/tmp/gtd-projects-$$.json"
      if td project list --json >"$projects_json" 2>/tmp/gtd-projects.err && python3 - "$projects_json" <<'PY'
import json, sys
json_path = sys.argv[1]
expected = {"🗂 Someday / Maybe", "🌅 Horizons"}
with open(json_path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
rows = data if isinstance(data, list) else data.get("results", data.get("projects", [])) if isinstance(data, dict) else []
names = {str(r.get("name", "")) for r in rows if isinstance(r, dict)}
missing = sorted(expected - names)
for name in sorted(expected & names):
    print(f"OK Todoist project exists: {name}")
for name in missing:
    print(f"ISSUE Todoist project missing: {name}")
sys.exit(1 if missing else 0)
PY
      then ok "Todoist project scaffold matches"; else issue "Todoist project scaffold drift"; fi

      labels_json="/tmp/gtd-labels-$$.json"
      if td label list --json >"$labels_json" 2>/tmp/gtd-labels.err && python3 - "$labels_json" <<'PY'
import json, sys
json_path = sys.argv[1]
expected = {"next","waiting","电脑","家","外出","电话","深度工作","2min"}
with open(json_path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
rows = data if isinstance(data, list) else data.get("results", data.get("labels", [])) if isinstance(data, dict) else []
names = {str(r.get("name", "")) for r in rows if isinstance(r, dict)}
missing = sorted(expected - names)
for name in sorted(expected & names):
    print(f"OK Todoist label exists: {name}")
for name in missing:
    print(f"ISSUE Todoist label missing: {name}")
sys.exit(1 if missing else 0)
PY
      then ok "Todoist label scaffold matches"; else issue "Todoist label scaffold drift"; fi

      filters_json="/tmp/gtd-filters-$$.json"
      if td filter list --json >"$filters_json" 2>/tmp/gtd-filters.err && python3 - "$filters_json" <<'PY'
import json, sys
json_path = sys.argv[1]
expected = {
    "GTD - Next Actions",
    "GTD - Waiting For",
    "GTD - Today Focus",
    "GTD - Quick Wins",
    "GTD - Deep Work",
    "GTD - Context Computer",
    "GTD - Context Home",
    "GTD - Context Outside",
    "GTD - Context Phone",
}
with open(json_path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
rows = data if isinstance(data, list) else data.get("results", data.get("filters", [])) if isinstance(data, dict) else []
names = {str(r.get("name", "")) for r in rows if isinstance(r, dict)}
missing = sorted(expected - names)
for name in sorted(expected & names):
    print(f"OK Todoist filter exists: {name}")
for name in missing:
    print(f"ISSUE Todoist filter missing: {name}")
sys.exit(1 if missing else 0)
PY
      then ok "Todoist filter scaffold matches"; else issue "Todoist filter scaffold drift"; fi
    else
      issue "python3 missing for optional Todoist scaffold check"
    fi
  fi
else
  info "Todoist scaffold check skipped by default; set INCLUDE_TODOIST_SCAFFOLD=1 to inspect projects/labels/filters only"
fi

section "manual_semantic_review_required"
printf '%s\n' "Review these manually before declaring clean:"
printf '%s\n' "- Clarify decisions happen before Organize actions."
printf '%s\n' "- Calendar dates are only hard landscape."
printf '%s\n' "- Waiting For includes who, what, and follow-up context."
printf '%s\n' "- Projects are multi-step outcomes with at least one Next Action."
printf '%s\n' "- Weekly Review reviews the whole action system, not only projects."
printf '%s\n' "- Cron jobs remind only; GTD decisions remain in the main chat session."

section "result"
printf 'issue_count=%s\n' "${#ISSUES[@]}"
printf 'info_count=%s\n' "${#INFO[@]}"
if [ "${#ISSUES[@]}" -eq 0 ]; then
  printf 'STATUS=clean\n'
  exit 0
fi

printf 'STATUS=issues\n'
printf '\n-- issues --\n'
for item in "${ISSUES[@]}"; do
  printf -- '- %s\n' "$item"
done
exit 2
