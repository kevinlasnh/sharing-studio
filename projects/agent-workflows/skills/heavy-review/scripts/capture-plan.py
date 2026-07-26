#!/usr/bin/env python3
"""Capture one stable byte snapshot of deployment-plan.md and its SHA-256."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_path")
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        return fail("当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。")
    workflows_root = workflows_dir.resolve()

    requested = Path(args.plan_path).expanduser()
    if requested.is_symlink():
        return fail("PLAN_PATH 不得是 symlink。")
    plan_path = requested.resolve()
    session_dir = plan_path.parent
    if session_dir.parent != workflows_root or not SESSION_RE.fullmatch(session_dir.name):
        return fail("PLAN_PATH 必须位于当前仓库合法时间戳 session 中。")

    review_dir = session_dir / "review"
    if review_dir.is_symlink() or not review_dir.is_dir():
        return fail("请先创建真实的 review/ 目录。")
    snapshot_path = review_dir / "plan-snapshot.md"
    if snapshot_path.is_symlink():
        return fail("plan-snapshot.md 不得是 symlink。")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(plan_path, flags)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                return fail("deployment-plan.md 不是普通文件。")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
        finally:
            os.close(fd)
        data = b"".join(chunks)
        data.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        return fail(f"无法稳定读取 UTF-8 plan：{exc}")
    if not data.strip():
        return fail("deployment-plan.md 去除空白后为空。")

    digest = hashlib.sha256(data).hexdigest()
    temp_path = review_dir / f"plan-snapshot.tmp-{os.getpid()}.md"
    with temp_path.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, snapshot_path)

    print(f"PLAN_SHA256={digest}")
    print(f"PLAN_SNAPSHOT_PATH={snapshot_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
