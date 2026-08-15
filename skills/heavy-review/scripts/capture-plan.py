#!/usr/bin/env python3
"""Capture one stable byte snapshot of deployment-plan.md and its SHA-256."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import os
import re
import secrets
import stat
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def cleanup_temp(path: Path) -> str | None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return f"无法清理临时 snapshot {path}：{exc}"
    return None


def atomic_write_snapshot(path: Path, data: bytes) -> None:
    temp_path = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(4)}"
    )
    try:
        with temp_path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except OSError as exc:
        cleanup_error = cleanup_temp(temp_path)
        detail = f"；{cleanup_error}" if cleanup_error else ""
        raise OSError(f"{exc}{detail}") from exc
    cleanup_error = cleanup_temp(temp_path)
    if cleanup_error:
        raise OSError(cleanup_error)


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
    parser.add_argument("plan_path")
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        return fail("当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。")
    workflows_root = workflows_dir.resolve()

    plan_path = Path(os.path.abspath(Path(args.plan_path).expanduser()))
    session_dir = plan_path.parent
    if (
        plan_path.is_symlink()
        or session_dir.is_symlink()
        or session_dir.parent != workflows_root
        or not valid_session_name(session_dir.name)
        or plan_path.name != "deployment-plan.md"
        or not plan_path.is_file()
    ):
        return fail("PLAN_PATH 必须是当前仓库合法时间戳 session 下的真实 deployment-plan.md。")

    review_dir = session_dir / "review"
    if review_dir.is_symlink() or not review_dir.is_dir():
        return fail("请先创建真实的 review/ 目录。")
    run_path = review_dir / "_run.md"
    if run_path.exists() or run_path.is_symlink():
        return fail("当前 review/ 已存在 _run.md；必须先 prepare 新 run，不能覆盖在用 snapshot。")
    snapshot_path = review_dir / "plan-snapshot.md"
    if snapshot_path.is_symlink():
        return fail("plan-snapshot.md 不得是 symlink。")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
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
    try:
        atomic_write_snapshot(snapshot_path, data)
    except OSError as exc:
        return fail(f"无法原子写入 plan snapshot：{exc}")

    print(f"SESSION_ID={session_dir.name}")
    print(f"PLAN_SHA256={digest}")
    print(f"PLAN_SNAPSHOT_PATH={snapshot_path.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        exit_code = fail(f"文件系统操作失败：{exc}")
    raise SystemExit(exit_code)
