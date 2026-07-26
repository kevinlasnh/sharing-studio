#!/usr/bin/env python3
"""Hash the current Git-visible repository source state without writing it."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


def git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "--no-optional-locks", *args],
        cwd=Path.cwd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def main() -> int:
    root_result = git("rev-parse", "--show-toplevel")
    if root_result.returncode != 0:
        print(json.dumps({"status": "unverifiable", "reason": "当前目录不是 Git worktree。"}, ensure_ascii=False))
        return 0
    repo_root = Path(root_result.stdout.decode("utf-8").strip()).resolve()
    if repo_root != Path.cwd().resolve():
        print(json.dumps({"status": "unverifiable", "reason": "必须在 Git 仓库根目录运行。"}, ensure_ascii=False))
        return 0

    head_result = git("rev-parse", "--verify", "HEAD")
    head = head_result.stdout.decode("ascii").strip() if head_result.returncode == 0 else "unborn"
    files_result = git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if files_result.returncode != 0:
        reason = files_result.stderr.decode("utf-8", errors="replace").strip()
        print(json.dumps({"status": "unverifiable", "reason": reason or "git ls-files 失败。"}, ensure_ascii=False))
        return 0

    paths = sorted({part.decode("utf-8") for part in files_result.stdout.split(b"\0") if part})
    hasher = hashlib.sha256()
    count = 0
    for relative in paths:
        normalized = relative.replace("\\", "/")
        if normalized == ".workflows" or normalized.startswith(".workflows/"):
            continue
        path = repo_root / relative
        try:
            info = os.lstat(path)
        except FileNotFoundError:
            kind = b"missing"
            payload = b""
        else:
            if stat.S_ISLNK(info.st_mode):
                kind = b"symlink"
                payload = os.readlink(path).encode("utf-8")
            elif stat.S_ISREG(info.st_mode):
                kind = b"file"
                payload = path.read_bytes()
            else:
                kind = b"other"
                payload = str(stat.S_IFMT(info.st_mode)).encode("ascii")
        path_bytes = normalized.encode("utf-8")
        hasher.update(len(path_bytes).to_bytes(8, "big"))
        hasher.update(path_bytes)
        hasher.update(kind + b"\0")
        hasher.update(len(payload).to_bytes(8, "big"))
        hasher.update(payload)
        count += 1

    hasher.update(b"HEAD\0" + head.encode("ascii", errors="replace"))
    result = {
        "status": "confirmed",
        "repo_root": str(repo_root),
        "git_head": head,
        "source_snapshot_sha256": hasher.hexdigest(),
        "file_count": count,
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
