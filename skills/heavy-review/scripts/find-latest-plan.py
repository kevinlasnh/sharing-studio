#!/usr/bin/env python3
"""Find the latest heavy-research deployment plan on Linux/Ubuntu hosts."""

from __future__ import annotations

from datetime import datetime
import os
import re
import stat
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_ATTEMPTS = 3


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


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def parse_session_name(name: str) -> tuple[datetime, int] | None:
    match = SESSION_RE.fullmatch(name)
    if not match:
        return None
    try:
        stamp = datetime.strptime(match.group(1), "%Y-%m-%d-%H%M%S")
    except ValueError:
        return None
    return stamp, int(match.group(2) or 0)


def session_sort_key(path: Path) -> tuple[datetime, int, str]:
    parsed = parse_session_name(path.name)
    return (*parsed, path.name) if parsed else (datetime.min, -1, path.name)


def is_legacy_plan(path: Path) -> bool:
    try:
        text = read_regular_text(path / "deployment-plan.md")
    except (OSError, UnicodeError):
        return False
    return re.search(r"(?m)^## Workflow Provenance\s*$", text) is None


def state_kind(path: Path) -> str | None:
    research_dir = path / "research"
    if research_dir.is_symlink():
        return None
    if not research_dir.exists():
        return "legacy" if is_legacy_plan(path) else None
    if not research_dir.is_dir() or research_dir.resolve().parent != path:
        return None
    state_path = research_dir / "_state.md"
    if state_path.is_symlink():
        return None
    if not state_path.exists():
        return "legacy" if is_legacy_plan(path) else None
    if not state_path.is_file():
        return None
    try:
        text = read_regular_text(state_path)
    except (OSError, UnicodeError):
        return None
    status = re.findall(r"(?m)^-\s+status:\s*(.*?)\s*$", text)
    phase = re.findall(r"(?m)^-\s+phase:\s*(.*?)\s*$", text)
    session_id = re.findall(r"(?m)^-\s+session_id:\s*(.*?)\s*$", text)
    topic_hash = re.findall(r"(?m)^-\s+topic_sha256:\s*(.*?)\s*$", text)
    updated_at = re.findall(r"(?m)^-\s+updated_at:\s*(.*?)\s*$", text)
    if (
        len(status) != 1
        or len(phase) != 1
        or len(session_id) != 1
        or len(topic_hash) != 1
        or len(updated_at) != 1
        or session_id[0].strip() != path.name
        or not SHA256_RE.fullmatch(topic_hash[0].strip())
    ):
        return None
    try:
        parsed = datetime.fromisoformat(updated_at[0].strip())
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return "complete" if status[0].strip() == "complete" and phase[0].strip() == "complete" else None


def reviewable_session(path: Path, workflows_root: Path) -> tuple[Path, str] | None:
    if path.is_symlink():
        return None
    resolved = path.resolve()
    if not resolved.is_dir() or resolved.parent != workflows_root:
        return None
    if parse_session_name(resolved.name) is None:
        return None
    plan_path = resolved / "deployment-plan.md"
    if plan_path.is_symlink() or not plan_path.is_file():
        return None
    kind = state_kind(resolved)
    return (resolved, kind) if kind is not None else None


def latest_candidate(workflows_dir: Path, workflows_root: Path) -> tuple[Path, str] | None:
    candidates = [
        candidate
        for path in workflows_dir.iterdir()
        if (candidate := reviewable_session(path, workflows_root)) is not None
    ]
    return max(candidates, key=lambda candidate: session_sort_key(candidate[0])) if candidates else None


def stable_latest_candidate(
    workflows_dir: Path,
    workflows_root: Path,
    scanner=None,
) -> tuple[bool, tuple[Path, str] | None]:
    scan = scanner or latest_candidate
    for _ in range(MAX_ATTEMPTS):
        try:
            before = scan(workflows_dir, workflows_root)
            after = scan(workflows_dir, workflows_root)
        except (OSError, RuntimeError):
            continue
        if before == after:
            return True, after
    return False, None


def main() -> int:
    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink():
        return fail(".workflows/ 不得是 symlink。")
    if not workflows_dir.is_dir():
        return fail("未找到 .workflows/ 目录。请先用 heavy-research 生成 deployment-plan。")

    workflows_root = workflows_dir.resolve()

    stable, candidate = stable_latest_candidate(workflows_dir, workflows_root)
    if not stable:
        return fail("session 候选在连续扫描期间发生变化，无法稳定定位最新 deployment-plan。")
    if candidate is None:
        return fail("未找到包含 deployment-plan.md 的 session 目录。请先用 heavy-research 生成 deployment-plan。")

    latest, state = candidate
    plan_path = latest / "deployment-plan.md"
    print(f"SESSION_DIR={latest}")
    print(f"PLAN_PATH={plan_path}")
    print(f"SESSION_STATE={state}")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        exit_code = fail(f"文件系统操作失败：{exc}")
    raise SystemExit(exit_code)
