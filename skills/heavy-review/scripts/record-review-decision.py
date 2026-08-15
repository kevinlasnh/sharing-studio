#!/usr/bin/env python3
"""Persist a user decision bound to the current validated review summary."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys

from fix_state_contract import parse_json_object, read_regular, valid_session_name


def ids(value: str) -> list[int]:
    if value == "none":
        return []
    if not re.fullmatch(r"#\d+(?:\s*,\s*#\d+)*", value):
        raise ValueError("item ids 必须是 none 或逗号分隔的 #N 列表。")
    result = [int(item) for item in re.findall(r"#(\d+)", value)]
    if len(result) != len(set(result)):
        raise ValueError("item ids 不得重复。")
    return result


def cleanup_temp(path: Path) -> str | None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return f"无法清理临时 approval {path}：{exc}"
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
    parser.add_argument("--decision", required=True, choices=("approved-inline-fixes", "rejected-retry"))
    parser.add_argument("--item-ids", required=True)
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
        requested_ids = ids(args.item_ids)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if validation.get("verdict") != "changes-required":
        print("ERROR: 当前 review 已 PASS，不应记录 inline-fix 决策。", file=sys.stderr)
        return 1
    aggregate = validation.get("aggregate", {})
    if not isinstance(aggregate, dict) or not isinstance(aggregate.get("fail"), list) or not isinstance(aggregate.get("unverifiable"), list):
        print("ERROR: validator 未返回合法 aggregate。", file=sys.stderr)
        return 1
    actionable = sorted(set(aggregate["fail"]) | set(aggregate["unverifiable"]))
    if args.decision == "approved-inline-fixes":
        if sorted(requested_ids) != actionable:
            print("ERROR: approved item ids 必须精确等于当前全部 FAIL/UNVERIFIABLE item。", file=sys.stderr)
            return 1
    elif requested_ids:
        print("ERROR: rejected-retry 必须使用 --item-ids none。", file=sys.stderr)
        return 1

    summary_path = review_dir / "summary.md"
    if summary_path.is_symlink() or not summary_path.is_file():
        print("ERROR: 缺少真实 review/summary.md。", file=sys.stderr)
        return 1
    try:
        summary_sha = hashlib.sha256(read_regular(summary_path)).hexdigest()
    except OSError as exc:
        print(f"ERROR: 无法读取 review/summary.md：{exc}", file=sys.stderr)
        return 1
    if validation.get("summary_sha256") != summary_sha:
        print("ERROR: validator 返回的 summary hash 与当前 summary.md 不一致。", file=sys.stderr)
        return 1
    item_text = "none" if not requested_ids else ", ".join(f"#{item}" for item in requested_ids)
    approval_text = "\n".join(
        [
            "# Heavy Review Decision",
            "",
            f"- session_id: {validation['session_id']}",
            f"- review_run_id: {validation['review_run_id']}",
            f"- plan_sha256: {validation['plan_sha256']}",
            f"- review_summary_sha256: {summary_sha}",
            f"- decision: {args.decision}",
            f"- approved_item_ids: {item_text}",
            f"- approved_at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            "",
        ]
    )
    approval_path = review_dir / "_approval.md"
    if approval_path.is_symlink():
        print("ERROR: review/_approval.md 不得是 symlink。", file=sys.stderr)
        return 1
    try:
        atomic_write_text(approval_path, approval_text)
    except OSError as exc:
        print(f"ERROR: 无法持久化 review decision：{exc}", file=sys.stderr)
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
        or revalidation.get("session_id") != validation.get("session_id")
        or revalidation.get("review_run_id") != validation.get("review_run_id")
        or revalidation.get("plan_sha256") != validation.get("plan_sha256")
        or revalidation.get("summary_sha256") != summary_sha
    ):
        print("ERROR: review bundle 在记录用户决定期间发生变化；已写 approval 仍绑定旧 hash，拒绝继续。", file=sys.stderr)
        return 1

    if args.decision == "rejected-retry":
        archiver = Path(__file__).with_name("archive-review-run.py")
        try:
            archived = subprocess.run(
                [sys.executable, str(archiver), str(session_dir)],
                cwd=Path.cwd(),
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            print(f"ERROR: 无法运行 review archiver：{exc}", file=sys.stderr)
            return 1
        if archived.returncode != 0:
            print(archived.stdout.strip() or archived.stderr.strip(), file=sys.stderr)
            return 1
    print(json.dumps({"status": "recorded", "decision": args.decision, "approved_item_ids": requested_ids}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"ERROR: 文件系统操作失败：{exc}", file=sys.stderr)
        exit_code = 1
    raise SystemExit(exit_code)
