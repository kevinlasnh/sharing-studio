#!/usr/bin/env python3
"""Find the latest reusable heavy-research session on Linux/Ubuntu hosts."""

from __future__ import annotations

import re
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{4}(\d{2})?)(?:-(\d+))?$")


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def is_session_dir(path: Path, workflows_root: Path) -> bool:
    try:
        resolved = path.resolve()
        resolved.relative_to(workflows_root)
    except (FileNotFoundError, ValueError):
        return False

    if not resolved.is_dir():
        return False
    if not SESSION_RE.match(resolved.name):
        return False
    return (resolved / "deployment-plan.md").exists() or (resolved / "research").exists()


def session_sort_key(path: Path) -> tuple[str, int]:
    match = SESSION_RE.match(path.name)
    if not match:
        return ("", -1)
    suffix = int(match.group(3)) if match.group(3) else 0
    return (match.group(1), suffix)


def main() -> int:
    workflows_dir = Path(".workflows")
    if not workflows_dir.is_dir():
        return fail("未找到 .workflows/ 目录。")

    workflows_root = workflows_dir.resolve()
    active_session_file = workflows_dir / ".active-session"

    if active_session_file.is_file():
        active = active_session_file.read_text(encoding="utf-8").splitlines()
        active_path = Path(active[0].strip()) if active and active[0].strip() else None
        if active_path and active_path.exists():
            if is_session_dir(active_path, workflows_root):
                print(f"SESSION_DIR={active_path.resolve()}")
                return 0
            warn(".active-session 指向的路径不是当前仓库 .workflows/ 下的 session 目录，已忽略。")

    candidates = [
        path
        for path in workflows_dir.iterdir()
        if path.is_dir()
        and SESSION_RE.match(path.name)
        and ((path / "deployment-plan.md").exists() or (path / "research").exists())
    ]

    if not candidates:
        return fail("未找到可复用的 session 目录。")

    latest = max(candidates, key=session_sort_key)
    print(f"SESSION_DIR={latest.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
