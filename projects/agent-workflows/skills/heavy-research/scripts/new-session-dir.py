#!/usr/bin/env python3
"""Create a heavy-research session directory for Linux/Ubuntu hosts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def main() -> int:
    workflows_dir = Path(".workflows")
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    suffix = 0

    while True:
        name = timestamp if suffix == 0 else f"{timestamp}-{suffix}"
        session_dir = workflows_dir / name
        if not session_dir.exists():
            break
        suffix += 1

    research_dir = session_dir / "research"
    research_dir.mkdir(parents=True, exist_ok=True)

    resolved = session_dir.resolve()
    active_session_file = workflows_dir / ".active-session"
    active_session_file.write_text(f"{resolved}\n", encoding="utf-8")

    print(f"SESSION_DIR={resolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
