#!/usr/bin/env python3
"""Generate a collision-resistant review_run_id bound to one workflow session."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
import secrets
import sys

from fix_state_contract import read_regular


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")


def valid_session_name(name: str) -> bool:
    match = SESSION_RE.fullmatch(name)
    if not match:
        return False
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d-%H%M%S")
    except ValueError:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        print("ERROR: 当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。", file=sys.stderr)
        return 1
    workflows_root = workflows_dir.resolve()
    requested = Path(args.session_dir).expanduser()
    if requested.is_symlink():
        print("ERROR: SESSION_DIR 不得是 symlink。", file=sys.stderr)
        return 1
    session_dir = requested.resolve()
    if session_dir.parent != workflows_root or not session_dir.is_dir() or not valid_session_name(session_dir.name):
        print("ERROR: SESSION_DIR 必须是当前仓库真实时间戳 session。", file=sys.stderr)
        return 1

    review_dir = session_dir / "review"
    if review_dir.is_symlink() or not review_dir.is_dir():
        print("ERROR: 请先创建真实 review/ 目录。", file=sys.stderr)
        return 1
    existing_text = ""
    run_path = review_dir / "_run.md"
    if run_path.exists() or run_path.is_symlink():
        if run_path.is_symlink() or not run_path.is_file():
            print("ERROR: 当前 review/_run.md 必须是真实普通文件，或尚不存在。", file=sys.stderr)
            return 1
        try:
            existing_text = read_regular(run_path).decode("utf-8")
        except (OSError, UnicodeError) as exc:
            print(f"ERROR: 无法读取当前 review/_run.md：{exc}", file=sys.stderr)
            return 1
    history_dir = review_dir / "history"
    if history_dir.is_symlink() or (history_dir.exists() and not history_dir.is_dir()):
        print("ERROR: review/history 必须是真实目录，或尚不存在。", file=sys.stderr)
        return 1

    while True:
        run_id = f"{session_dir.name}-review-{secrets.token_hex(8)}"
        history_target = history_dir / run_id
        if run_id not in existing_text and not history_target.exists() and not history_target.is_symlink():
            print(f"REVIEW_RUN_ID={run_id}")
            return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"ERROR: 文件系统操作失败：{exc}", file=sys.stderr)
        exit_code = 1
    raise SystemExit(exit_code)
