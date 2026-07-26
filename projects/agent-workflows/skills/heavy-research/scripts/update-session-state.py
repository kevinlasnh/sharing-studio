#!/usr/bin/env python3
"""Atomically update a heavy-research session phase and close active state."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
import re
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
PHASES = {"B0", "B1", "B2", "B3", "B4", "C", "D", "complete"}


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def field(text: str, name: str) -> str | None:
    matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
    return matches[0].strip() if len(matches) == 1 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    parser.add_argument("--phase", required=True, choices=sorted(PHASES))
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        return fail("当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。")
    workflows_root = workflows_dir.resolve()
    requested = Path(args.session_dir).expanduser()
    if requested.is_symlink():
        return fail("SESSION_DIR 不得是 symlink。")
    session_dir = requested.resolve()
    if session_dir.parent != workflows_root or not SESSION_RE.fullmatch(session_dir.name):
        return fail("SESSION_DIR 必须是当前仓库 .workflows/ 下的合法时间戳目录。")

    state_path = session_dir / "research" / "_state.md"
    if not state_path.is_file() or state_path.is_symlink():
        return fail(f"缺少真实 session state：{state_path}")
    text = state_path.read_text(encoding="utf-8")
    session_id = field(text, "session_id")
    topic_hash = field(text, "topic_sha256")
    if session_id != session_dir.name or not topic_hash:
        return fail("session state 的 session_id/topic_sha256 无效。")

    status = "complete" if args.phase == "complete" else "in_progress"
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    new_text = "\n".join(
        [
            "# Heavy Research Session State",
            "",
            f"- session_id: {session_id}",
            f"- topic_sha256: {topic_hash}",
            f"- status: {status}",
            f"- phase: {args.phase}",
            f"- updated_at: {now}",
            "",
        ]
    )
    tmp_path = state_path.with_name(f"_state.tmp-{os.getpid()}.md")
    tmp_path.write_text(new_text, encoding="utf-8")
    os.replace(tmp_path, state_path)

    active_path = workflows_dir / ".active-session"
    if status == "complete" and active_path.is_file() and not active_path.is_symlink():
        lines = active_path.read_text(encoding="utf-8").splitlines()
        active_value = Path(lines[0].strip()).resolve() if lines and lines[0].strip() else None
        if active_value == session_dir:
            active_path.unlink()

    print(f"SESSION_DIR={session_dir}")
    print(f"STATUS={status}")
    print(f"PHASE={args.phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
