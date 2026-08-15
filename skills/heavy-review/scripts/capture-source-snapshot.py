#!/usr/bin/env python3
"""Hash one stable Git-visible repository source state without writing it."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


MAX_ATTEMPTS = 3


def git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "--no-optional-locks", *args],
        cwd=cwd or Path.cwd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def included_path(raw: bytes) -> str | None:
    path = raw.decode("utf-8")
    return None if path == ".workflows" or path.startswith(".workflows/") else path


def git_state() -> tuple[str, list[str], bytes, dict[str, tuple[str, str]]]:
    head_result = git("rev-parse", "--verify", "HEAD")
    head = head_result.stdout.decode("ascii").strip() if head_result.returncode == 0 else "unborn"
    index_result = git("ls-files", "--stage", "-z")
    others_result = git("ls-files", "-z", "--others", "--exclude-standard")
    if index_result.returncode != 0 or others_result.returncode != 0:
        reason = (index_result.stderr or others_result.stderr).decode("utf-8", errors="replace").strip()
        raise OSError(reason or "git ls-files 失败。")
    index: dict[str, tuple[str, str]] = {}
    for record in index_result.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_id, stage = metadata.split(b" ", 2)
            path = included_path(raw_path)
        except (ValueError, UnicodeError) as exc:
            raise OSError("无法解析 UTF-8 Git index entry。") from exc
        if stage != b"0":
            raise OSError("Git index 含未合并 stage，无法形成稳定 source snapshot。")
        if path is not None:
            index[path] = (mode.decode("ascii"), object_id.decode("ascii"))
    others: set[str] = set()
    for raw_path in others_result.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = included_path(raw_path)
        if path is not None:
            others.add(path)
    paths = sorted(set(index) | others)
    status_result = git(
        "status",
        "--porcelain=v2",
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=none",
        "--",
        ".",
        ":(exclude).workflows",
        ":(exclude).workflows/**",
    )
    if status_result.returncode != 0:
        reason = status_result.stderr.decode("utf-8", errors="replace").strip()
        raise OSError(reason or "git status 失败。")
    return head, paths, status_result.stdout, index


def stable_submodule(path: Path, expected_object: str) -> tuple[bytes, bytes]:
    if path.is_symlink() or not path.is_dir():
        raise OSError(f"submodule 缺失或不是实际目录：{path}")
    head_result = git("rev-parse", "--verify", "HEAD", cwd=path)
    if head_result.returncode != 0:
        reason = head_result.stderr.decode("utf-8", errors="replace").strip()
        raise OSError(reason or f"无法读取 submodule HEAD：{path}")
    actual_head = head_result.stdout.decode("ascii").strip()
    if actual_head != expected_object:
        raise OSError(f"submodule HEAD 与 index gitlink 不一致：{path}")
    status_result = git(
        "status",
        "--porcelain=v2",
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=none",
        cwd=path,
    )
    if status_result.returncode != 0:
        reason = status_result.stderr.decode("utf-8", errors="replace").strip()
        raise OSError(reason or f"无法检查 submodule 状态：{path}")
    if status_result.stdout:
        raise OSError(f"submodule 含未提交或未跟踪变化，无法精确绑定：{path}")
    return b"160000", actual_head.encode("ascii")


def stable_payload(path: Path) -> tuple[bytes, bytes]:
    try:
        before = os.lstat(path)
    except FileNotFoundError:
        return b"missing", b""
    signature_before = (before.st_mode, before.st_ino, before.st_size, before.st_mtime_ns)
    if stat.S_ISLNK(before.st_mode):
        kind = b"120000"
        payload = os.readlink(path).encode("utf-8")
    elif stat.S_ISREG(before.st_mode):
        kind = b"100755" if before.st_mode & 0o111 else b"100644"
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if (opened.st_mode, opened.st_ino, opened.st_size, opened.st_mtime_ns) != signature_before:
                raise RuntimeError("changed")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            payload = b"".join(chunks)
        finally:
            os.close(fd)
    else:
        raise OSError(
            f"Git-visible 路径不是可精确绑定的普通文件、symlink 或 clean submodule：{path}"
        )
    try:
        after = os.lstat(path)
    except FileNotFoundError as exc:
        raise RuntimeError("changed") from exc
    signature_after = (after.st_mode, after.st_ino, after.st_size, after.st_mtime_ns)
    if signature_after != signature_before:
        raise RuntimeError("changed")
    return kind, payload


def capture(repo_root: Path) -> dict[str, object]:
    head_before, paths_before, status_before, index_before = git_state()
    hasher = hashlib.sha256()
    count = 0
    for relative in paths_before:
        index_entry = index_before.get(relative)
        if index_entry is not None and index_entry[0] == "160000":
            kind, payload = stable_submodule(repo_root / relative, index_entry[1])
        else:
            kind, payload = stable_payload(repo_root / relative)
        path_bytes = relative.encode("utf-8")
        hasher.update(len(path_bytes).to_bytes(8, "big"))
        hasher.update(path_bytes)
        hasher.update(kind + b"\0")
        hasher.update(len(payload).to_bytes(8, "big"))
        hasher.update(payload)
        count += 1
    head_after, paths_after, status_after, index_after = git_state()
    if (
        head_after != head_before
        or paths_after != paths_before
        or status_after != status_before
        or index_after != index_before
    ):
        raise RuntimeError("changed")
    for relative, (mode, object_id) in sorted(index_before.items()):
        entry = f"{mode} {object_id} {relative}".encode("utf-8")
        hasher.update(b"INDEX\0" + len(entry).to_bytes(8, "big") + entry)
    hasher.update(b"STATUS\0" + len(status_before).to_bytes(8, "big") + status_before)
    hasher.update(b"HEAD\0" + head_before.encode("ascii", errors="replace"))
    return {
        "status": "confirmed",
        "repo_root": str(repo_root),
        "git_head": head_before,
        "source_snapshot_sha256": hasher.hexdigest(),
        "file_count": count,
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def main() -> int:
    try:
        root_result = git("rev-parse", "--show-toplevel")
    except OSError as exc:
        print(json.dumps({"status": "unverifiable", "reason": f"无法运行 Git：{exc}"}, ensure_ascii=False))
        return 0
    if root_result.returncode != 0:
        print(json.dumps({"status": "unverifiable", "reason": "当前目录不是 Git worktree。"}, ensure_ascii=False))
        return 0
    repo_root = Path(root_result.stdout.decode("utf-8").strip()).resolve()
    if repo_root != Path.cwd().resolve():
        print(json.dumps({"status": "unverifiable", "reason": "必须在 Git 仓库根目录运行。"}, ensure_ascii=False))
        return 0

    for _ in range(MAX_ATTEMPTS):
        try:
            result = capture(repo_root)
        except RuntimeError:
            continue
        except (OSError, UnicodeError) as exc:
            print(json.dumps({"status": "unverifiable", "reason": str(exc)}, ensure_ascii=False))
            return 0
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    print(
        json.dumps(
            {"status": "unverifiable", "reason": "源码状态在连续三次捕获期间发生变化，无法形成稳定 snapshot。"},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(json.dumps({"status": "unverifiable", "reason": str(exc)}, ensure_ascii=False))
        exit_code = 0
    raise SystemExit(exit_code)
