#!/usr/bin/env python3
"""Find the latest heavy-research deployment plan on Linux/Ubuntu hosts."""

from __future__ import annotations

from datetime import datetime
import re
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def parse_session_name(name: str) -> tuple[datetime, int] | None:
    match = SESSION_RE.fullmatch(name)
    if not match:
        return None
    try:
        stamp = datetime.strptime(match.group(1), "%Y-%m-%d-%H%M%S")
    except ValueError:
        return None
    return stamp, int(match.group(2) or 0)


def session_sort_key(path: Path) -> tuple[datetime, int, str]:
    parsed = parse_session_name(path.name)
    return (*parsed, path.name) if parsed else (datetime.min, -1, path.name)


def state_kind(path: Path) -> str | None:
    state_path = path / "research" / "_state.md"
    if not state_path.exists():
        return "legacy"
    if not state_path.is_file() or state_path.is_symlink():
        return None
    try:
        text = state_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    status = re.findall(r"(?m)^-\s+status:\s*(.*?)\s*$", text)
    session_id = re.findall(r"(?m)^-\s+session_id:\s*(.*?)\s*$", text)
    if len(status) != 1 or len(session_id) != 1 or session_id[0].strip() != path.name:
        return None
    return "complete" if status[0].strip() == "complete" else None


def is_reviewable_session(path: Path, workflows_root: Path) -> bool:
    if path.is_symlink():
        return False
    resolved = path.resolve()
    if not resolved.is_dir() or resolved.parent != workflows_root:
        return False
    if parse_session_name(resolved.name) is None:
        return False
    plan_path = resolved / "deployment-plan.md"
    return plan_path.is_file() and not plan_path.is_symlink() and state_kind(resolved) is not None


def main() -> int:
    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink():
        return fail(".workflows/ 不得是 symlink。")
    if not workflows_dir.is_dir():
        return fail("未找到 .workflows/ 目录。请先用 heavy-research 生成 deployment-plan。")

    workflows_root = workflows_dir.resolve()

    candidates = [
        path
        for path in workflows_dir.iterdir()
        if is_reviewable_session(path, workflows_root)
    ]

    if not candidates:
        return fail("未找到包含 deployment-plan.md 的 session 目录。请先用 heavy-research 生成 deployment-plan。")

    latest = max(candidates, key=session_sort_key).resolve()
    plan_path = latest / "deployment-plan.md"
    print(f"SESSION_DIR={latest}")
    print(f"PLAN_PATH={plan_path}")
    print(f"SESSION_STATE={state_kind(latest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
