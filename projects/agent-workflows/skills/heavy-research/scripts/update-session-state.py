#!/usr/bin/env python3
"""Atomically update a heavy-research session phase and close active state."""

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
PHASES = {"B0", "B1", "B2", "B3", "B4", "C", "D", "complete"}
ALLOWED_TRANSITIONS = {
    "B0": {"B0", "B1"},
    "B1": {"B1", "B2"},
    "B2": {"B2", "B3"},
    "B3": {"B3", "B4"},
    "B4": {"B4", "C"},
    "C": {"C", "B1", "D"},
    "D": {"D", "complete"},
    "complete": {"complete"},
}


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


def cleanup_temp(path: Path) -> str | None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return f"无法清理临时路径 {path}：{exc}"
    return None


def field(text: str, name: str) -> str | None:
    matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
    return matches[0].strip() if len(matches) == 1 else None


def valid_session_name(name: str) -> bool:
    match = SESSION_RE.fullmatch(name)
    if not match:
        return False
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d-%H%M%S")
    except ValueError:
        return False
    return True


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


def atomic_write(path: Path, text: str) -> None:
    temp_path = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(4)}"
    )
    try:
        with temp_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    parser.add_argument("--phase", required=True, choices=sorted(PHASES))
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        return fail("当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。")
    workflows_root = workflows_dir.resolve()
    requested = Path(args.session_dir).expanduser()
    if requested.is_symlink():
        return fail("SESSION_DIR 不得是 symlink。")
    session_dir = requested.resolve()
    if session_dir.parent != workflows_root or not session_dir.is_dir() or not valid_session_name(session_dir.name):
        return fail("SESSION_DIR 必须是当前仓库 .workflows/ 下的合法时间戳目录。")

    research_dir = session_dir / "research"
    if research_dir.is_symlink() or not research_dir.is_dir() or research_dir.resolve().parent != session_dir:
        return fail("research/ 必须是当前 session 内的真实目录。")
    state_path = research_dir / "_state.md"
    if not state_path.is_file() or state_path.is_symlink():
        return fail(f"缺少真实 session state：{state_path}")
    try:
        text = read_regular_text(state_path)
    except (OSError, UnicodeError) as exc:
        return fail(f"无法读取 UTF-8 session state：{exc}")
    session_id = field(text, "session_id")
    topic_hash = field(text, "topic_sha256")
    current_status = field(text, "status")
    current_phase = field(text, "phase")
    updated_at = field(text, "updated_at")
    if session_id != session_dir.name or not topic_hash or not SHA256_RE.fullmatch(topic_hash):
        return fail("session state 的 session_id/topic_sha256 无效。")
    if current_status not in {"in_progress", "complete"} or current_phase not in PHASES:
        return fail("session state 的 status/phase 无效。")
    if (current_status == "complete") != (current_phase == "complete"):
        return fail("session state 的 status 与 phase 不一致。")
    try:
        parsed_updated_at = datetime.fromisoformat(updated_at or "")
    except ValueError:
        return fail("session state 的 updated_at 无效。")
    if parsed_updated_at.tzinfo is None or parsed_updated_at.utcoffset() is None:
        return fail("session state 的 updated_at 必须带时区。")
    if args.phase not in ALLOWED_TRANSITIONS[current_phase]:
        return fail(f"非法 phase 转移：{current_phase} -> {args.phase}")

    active_path = workflows_dir / ".active-session"
    if args.phase == "complete" and active_path.is_symlink():
        return fail(".active-session 是 symlink，拒绝在无法确认指向时关闭 session。")
    if args.phase == "complete" and active_path.exists() and not active_path.is_file():
        return fail(".active-session 存在但不是普通文件。")
    active_value: Path | None = None
    if args.phase == "complete" and active_path.is_file():
        try:
            active_lines = read_regular_text(active_path).splitlines()
        except (OSError, UnicodeError) as exc:
            return fail(f"无法读取 .active-session：{exc}")
        if len(active_lines) != 1 or not active_lines[0].strip():
            return fail(".active-session 必须是单行非空 canonical absolute path。")
        raw_active = Path(active_lines[0].strip())
        if not raw_active.is_absolute():
            return fail(".active-session 必须使用 absolute path。")
        try:
            active_value = raw_active.resolve()
        except (OSError, RuntimeError) as exc:
            return fail(f"无法解析 .active-session：{exc}")
        if str(active_value) != active_lines[0].strip():
            return fail(".active-session 必须使用 canonical absolute path。")

    status = "complete" if args.phase == "complete" else "in_progress"
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    new_text = "\n".join(
        [
            "# Heavy Research Session State",
            "",
            f"- session_id: {session_id}",
            f"- topic_sha256: {topic_hash}",
            f"- status: {status}",
            f"- phase: {args.phase}",
            f"- updated_at: {now}",
            "",
        ]
    )
    try:
        atomic_write(state_path, new_text)
    except OSError as exc:
        return fail(f"无法原子更新 session state：{exc}")

    if status == "complete" and active_path.is_file():
        if active_value == session_dir:
            try:
                active_path.unlink()
            except OSError as exc:
                try:
                    atomic_write(state_path, text)
                except OSError as restore_exc:
                    return fail(f"无法关闭 active pointer：{exc}；且无法恢复旧 state：{restore_exc}")
                return fail(f"无法关闭 active pointer，已恢复旧 state：{exc}")
    elif status == "in_progress":
        try:
            write_active_pointer(workflows_dir, session_dir)
        except OSError as exc:
            try:
                atomic_write(state_path, text)
            except OSError as restore_exc:
                return fail(f"无法刷新 .active-session：{exc}；且无法恢复旧 state：{restore_exc}")
            return fail(f"无法刷新 .active-session，已恢复旧 state：{exc}")

    print(f"SESSION_DIR={session_dir}")
    print(f"STATUS={status}")
    print(f"PHASE={args.phase}")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        exit_code = fail(f"文件系统操作失败：{exc}")
    raise SystemExit(exit_code)
