#!/usr/bin/env python3
"""Find the latest heavy-research deployment plan on Linux/Ubuntu hosts."""

from __future__ import annotations

import re
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{4}(\d{2})?)(?:-(\d+))?$")


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def session_sort_key(path: Path) -> tuple[str, int]:
    match = SESSION_RE.match(path.name)
    if not match:
        return ("", -1)
    suffix = int(match.group(3)) if match.group(3) else 0
    return (match.group(1), suffix)


def main() -> int:
    workflows_dir = Path(".workflows")
    if not workflows_dir.is_dir():
        return fail("未找到 .workflows/ 目录。请先用 heavy-research 生成 deployment-plan。")

    candidates = [
        path
        for path in workflows_dir.iterdir()
        if path.is_dir() and SESSION_RE.match(path.name) and (path / "deployment-plan.md").is_file()
    ]

    if not candidates:
        return fail("未找到包含 deployment-plan.md 的 session 目录。请先用 heavy-research 生成 deployment-plan。")

    latest = max(candidates, key=session_sort_key).resolve()
    plan_path = latest / "deployment-plan.md"
    print(f"SESSION_DIR={latest}")
    print(f"PLAN_PATH={plan_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
