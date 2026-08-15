#!/usr/bin/env python3
"""Ensure a heavy-review session has a review directory."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
import re
import stat
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def read_regular_text(path: Path) -> str:
    if path.is_symlink():
        raise OSError(f"路径不得是 symlink：{path}")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise OSError(f"路径不是普通文件：{path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8")
    finally:
        os.close(fd)


def valid_session_name(name: str) -> bool:
    match = SESSION_RE.fullmatch(name)
    if not match:
        return False
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d-%H%M%S")
    except ValueError:
        return False
    return True


def is_legacy_plan(session_dir: Path) -> bool:
    try:
        text = read_regular_text(session_dir / "deployment-plan.md")
    except (OSError, UnicodeError):
        return False
    return re.search(r"(?m)^## Workflow Provenance\s*$", text) is None


def reviewable_state(session_dir: Path) -> bool:
    research_dir = session_dir / "research"
    if research_dir.is_symlink():
        return False
    if not research_dir.exists():
        return is_legacy_plan(session_dir)
    if not research_dir.is_dir() or research_dir.resolve().parent != session_dir:
        return False
    state_path = research_dir / "_state.md"
    if state_path.is_symlink():
        return False
    if not state_path.exists():
        return is_legacy_plan(session_dir)
    if not state_path.is_file():
        return False
    try:
        text = read_regular_text(state_path)
    except (OSError, UnicodeError):
        return False
    values = {
        name: re.findall(rf"(?m)^-\s+{name}:\s*(.*?)\s*$", text)
        for name in ("session_id", "topic_sha256", "status", "phase", "updated_at")
    }
    if any(len(matches) != 1 for matches in values.values()):
        return False
    if (
        values["session_id"][0].strip() != session_dir.name
        or not SHA256_RE.fullmatch(values["topic_sha256"][0].strip())
        or values["status"][0].strip() != "complete"
        or values["phase"][0].strip() != "complete"
    ):
        return False
    try:
        updated_at = datetime.fromisoformat(values["updated_at"][0].strip())
    except ValueError:
        return False
    return updated_at.tzinfo is not None and updated_at.utcoffset() is not None


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
        or not valid_session_name(session_dir.name)
    ):
        print(f"ERROR: SESSION_DIR 必须是当前仓库 .workflows/ 下的时间戳目录：{session_dir}", file=sys.stderr)
        return 1

    plan_path = session_dir / "deployment-plan.md"
    if not plan_path.is_file() or plan_path.is_symlink():
        print(f"ERROR: SESSION_DIR 中缺少真实 deployment-plan.md：{plan_path}", file=sys.stderr)
        return 1
    if not reviewable_state(session_dir):
        print("ERROR: Research state 必须是 complete 或可识别的 legacy session。", file=sys.stderr)
        return 1

    review_dir = session_dir / "review"
    if review_dir.is_symlink():
        print(f"ERROR: review 目录不得是 symlink：{review_dir}", file=sys.stderr)
        return 1
    if review_dir.exists() and not review_dir.is_dir():
        print(f"ERROR: review 路径存在但不是目录：{review_dir}", file=sys.stderr)
        return 1
    try:
        review_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"ERROR: 无法创建 review/ 目录：{exc}", file=sys.stderr)
        return 1
    print(review_dir.resolve())
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"ERROR: 文件系统操作失败：{exc}", file=sys.stderr)
        exit_code = 1
    raise SystemExit(exit_code)
