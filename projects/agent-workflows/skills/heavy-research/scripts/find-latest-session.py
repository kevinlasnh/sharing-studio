#!/usr/bin/env python3
"""Find the latest reusable heavy-research session on Linux/Ubuntu hosts."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
import re
import secrets
import stat
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IN_PROGRESS_PHASES = {"B0", "B1", "B2", "B3", "B4", "C", "D"}
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


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def cleanup_temp(path: Path) -> str | None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return f"无法清理临时路径 {path}：{exc}"
    return None


def field(text: str, name: str) -> str | None:
    matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
    return matches[0].strip() if len(matches) == 1 else None


def parse_session_name(name: str) -> tuple[datetime, int] | None:
    match = SESSION_RE.fullmatch(name)
    if not match:
        return None
    try:
        stamp = datetime.strptime(match.group(1), "%Y-%m-%d-%H%M%S")
    except ValueError:
        return None
    return stamp, int(match.group(2) or 0)


def session_state(path: Path, topic_hash: str) -> dict[str, str] | None:
    research_dir = path / "research"
    if research_dir.is_symlink() or not research_dir.is_dir() or research_dir.resolve().parent != path:
        return None
    state_path = research_dir / "_state.md"
    if not state_path.is_file() or state_path.is_symlink():
        return None
    try:
        text = read_regular_text(state_path)
    except (OSError, UnicodeError):
        return None
    values = {
        name: field(text, name)
        for name in ("session_id", "topic_sha256", "status", "phase", "updated_at")
    }
    if any(value is None for value in values.values()):
        return None
    if values["session_id"] != path.name or values["topic_sha256"] != topic_hash:
        return None
    if values["status"] != "in_progress" or values["phase"] not in IN_PROGRESS_PHASES:
        return None
    try:
        updated_at = datetime.fromisoformat(values["updated_at"] or "")
    except ValueError:
        return None
    if updated_at.tzinfo is None or updated_at.utcoffset() is None:
        return None
    return {name: value for name, value in values.items() if value is not None}


def is_session_dir(path: Path, workflows_root: Path, topic_hash: str) -> bool:
    if path.is_symlink():
        return False
    try:
        resolved = path.resolve()
        resolved.relative_to(workflows_root)
    except (OSError, RuntimeError, ValueError):
        return False

    if not resolved.is_dir():
        return False
    if resolved.parent != workflows_root:
        return False
    if parse_session_name(resolved.name) is None:
        return False
    return session_state(resolved, topic_hash) is not None


def session_sort_key(path: Path) -> tuple[datetime, int, str]:
    parsed = parse_session_name(path.name)
    return (*parsed, path.name) if parsed else (datetime.min, -1, path.name)


def latest_candidate(workflows_dir: Path, workflows_root: Path, topic_hash: str) -> Path | None:
    candidates = [
        path.resolve()
        for path in workflows_dir.iterdir()
        if is_session_dir(path, workflows_root, topic_hash)
    ]
    return max(candidates, key=session_sort_key) if candidates else None


def stable_latest_candidate(
    workflows_dir: Path,
    workflows_root: Path,
    topic_hash: str,
    scanner=None,
) -> tuple[bool, Path | None]:
    scan = scanner or latest_candidate
    for _ in range(MAX_ATTEMPTS):
        try:
            before = scan(workflows_dir, workflows_root, topic_hash)
            after = scan(workflows_dir, workflows_root, topic_hash)
        except OSError:
            continue
        if before == after:
            return True, after
    return False, None


def write_active_pointer(workflows_dir: Path, session_dir: Path) -> None:
    active_path = workflows_dir / ".active-session"
    if active_path.exists() and not active_path.is_file() and not active_path.is_symlink():
        raise OSError(f"active pointer 路径不是普通文件：{active_path}")
    temp_path = workflows_dir / f".active-session.tmp-{os.getpid()}-{secrets.token_hex(4)}"
    try:
        with temp_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(f"{session_dir.resolve()}\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, active_path)
    except OSError as exc:
        cleanup_error = cleanup_temp(temp_path)
        detail = f"；{cleanup_error}" if cleanup_error else ""
        raise OSError(f"{exc}{detail}") from exc
    cleanup_error = cleanup_temp(temp_path)
    if cleanup_error:
        raise OSError(cleanup_error)


def clear_active_pointer_if_matches(active_path: Path, session_dir: Path) -> str | None:
    try:
        if active_path.is_symlink() or not active_path.is_file():
            return f"无法确认刚写入的 active pointer：{active_path}"
        lines = read_regular_text(active_path).splitlines()
        expected = str(session_dir.resolve())
        if len(lines) == 1 and lines[0].strip() == expected:
            active_path.unlink()
            return None
        return "active pointer 已被其他进程改写，未清理"
    except (OSError, UnicodeError) as exc:
        return f"无法清理失效 active pointer：{exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic-hash", required=True)
    args = parser.parse_args()
    if not SHA256_RE.fullmatch(args.topic_hash):
        return fail("--topic-hash 必须是 64 位小写十六进制 SHA-256。")

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink():
        return fail(".workflows/ 不得是 symlink。")
    if not workflows_dir.is_dir():
        return fail("未找到 .workflows/ 目录。")

    workflows_root = workflows_dir.resolve()
    active_session_file = workflows_dir / ".active-session"

    if active_session_file.exists() or active_session_file.is_symlink():
        if active_session_file.is_symlink() or not active_session_file.is_file():
            warn(".active-session 不是普通文件，已忽略并等待合法 fallback 修复。")
        else:
            try:
                active = read_regular_text(active_session_file).splitlines()
            except (OSError, UnicodeError) as exc:
                warn(f"无法读取 .active-session，已忽略：{exc}")
                active = []
            if len(active) == 1 and active[0].strip():
                raw_active = active[0].strip()
                active_path = Path(raw_active)
                try:
                    resolved_active = active_path.resolve() if active_path.is_absolute() else None
                except (OSError, RuntimeError):
                    resolved_active = None
                if (
                    resolved_active is not None
                    and raw_active == str(resolved_active)
                    and is_session_dir(resolved_active, workflows_root, args.topic_hash)
                    and is_session_dir(resolved_active, workflows_root, args.topic_hash)
                ):
                    print(f"SESSION_DIR={resolved_active}")
                    print(f"SESSION_ID={resolved_active.name}")
                    print(f"TOPIC_SHA256={args.topic_hash}")
                    return 0
            warn(".active-session 不是当前主题的合法未完成 session，已忽略。")

    stable, latest = stable_latest_candidate(workflows_dir, workflows_root, args.topic_hash)
    if not stable:
        return fail("session 候选在连续扫描期间发生变化，无法稳定恢复。")
    if latest is None:
        return fail("未找到可复用的 session 目录。")

    try:
        write_active_pointer(workflows_dir, latest)
    except OSError as exc:
        return fail(f"找到 session，但无法原子修复 .active-session：{exc}")
    if not is_session_dir(latest, workflows_root, args.topic_hash):
        cleanup_issue = clear_active_pointer_if_matches(active_session_file, latest)
        detail = f"；{cleanup_issue}" if cleanup_issue else "；已清理刚写入的 pointer"
        return fail(f"session 在 active pointer 写回后失效，拒绝恢复{detail}。")
    print(f"SESSION_DIR={latest}")
    print(f"SESSION_ID={latest.name}")
    print(f"TOPIC_SHA256={args.topic_hash}")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        exit_code = fail(f"文件系统操作失败：{exc}")
    raise SystemExit(exit_code)
