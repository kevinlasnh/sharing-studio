#!/usr/bin/env python3
"""Ensure a heavy-review session has a review directory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create <SESSION_DIR>/review if needed.")
    parser.add_argument("session_dir", help="Path to the heavy workflow session directory.")
    args = parser.parse_args()

    session_dir = Path(args.session_dir).expanduser()
    if not session_dir.is_dir():
        print(f"ERROR: SESSION_DIR 不存在或不是目录：{session_dir}", file=sys.stderr)
        return 1

    review_dir = session_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    print(review_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
