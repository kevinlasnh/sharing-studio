#!/usr/bin/env python3
"""Mark an applied inline-fix transaction verified by a fresh PASS review run."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

from fix_state_contract import (
    field,
    load_fix_state,
    parse_iso,
    parse_json_object,
    read_regular,
    valid_session_name,
)


def cleanup_temp(path: Path) -> str | None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return f"无法清理临时 fix-state {path}：{exc}"
    return None


def atomic_write_text(path: Path, text: str) -> None:
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
    state_path = review_dir / "fix-state.md"
    if state_path.is_symlink() or not state_path.is_file():
        print("ERROR: 缺少真实 fix-state.md。", file=sys.stderr)
        return 1
    try:
        state, state_values = load_fix_state(state_path, session_dir, review_dir)
    except OSError as exc:
        print(f"ERROR: fix-state.md 契约无效：{exc}", file=sys.stderr)
        return 1
    if state_values["status"] != "applied-awaiting-post-fix-review":
        print("ERROR: fix-state 当前不等待 post-fix review。", file=sys.stderr)
        return 1
    original_review_id = state_values["review_run_id"]

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
    if validation.get("verdict") != "pass" or validation.get("mode") != "post-fix":
        print("ERROR: post-fix review 尚未全 PASS。", file=sys.stderr)
        return 1
    candidate_sha = state_values["candidate_plan_sha256"]
    if validation.get("plan_sha256") != candidate_sha:
        print("ERROR: PASS review 审查的不是 fix-state candidate plan。", file=sys.stderr)
        return 1
    summary_path = review_dir / "summary.md"
    if summary_path.is_symlink() or not summary_path.is_file():
        print("ERROR: 缺少真实 review summary。", file=sys.stderr)
        return 1
    validated_summary_sha = validation.get("summary_sha256")
    try:
        summary_data = read_regular(summary_path)
        summary_text = summary_data.decode("utf-8")
        current_summary_sha = hashlib.sha256(summary_data).hexdigest()
        applied_at = field(state, "applied_at")
        applied_time = parse_iso(applied_at, "fix-state applied_at")
        post_fix_summarized_at = parse_iso(
            field(summary_text, "summarized_at"), "post-fix summary.md summarized_at"
        )
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: 无法读取 post-fix summary：{exc}", file=sys.stderr)
        return 1
    if not isinstance(validated_summary_sha, str) or current_summary_sha != validated_summary_sha:
        print("ERROR: validator 返回的 post-fix summary hash 与当前文件不一致。", file=sys.stderr)
        return 1
    if post_fix_summarized_at < applied_time:
        print("ERROR: post-fix summary summarized_at 不得早于 fix-state applied_at。", file=sys.stderr)
        return 1

    if validation.get("review_run_id") == original_review_id:
        print("ERROR: post-fix review 必须使用新的 review_run_id。", file=sys.stderr)
        return 1

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
    try:
        revalidation = parse_json_object(rechecked.stdout, "review validator 复核输出")
    except OSError:
        revalidation = {}
    if (
        rechecked.returncode != 0
        or revalidation.get("verdict") != "pass"
        or revalidation.get("mode") != "post-fix"
        or revalidation.get("review_run_id") != validation.get("review_run_id")
        or revalidation.get("plan_sha256") != candidate_sha
        or revalidation.get("summary_sha256") != validated_summary_sha
    ):
        print("ERROR: post-fix review 在写 verified state 前发生变化。", file=sys.stderr)
        return 1
    try:
        if read_regular(state_path).decode("utf-8") != state:
            print("ERROR: fix-state 在 verified 写入前发生变化。", file=sys.stderr)
            return 1
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: 无法复核 fix-state 稳定性：{exc}", file=sys.stderr)
        return 1

    retained = []
    for name in (
        "session_id",
        "review_run_id",
        "base_plan_sha256",
        "candidate_plan_sha256",
        "review_summary_sha256",
        "fixes_sha256",
        "review_approval_sha256",
        "approved_item_ids",
        "archive_path",
        "backup_path",
        "applied_replacements",
    ):
        value = field(state, name)
        if value is None:
            print(f"ERROR: fix-state 缺少字段 {name}。", file=sys.stderr)
            return 1
        retained.append((name, value))
    verified_time = datetime.now().astimezone()
    if verified_time < post_fix_summarized_at:
        print("ERROR: verified_at 不得早于 post-fix summary summarized_at。", file=sys.stderr)
        return 1
    retained.append(("applied_at", applied_at))
    retained.extend(
        [
            ("post_fix_review_run_id", str(validation["review_run_id"])),
            ("post_fix_summary_sha256", validated_summary_sha),
            ("status", "verified"),
            ("verified_at", verified_time.isoformat(timespec="seconds")),
        ]
    )
    text = "\n".join(["# Heavy Review Inline Fix State", "", *(f"- {name}: {value}" for name, value in retained), ""])
    try:
        atomic_write_text(state_path, text)
    except OSError as exc:
        print(f"ERROR: 无法更新 fix-state：{exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "verified", "review_run_id": validation["review_run_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"ERROR: 文件系统操作失败：{exc}", file=sys.stderr)
        exit_code = 1
    raise SystemExit(exit_code)
