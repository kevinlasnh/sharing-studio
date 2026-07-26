#!/usr/bin/env python3
"""Find the latest reusable heavy-research session on Linux/Ubuntu hosts."""

from __future__ import annotations

import argparse
from datetime import datetime
import re
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def field(text: str, name: str) -> str | None:
    matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
    return matches[0].strip() if len(matches) == 1 else None


def parse_session_name(name: str) -> tuple[datetime, int] | None:
    match = SESSION_RE.fullmatch(name)
    if not match:
        return None
    try:
        stamp = datetime.strptime(match.group(1), "%Y-%m-%d-%H%M%S")
    except ValueError:
        return None
    return stamp, int(match.group(2) or 0)


def session_state(path: Path, topic_hash: str) -> dict[str, str] | None:
    state_path = path / "research" / "_state.md"
    if not state_path.is_file() or state_path.is_symlink():
        return None
    try:
        text = state_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    values = {name: field(text, name) for name in ("session_id", "topic_sha256", "status", "phase")}
    if any(value is None for value in values.values()):
        return None
    if values["session_id"] != path.name or values["topic_sha256"] != topic_hash:
        return None
    if values["status"] != "in_progress" or values["phase"] == "complete":
        return None
    return {name: value for name, value in values.items() if value is not None}


def is_session_dir(path: Path, workflows_root: Path, topic_hash: str) -> bool:
    if path.is_symlink():
        return False
    try:
        resolved = path.resolve()
        resolved.relative_to(workflows_root)
    except (FileNotFoundError, ValueError):
        return False

    if not resolved.is_dir():
        return False
    if resolved.parent != workflows_root:
        return False
    if parse_session_name(resolved.name) is None:
        return False
    return session_state(resolved, topic_hash) is not None


def session_sort_key(path: Path) -> tuple[datetime, int, str]:
    parsed = parse_session_name(path.name)
    return (*parsed, path.name) if parsed else (datetime.min, -1, path.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic-hash", required=True)
    args = parser.parse_args()
    if not SHA256_RE.fullmatch(args.topic_hash):
        return fail("--topic-hash 必须是 64 位小写十六进制 SHA-256。")

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink():
        return fail(".workflows/ 不得是 symlink。")
    if not workflows_dir.is_dir():
        return fail("未找到 .workflows/ 目录。")

    workflows_root = workflows_dir.resolve()
    active_session_file = workflows_dir / ".active-session"

    if active_session_file.is_file():
        active = active_session_file.read_text(encoding="utf-8").splitlines()
        active_path = Path(active[0].strip()) if active and active[0].strip() else None
        if active_path and active_path.exists():
            if is_session_dir(active_path, workflows_root, args.topic_hash):
                print(f"SESSION_DIR={active_path.resolve()}")
                print(f"SESSION_ID={active_path.resolve().name}")
                print(f"TOPIC_SHA256={args.topic_hash}")
                return 0
            warn(".active-session 不是当前主题的未完成 session，已忽略。")

    candidates = [
        path
        for path in workflows_dir.iterdir()
        if is_session_dir(path, workflows_root, args.topic_hash)
    ]

    if not candidates:
        return fail("未找到可复用的 session 目录。")

    latest = max(candidates, key=session_sort_key)
    print(f"SESSION_DIR={latest.resolve()}")
    print(f"SESSION_ID={latest.resolve().name}")
    print(f"TOPIC_SHA256={args.topic_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
