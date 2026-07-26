#!/usr/bin/env python3
"""Ensure a heavy-review session has a review directory."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create <SESSION_DIR>/review if needed.")
    parser.add_argument("session_dir", help="Path to the heavy workflow session directory.")
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        print("ERROR: 当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。", file=sys.stderr)
        return 1

    workflows_root = workflows_dir.resolve()
    requested = Path(args.session_dir).expanduser()
    if requested.is_symlink():
        print(f"ERROR: SESSION_DIR 不得是 symlink：{requested}", file=sys.stderr)
        return 1

    session_dir = requested.resolve()
    if (
        not session_dir.is_dir()
        or session_dir.parent != workflows_root
        or not SESSION_RE.match(session_dir.name)
    ):
        print(f"ERROR: SESSION_DIR 必须是当前仓库 .workflows/ 下的时间戳目录：{session_dir}", file=sys.stderr)
        return 1

    plan_path = session_dir / "deployment-plan.md"
    if not plan_path.is_file() or plan_path.is_symlink():
        print(f"ERROR: SESSION_DIR 中缺少真实 deployment-plan.md：{plan_path}", file=sys.stderr)
        return 1

    review_dir = session_dir / "review"
    if review_dir.is_symlink():
        print(f"ERROR: review 目录不得是 symlink：{review_dir}", file=sys.stderr)
        return 1
    if review_dir.exists() and not review_dir.is_dir():
        print(f"ERROR: review 路径存在但不是目录：{review_dir}", file=sys.stderr)
        return 1
    review_dir.mkdir(parents=True, exist_ok=True)
    print(review_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
