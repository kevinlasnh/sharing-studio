#!/usr/bin/env python3
"""Hash one review checklist plan locator using the validator's canonical rule."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import os
from pathlib import Path
import re
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
    parser.add_argument("snapshot_path")
    parser.add_argument("locator")
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        print("ERROR: 当前仓库缺少真实 .workflows/。", file=sys.stderr)
        return 1
    workflows_root = workflows_dir.resolve()
    requested = Path(os.path.abspath(Path(args.snapshot_path).expanduser()))
    lexical_review = requested.parent
    lexical_session = lexical_review.parent
    if requested.is_symlink() or lexical_review.is_symlink() or lexical_session.is_symlink():
        print("ERROR: snapshot 及其 session/review 父级不得是 symlink。", file=sys.stderr)
        return 1
    path = requested
    review_dir = path.parent
    session_dir = review_dir.parent
    if (
        path.name != "plan-snapshot.md"
        or not path.is_file()
        or review_dir.name != "review"
        or session_dir.parent != workflows_root
        or not valid_session_name(session_dir.name)
    ):
        print("ERROR: snapshot 必须是当前仓库真实 session 的 review/plan-snapshot.md。", file=sys.stderr)
        return 1
    try:
        data = read_regular(path)
        data.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: 无法读取 UTF-8 snapshot：{exc}", file=sys.stderr)
        return 1

    match = re.fullmatch(r"lines\s+(\d+)-(\d+)", args.locator)
    if match:
        start, end = map(int, match.groups())
        lines = data.splitlines(keepends=True)
        if start < 1 or end < start or end > len(lines):
            print("ERROR: locator 超出 snapshot 行范围。", file=sys.stderr)
            return 1
        payload = b"".join(lines[start - 1:end])
    elif re.fullmatch(
        r"synthetic:(?:missing-section|plan-structure|provenance|source-snapshot):[^\s:][^\r\n]*",
        args.locator,
    ):
        payload = args.locator.encode("utf-8")
    else:
        print("ERROR: locator 必须是 lines N-M 或合法 synthetic locator。", file=sys.stderr)
        return 1
    print(f"STATEMENT_SHA256={hashlib.sha256(payload).hexdigest()}")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"ERROR: 文件系统操作失败：{exc}", file=sys.stderr)
        exit_code = 1
    raise SystemExit(exit_code)
