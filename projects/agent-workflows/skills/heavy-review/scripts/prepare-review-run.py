#!/usr/bin/env python3
"""Retire any current root bundle safely and prepare a fresh full review run."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import os
from pathlib import Path
import secrets
import subprocess
import sys

from fix_state_contract import field, load_fix_state, parse_ids, parse_json_object, read_regular, valid_session_name


RUN_FILES = (
    "_run.md",
    "plan-snapshot.md",
    "provenance.json",
    "web.md",
    "source.md",
    "summary.md",
    "fixes.json",
    "_approval.md",
)
MODES = ("initial", "resume", "rerun-after-feedback", "post-fix")


def existing_files(review_dir: Path) -> list[Path]:
    result: list[Path] = []
    for name in RUN_FILES:
        path = review_dir / name
        if path.exists() or path.is_symlink():
            if path.is_dir() and not path.is_symlink():
                raise OSError(f"run-scoped 路径意外成为目录：{path}")
            result.append(path)
    return result


def validate_recorded_decision(review_dir: Path, validation: dict[str, object]) -> str:
    approval_path = review_dir / "_approval.md"
    summary_path = review_dir / "summary.md"
    if approval_path.is_symlink() or not approval_path.is_file():
        raise OSError("changes-required summary 尚未记录真实 _approval.md，拒绝开始新 run。")
    if summary_path.is_symlink() or not summary_path.is_file():
        raise OSError("缺少用于绑定用户决定的真实 summary.md。")
    try:
        approval_text = read_regular(approval_path).decode("utf-8")
        summary_sha = hashlib.sha256(read_regular(summary_path)).hexdigest()
    except (OSError, UnicodeError) as exc:
        raise OSError(f"无法读取 review decision：{exc}") from exc
    if validation.get("summary_sha256") != summary_sha:
        raise OSError("validator 返回的 summary hash 与当前 summary.md 不一致。")
    expected = {
        "session_id": validation.get("session_id"),
        "review_run_id": validation.get("review_run_id"),
        "plan_sha256": validation.get("plan_sha256"),
        "review_summary_sha256": summary_sha,
    }
    for name, value in expected.items():
        if not isinstance(value, str) or field(approval_text, name) != value:
            raise OSError(f"_approval.md 的 {name} 未绑定当前 changes-required summary。")
    decision = field(approval_text, "decision")
    approved_ids = parse_ids(field(approval_text, "approved_item_ids"))
    aggregate = validation.get("aggregate")
    if not isinstance(aggregate, dict):
        raise OSError("validator 未返回合法 aggregate。")
    fail_ids = aggregate.get("fail")
    unverifiable_ids = aggregate.get("unverifiable")
    if not isinstance(fail_ids, list) or not isinstance(unverifiable_ids, list):
        raise OSError("validator aggregate 缺少 fail/unverifiable 列表。")
    actionable = sorted(set(fail_ids) | set(unverifiable_ids))
    if decision == "approved-inline-fixes":
        if approved_ids is None or sorted(approved_ids) != actionable:
            raise OSError("approved-inline-fixes 决定未精确覆盖全部可修复审查项。")
    elif decision == "rejected-retry":
        if approved_ids != []:
            raise OSError("rejected-retry 决定的 approved_item_ids 必须为 none。")
    else:
        raise OSError("_approval.md 的 decision 无效。")
    approved_at = field(approval_text, "approved_at")
    try:
        parsed = datetime.fromisoformat(approved_at or "")
    except ValueError as exc:
        raise OSError("_approval.md 的 approved_at 无效。") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OSError("_approval.md 的 approved_at 必须带时区。")
    return decision


def archived_bundle_matches(candidate: Path, current: list[Path]) -> bool:
    manifest_path = candidate / "manifest.json"
    if candidate.is_symlink() or not candidate.is_dir() or manifest_path.is_symlink() or not manifest_path.is_file():
        return False
    try:
        manifest = parse_json_object(read_regular(manifest_path), "history manifest")
    except OSError:
        return False
    expected = manifest.get("files")
    current_names = {path.name for path in current}
    if (
        manifest.get("review_run_id") != candidate.name
        or not isinstance(expected, dict)
        or not current_names.issubset(expected)
    ):
        return False
    try:
        if {path.name for path in candidate.iterdir()} != set(expected) | {"manifest.json"}:
            return False
    except OSError:
        return False
    for name, archived_hash in expected.items():
        if not isinstance(name, str) or not isinstance(archived_hash, str):
            return False
        try:
            if hashlib.sha256(read_regular(candidate / name)).hexdigest() != archived_hash:
                return False
        except OSError:
            return False
    for path in current:
        if path.is_symlink() or not path.is_file():
            return False
        try:
            digest = hashlib.sha256(read_regular(path)).hexdigest()
            archived_digest = hashlib.sha256(read_regular(candidate / path.name)).hexdigest()
        except OSError:
            return False
        if expected.get(path.name) != digest or archived_digest != digest:
            return False
    return True


def unlink_archived(paths: list[Path]) -> None:
    ordered = [path for path in paths if path.name != "_run.md"]
    ordered.extend(path for path in paths if path.name == "_run.md")
    for path in ordered:
        try:
            path.unlink()
        except OSError as exc:
            raise OSError(f"bundle 已归档，但无法清理当前文件 {path}：{exc}") from exc


def move_invalid_bundle(current: list[Path], orphan_dir: Path) -> None:
    moved: list[tuple[Path, Path]] = []
    try:
        for source in current:
            destination = orphan_dir / source.name
            os.rename(source, destination)
            moved.append((source, destination))
    except OSError as exc:
        rollback_errors: list[str] = []
        for source, destination in reversed(moved):
            try:
                os.rename(destination, source)
            except OSError as rollback_exc:
                rollback_errors.append(f"{destination} -> {source}: {rollback_exc}")
        detail = f"；回滚失败：{'；'.join(rollback_errors)}" if rollback_errors else "；已回滚已移动文件"
        raise OSError(f"无法移动 invalid bundle：{exc}{detail}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    parser.add_argument("--mode", required=True, choices=MODES)
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        print("ERROR: 当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。", file=sys.stderr)
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
    try:
        current = existing_files(review_dir)
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    fix_state = review_dir / "fix-state.md"
    if fix_state.is_symlink() or (fix_state.exists() and not fix_state.is_file()):
        print("ERROR: fix-state.md 必须是真实普通文件，或尚不存在。", file=sys.stderr)
        return 1
    if fix_state.is_file():
        try:
            _, state_values = load_fix_state(fix_state, session_dir, review_dir)
        except OSError as exc:
            print(f"ERROR: fix-state.md 契约无效：{exc}", file=sys.stderr)
            return 1
        state_status = state_values["status"]
        if state_status == "prepared":
            print(
                "ERROR: inline fix 仍处于 prepared；必须先幂等重跑 apply-inline-fixes.py 完成或修复 plan 应用，不能开始 post-fix review。",
                file=sys.stderr,
            )
            return 1
        waiting = state_status == "applied-awaiting-post-fix-review"
        if waiting:
            plan_path = session_dir / "deployment-plan.md"
            try:
                live_sha = hashlib.sha256(read_regular(plan_path)).hexdigest()
            except OSError as exc:
                print(f"ERROR: 无法验证等待 post-fix 的 live plan：{exc}", file=sys.stderr)
                return 1
            if live_sha != state_values["candidate_plan_sha256"]:
                print("ERROR: 等待 post-fix 的 live plan 不等于 fix-state candidate hash。", file=sys.stderr)
                return 1
        if waiting and args.mode != "post-fix":
            print("ERROR: 当前存在等待验证的 inline fix，新 run 必须使用 mode=post-fix。", file=sys.stderr)
            return 1
        if args.mode == "post-fix" and not waiting:
            print("ERROR: mode=post-fix 需要 applied-awaiting-post-fix-review fix-state。", file=sys.stderr)
            return 1
    elif args.mode == "post-fix":
        print("ERROR: mode=post-fix 需要 fix-state.md。", file=sys.stderr)
        return 1

    retired_path: str | None = None
    if current:
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
        if checked.returncode == 0:
            try:
                validation = parse_json_object(checked.stdout, "review validator 输出")
            except OSError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
            if validation.get("verdict") == "changes-required":
                try:
                    decision = validate_recorded_decision(review_dir, validation)
                except OSError as exc:
                    print(f"ERROR: {exc}", file=sys.stderr)
                    return 1
                if decision == "approved-inline-fixes" and args.mode != "post-fix":
                    print("ERROR: 已批准 inline fixes；必须先应用修复，再以 mode=post-fix 开始新 run。", file=sys.stderr)
                    return 1
                if decision == "rejected-retry" and args.mode not in {"rerun-after-feedback", "post-fix"}:
                    print("ERROR: rejected-retry 后的新 run 必须是 rerun-after-feedback 或待验证事务下的 post-fix。", file=sys.stderr)
                    return 1
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
            try:
                retired_path = parse_json_object(archived.stdout, "archive helper 输出").get("path")
            except OSError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
            if not isinstance(retired_path, str) or not retired_path:
                print("ERROR: archive helper 未返回合法归档路径。", file=sys.stderr)
                return 1
            try:
                unlink_archived(current)
            except OSError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
        else:
            history_dir = review_dir / "history"
            if history_dir.is_symlink() or (history_dir.exists() and not history_dir.is_dir()):
                print("ERROR: review/history 必须是真实目录。", file=sys.stderr)
                return 1
            try:
                history_dir.mkdir(exist_ok=True)
            except OSError as exc:
                print(f"ERROR: 无法创建 review/history：{exc}", file=sys.stderr)
                return 1
            archived_current: Path | None = None
            run_path = review_dir / "_run.md"
            if run_path.is_file() and not run_path.is_symlink():
                try:
                    run_id = field(read_regular(run_path).decode("utf-8"), "review_run_id")
                except (OSError, UnicodeError):
                    run_id = None
                if run_id:
                    candidate = history_dir / run_id
                    if archived_bundle_matches(candidate, current):
                        archived_current = candidate
            if archived_current is not None:
                try:
                    unlink_archived(current)
                except OSError as exc:
                    print(f"ERROR: {exc}", file=sys.stderr)
                    return 1
                retired_path = str(archived_current.resolve())
                current = []
            if not current:
                pass
            else:
                orphan_name = f"orphan-{datetime.now().astimezone().strftime('%Y-%m-%d-%H%M%S')}-{secrets.token_hex(4)}"
                orphan_dir = history_dir / orphan_name
                try:
                    orphan_dir.mkdir()
                except OSError as exc:
                    print(f"ERROR: 无法创建 invalid bundle 归档目录：{exc}", file=sys.stderr)
                    return 1
                reason_path = orphan_dir / "validation-error.txt"
                try:
                    with reason_path.open("x", encoding="utf-8", newline="\n") as handle:
                        handle.write(checked.stdout.strip() or checked.stderr.strip() or "current bundle invalid")
                        handle.write("\n")
                        handle.flush()
                        os.fsync(handle.fileno())
                    move_invalid_bundle(current, orphan_dir)
                except OSError as exc:
                    cleanup_errors: list[str] = []
                    try:
                        if reason_path.is_symlink() or reason_path.is_file():
                            reason_path.unlink()
                    except OSError as cleanup_exc:
                        cleanup_errors.append(f"无法清理错误说明：{cleanup_exc}")
                    try:
                        orphan_dir.rmdir()
                    except OSError as cleanup_exc:
                        cleanup_errors.append(f"无法清理空 orphan 目录：{cleanup_exc}")
                    detail = f"；{'；'.join(cleanup_errors)}" if cleanup_errors else ""
                    print(f"ERROR: 无法保存 invalid current bundle：{exc}{detail}", file=sys.stderr)
                    return 1
                retired_path = str(orphan_dir.resolve())

    generator = Path(__file__).with_name("new-review-run-id.py")
    try:
        generated = subprocess.run(
            [sys.executable, str(generator), str(session_dir)],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        print(f"ERROR: 无法运行 review run id generator：{exc}", file=sys.stderr)
        return 1
    if generated.returncode != 0:
        print(generated.stderr.strip() or generated.stdout.strip(), file=sys.stderr)
        return 1
    run_id = generated.stdout.strip().removeprefix("REVIEW_RUN_ID=")
    print(f"REVIEW_RUN_ID={run_id}")
    print(f"MODE={args.mode}")
    print(f"RETIRED_PATH={retired_path or 'none'}")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"ERROR: 文件系统操作失败：{exc}", file=sys.stderr)
        exit_code = 1
    raise SystemExit(exit_code)
