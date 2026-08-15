#!/usr/bin/env python3
"""Archive the current validated review bundle before another run overwrites it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

from fix_state_contract import parse_json_object, valid_session_name


FILES = (
    "_run.md",
    "plan-snapshot.md",
    "provenance.json",
    "web.md",
    "source.md",
    "summary.md",
    "fixes.json",
    "_approval.md",
)


def field(text: str, name: str) -> str | None:
    matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
    return matches[0].strip() if len(matches) == 1 else None


def read_stable_regular(path: Path) -> bytes:
    if path.is_symlink():
        raise OSError(f"路径不得是 symlink：{path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise OSError(f"路径不是普通文件：{path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(fd)
        before_signature = (before.st_ino, before.st_size, before.st_mtime_ns)
        after_signature = (after.st_ino, after.st_size, after.st_mtime_ns)
        if before_signature != after_signature:
            raise OSError(f"文件在归档读取期间发生变化：{path}")
        return b"".join(chunks)
    finally:
        os.close(fd)


def snapshot_files(directory: Path, names: list[str]) -> dict[str, bytes]:
    return {name: read_stable_regular(directory / name) for name in names}


def manifest_for(data: dict[str, bytes]) -> dict[str, str]:
    return {name: hashlib.sha256(payload).hexdigest() for name, payload in data.items()}


def cleanup_tree(path: Path) -> str | None:
    try:
        if path.is_symlink():
            path.unlink()
        elif path.exists():
            shutil.rmtree(path)
    except OSError as exc:
        return f"无法清理临时归档目录 {path}：{exc}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        print("ERROR: 当前仓库缺少真实 .workflows/。", file=sys.stderr)
        return 1
    workflows_root = workflows_dir.resolve()
    requested = Path(args.session_dir).expanduser()
    if requested.is_symlink():
        print("ERROR: SESSION_DIR 不得是 symlink。", file=sys.stderr)
        return 1
    session_dir = requested.resolve()
    if session_dir.parent != workflows_root or not session_dir.is_dir() or not valid_session_name(session_dir.name):
        print("ERROR: SESSION_DIR 必须是当前仓库真实时间戳 session。", file=sys.stderr)
        return 1
    review_dir = session_dir / "review"
    if review_dir.is_symlink() or not review_dir.is_dir():
        print("ERROR: 缺少真实 review/ 目录。", file=sys.stderr)
        return 1
    validator = Path(__file__).with_name("validate-review-run.py")
    try:
        checked = subprocess.run(
            [sys.executable, str(validator), str(session_dir), "--require-summary"],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        print(f"ERROR: 无法运行 review validator：{exc}", file=sys.stderr)
        return 1
    if checked.returncode != 0:
        print(checked.stdout.strip() or checked.stderr.strip(), file=sys.stderr)
        return 1
    try:
        validation = parse_json_object(checked.stdout, "review validator 输出")
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    review_run_id = validation.get("review_run_id")
    if not isinstance(review_run_id, str) or not review_run_id:
        print("ERROR: validator 未返回 review_run_id。", file=sys.stderr)
        return 1

    history_dir = review_dir / "history"
    if history_dir.is_symlink() or (history_dir.exists() and not history_dir.is_dir()):
        print("ERROR: review/history 必须是真实目录，不能是 symlink。", file=sys.stderr)
        return 1
    try:
        history_dir.mkdir(exist_ok=True)
    except OSError as exc:
        print(f"ERROR: 无法创建 review/history：{exc}", file=sys.stderr)
        return 1
    target = history_dir / review_run_id

    names: list[str] = []
    for name in FILES:
        path = review_dir / name
        if path.exists() or path.is_symlink():
            if path.is_symlink() or not path.is_file():
                print(f"ERROR: 当前 review bundle 含非普通文件：{path}", file=sys.stderr)
                return 1
            names.append(name)
    required = {"_run.md", "plan-snapshot.md", "provenance.json", "web.md", "source.md", "summary.md"}
    if not required.issubset(names):
        missing = sorted(required - set(names))
        print(f"ERROR: 当前 review bundle 缺少文件：{', '.join(missing)}", file=sys.stderr)
        return 1
    try:
        source_data = snapshot_files(review_dir, names)
    except OSError as exc:
        print(f"ERROR: 无法稳定读取当前 review bundle：{exc}", file=sys.stderr)
        return 1
    source_manifest = manifest_for(source_data)

    try:
        rechecked = subprocess.run(
            [sys.executable, str(validator), str(session_dir), "--require-summary"],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        print(f"ERROR: 无法复核运行 review validator：{exc}", file=sys.stderr)
        return 1
    if rechecked.returncode != 0:
        print(rechecked.stdout.strip() or rechecked.stderr.strip(), file=sys.stderr)
        return 1
    try:
        if snapshot_files(review_dir, names) != source_data:
            print("ERROR: review bundle 在归档事务期间发生变化。", file=sys.stderr)
            return 1
    except OSError as exc:
        print(f"ERROR: 无法复核当前 review bundle：{exc}", file=sys.stderr)
        return 1

    if target.exists() or target.is_symlink():
        manifest_path = target / "manifest.json"
        if target.is_symlink() or not target.is_dir() or not manifest_path.is_file() or manifest_path.is_symlink():
            print("ERROR: 已存在的 history target 无效。", file=sys.stderr)
            return 1
        try:
            archived = parse_json_object(read_stable_regular(manifest_path), "history manifest")
        except OSError as exc:
            print(f"ERROR: 已存在 history manifest 无法读取：{exc}", file=sys.stderr)
            return 1
        try:
            archived_entries = {path.name for path in target.iterdir()}
        except OSError as exc:
            print(f"ERROR: 已存在 history 目录无法枚举：{exc}", file=sys.stderr)
            return 1
        expected_entries = set(source_manifest) | {"manifest.json"}
        if archived_entries != expected_entries:
            print("ERROR: 已存在 history 目录含 manifest 之外的额外或缺失文件。", file=sys.stderr)
            return 1
        try:
            archived_data = snapshot_files(target, names)
        except OSError as exc:
            print(f"ERROR: 已存在 history 内容无法验证：{exc}", file=sys.stderr)
            return 1
        if (
            archived.get("review_run_id") != review_run_id
            or archived.get("files") != source_manifest
            or manifest_for(archived_data) != source_manifest
        ):
            print("ERROR: 同一 review_run_id 的 history 内容与当前 bundle 不一致。", file=sys.stderr)
            return 1
        print(json.dumps({"status": "already-archived", "path": str(target.resolve())}, ensure_ascii=False))
        return 0

    try:
        temp_dir = Path(tempfile.mkdtemp(prefix=f".{review_run_id}.tmp-", dir=history_dir))
    except OSError as exc:
        print(f"ERROR: 无法创建临时归档目录：{exc}", file=sys.stderr)
        return 1
    archive_error: OSError | None = None
    try:
        for name in names:
            destination = temp_dir / name
            with destination.open("xb") as handle:
                handle.write(source_data[name])
                handle.flush()
                os.fsync(handle.fileno())
        manifest = {
            "review_run_id": review_run_id,
            "files": source_manifest,
        }
        manifest_path = temp_dir / "manifest.json"
        with manifest_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(temp_dir, target)
    except OSError as exc:
        archive_error = exc
    cleanup_error = cleanup_tree(temp_dir)
    if archive_error is not None or cleanup_error is not None:
        details = [str(archive_error)] if archive_error is not None else []
        if cleanup_error is not None:
            details.append(cleanup_error)
        print(f"ERROR: 无法归档 review run：{'；'.join(details)}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "archived", "path": str(target.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"ERROR: 文件系统操作失败：{exc}", file=sys.stderr)
        exit_code = 1
    raise SystemExit(exit_code)
