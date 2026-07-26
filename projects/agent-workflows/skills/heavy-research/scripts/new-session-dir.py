#!/usr/bin/env python3
"""Create a heavy-research session directory for Linux/Ubuntu hosts."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import sys


SHA256_RE = __import__("re").compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic-hash", required=True, help="SHA-256 of the normalized Stage A topic and scope.")
    args = parser.parse_args()
    if not SHA256_RE.fullmatch(args.topic_hash):
        return fail("--topic-hash 必须是 64 位小写十六进制 SHA-256。")

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink():
        return fail(".workflows/ 不得是 symlink；拒绝把工作流文件写到仓库边界之外。")
    if workflows_dir.exists() and not workflows_dir.is_dir():
        return fail(".workflows 存在但不是目录。")

    workflows_dir.mkdir(exist_ok=True)
    now = datetime.now().astimezone()
    timestamp = now.strftime("%Y-%m-%d-%H%M%S")
    suffix = 0

    while True:
        name = timestamp if suffix == 0 else f"{timestamp}-{suffix}"
        session_dir = workflows_dir / name
        try:
            session_dir.mkdir()
            break
        except FileExistsError:
            suffix += 1

    research_dir = session_dir / "research"
    research_dir.mkdir()

    state_path = research_dir / "_state.md"
    state_path.write_text(
        "\n".join(
            [
                "# Heavy Research Session State",
                "",
                f"- session_id: {name}",
                f"- topic_sha256: {args.topic_hash}",
                "- status: in_progress",
                "- phase: B0",
                f"- updated_at: {now.isoformat(timespec='seconds')}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    resolved = session_dir.resolve()
    active_session_file = workflows_dir / ".active-session"
    active_tmp = workflows_dir / f".active-session.tmp-{os.getpid()}"
    active_tmp.write_text(f"{resolved}\n", encoding="utf-8")
    os.replace(active_tmp, active_session_file)

    print(f"SESSION_DIR={resolved}")
    print(f"SESSION_ID={name}")
    print(f"TOPIC_SHA256={args.topic_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
