#!/usr/bin/env python3
"""Create a heavy-research session directory for Linux/Ubuntu hosts."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import secrets
import sys


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def rollback_created_session(session_dir: Path, research_dir: Path, state_path: Path) -> list[str]:
    errors: list[str] = []
    for path, operation in (
        (state_path, "unlink"),
        (research_dir, "rmdir"),
        (session_dir, "rmdir"),
    ):
        try:
            if operation == "unlink":
                if path.exists() or path.is_symlink():
                    path.unlink()
            elif path.exists():
                path.rmdir()
        except OSError as exc:
            errors.append(f"{path}: {exc}")
    return errors


def cleanup_temp(path: Path) -> str | None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return f"无法清理临时路径 {path}：{exc}"
    return None


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

    try:
        workflows_dir.mkdir(exist_ok=True)
    except OSError as exc:
        return fail(f"无法创建 .workflows/：{exc}")
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
        except OSError as exc:
            return fail(f"无法创建 session 目录：{exc}")

    research_dir = session_dir / "research"
    state_path = research_dir / "_state.md"
    active_session_file = workflows_dir / ".active-session"
    active_tmp = workflows_dir / f".active-session.tmp-{os.getpid()}-{secrets.token_hex(4)}"
    try:
        research_dir.mkdir()
        state_text = "\n".join(
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
        )
        with state_path.open("x", encoding="utf-8", newline="\n") as state_file:
            state_file.write(state_text)
            state_file.flush()
            os.fsync(state_file.fileno())

        resolved = session_dir.resolve()
        with active_tmp.open("x", encoding="utf-8", newline="\n") as active_file:
            active_file.write(f"{resolved}\n")
            active_file.flush()
            os.fsync(active_file.fileno())
        os.replace(active_tmp, active_session_file)
    except OSError as exc:
        temp_error = cleanup_temp(active_tmp)
        rollback_errors = rollback_created_session(session_dir, research_dir, state_path)
        detail = "；".join([*(rollback_errors or []), *([temp_error] if temp_error else [])])
        if detail:
            return fail(f"创建 session 事务失败：{exc}；回滚未完全成功：{detail}")
        return fail(f"创建 session 事务失败，已回滚新 session：{exc}")

    print(f"SESSION_DIR={resolved}")
    print(f"SESSION_ID={name}")
    print(f"TOPIC_SHA256={args.topic_hash}")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        exit_code = fail(f"文件系统操作失败：{exc}")
    raise SystemExit(exit_code)
