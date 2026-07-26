#!/usr/bin/env python3
"""Apply all user-approved inline plan replacements in one guarded transaction."""

from __future__ import annotations

import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> int:
    print(json.dumps({"status": "error", "message": message}, ensure_ascii=False))
    return 1


def field(text: str, name: str) -> str | None:
    matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
    return matches[0].strip() if len(matches) == 1 else None


def read_regular(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise OSError(f"不是普通文件：{path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_path")
    args = parser.parse_args()

    try:
        request = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError) as exc:
        return fail(f"stdin 必须是 UTF-8 JSON：{exc}")
    if not isinstance(request, dict):
        return fail("JSON 顶层必须是对象。")

    expected_sha = request.get("expected_plan_sha256")
    review_run_id = request.get("review_run_id")
    review_summary_sha = request.get("review_summary_sha256")
    replacements = request.get("replacements")
    if not isinstance(expected_sha, str) or not SHA256_RE.fullmatch(expected_sha):
        return fail("expected_plan_sha256 无效。")
    if not isinstance(review_run_id, str) or not review_run_id.strip():
        return fail("review_run_id 无效。")
    if not isinstance(review_summary_sha, str) or not SHA256_RE.fullmatch(review_summary_sha):
        return fail("review_summary_sha256 无效。")
    if not isinstance(replacements, list) or not replacements:
        return fail("replacements 必须是非空数组。")

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
        return fail("缺少真实 review/ 目录。")

    approval_path = review_dir / "_approval.md"
    if not approval_path.is_file() or approval_path.is_symlink():
        return fail("缺少真实 review/_approval.md。")
    approval_text = approval_path.read_text(encoding="utf-8")
    required = {
        "session_id": session_dir.name,
        "review_run_id": review_run_id,
        "plan_sha256": expected_sha,
        "review_summary_sha256": review_summary_sha,
        "decision": "approved-inline-fixes",
    }
    for name, expected in required.items():
        if field(approval_text, name) != expected:
            return fail(f"_approval.md 的 {name} 与本次请求不一致。")
    if not field(approval_text, "approved_item_ids") or not field(approval_text, "approved_at"):
        return fail("_approval.md 缺少 approved_item_ids 或 approved_at。")

    lock_path = review_dir / ".inline-fix.lock"
    if lock_path.is_symlink():
        return fail("inline-fix lock 不得是 symlink。")
    lock_handle = lock_path.open("a+b")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        original_bytes = read_regular(plan_path)
        actual_sha = hashlib.sha256(original_bytes).hexdigest()
        if actual_sha != expected_sha:
            return fail("plan hash 已变化，拒绝套用旧修复。")
        try:
            updated = original_bytes.decode("utf-8")
        except UnicodeError as exc:
            return fail(f"plan 不是有效 UTF-8：{exc}")

        for index, replacement in enumerate(replacements, start=1):
            if not isinstance(replacement, dict):
                return fail(f"replacement #{index} 不是对象。")
            old = replacement.get("old")
            new = replacement.get("new")
            if not isinstance(old, str) or not isinstance(new, str) or not old or old == new:
                return fail(f"replacement #{index} 的 old/new 无效。")
            count = updated.count(old)
            if count != 1:
                return fail(f"replacement #{index} 的 old 必须精确匹配一次，实际 {count} 次。")
            updated = updated.replace(old, new, 1)
        updated_bytes = updated.encode("utf-8")

        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d-%H%M%S")
        backup_path = review_dir / "deployment-plan.before-inline-fix.md"
        suffix = 0
        while True:
            candidate = backup_path if suffix == 0 else review_dir / f"deployment-plan.before-inline-fix.{timestamp}-{suffix}.md"
            try:
                with candidate.open("xb") as backup:
                    backup.write(original_bytes)
                    backup.flush()
                    os.fsync(backup.fileno())
                backup_path = candidate
                break
            except FileExistsError:
                suffix += 1

        fd, temp_name = tempfile.mkstemp(prefix="deployment-plan.candidate-", suffix=".md", dir=session_dir)
        try:
            with os.fdopen(fd, "wb") as candidate_file:
                candidate_file.write(updated_bytes)
                candidate_file.flush()
                os.fsync(candidate_file.fileno())
            if hashlib.sha256(read_regular(plan_path)).hexdigest() != expected_sha:
                os.unlink(temp_name)
                return fail("plan 在候选文件准备期间发生变化，拒绝替换。")
            os.replace(temp_name, plan_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

        new_sha = hashlib.sha256(read_regular(plan_path)).hexdigest()
        state_path = review_dir / "fix-state.md"
        state_text = "\n".join(
            [
                "# Heavy Review Inline Fix State",
                "",
                f"- session_id: {session_dir.name}",
                f"- review_run_id: {review_run_id}",
                f"- base_plan_sha256: {expected_sha}",
                f"- applied_plan_sha256: {new_sha}",
                f"- review_summary_sha256: {review_summary_sha}",
                f"- applied_replacements: {len(replacements)}",
                "- status: applied-awaiting-post-fix-review",
                f"- applied_at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
                "",
            ]
        )
        state_tmp = review_dir / f"fix-state.tmp-{os.getpid()}.md"
        state_tmp.write_text(state_text, encoding="utf-8")
        os.replace(state_tmp, state_path)
        print(
            json.dumps(
                {
                    "status": "applied-awaiting-post-fix-review",
                    "new_plan_sha256": new_sha,
                    "backup_path": str(backup_path.resolve()),
                    "applied_replacements": len(replacements),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (OSError, UnicodeError) as exc:
        return fail(str(exc))
    finally:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        finally:
            lock_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
