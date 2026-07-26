#!/usr/bin/env python3
"""Apply the current file-backed, user-approved inline fix set transactionally."""

from __future__ import annotations

import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import tempfile

from fix_state_contract import (
    REVIEW_ID_RE,
    SHA256_RE,
    field,
    load_fix_state,
    parse_json_object,
    parse_ids,
    parse_iso,
    read_regular,
    valid_session_name,
)

def fail(message: str) -> int:
    print(json.dumps({"status": "error", "message": message}, ensure_ascii=False))
    return 1


def cleanup_temp(path: Path) -> str | None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return f"无法清理临时路径 {path}：{exc}"
    return None


def atomic_write(path: Path, text: str) -> None:
    if path.is_symlink():
        raise OSError(f"目标不得是 symlink：{path}")
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


def write_new_bytes(path: Path, payload: bytes) -> None:
    try:
        handle = path.open("xb")
    except OSError:
        raise
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        cleanup_error = cleanup_temp(path)
        detail = f"；{cleanup_error}" if cleanup_error else ""
        raise OSError(f"{exc}{detail}") from exc


def render_state(values: dict[str, str]) -> str:
    return "\n".join(
        ["# Heavy Review Inline Fix State", "", *(f"- {name}: {value}" for name, value in values.items()), ""]
    )


def load_fixes(path: Path) -> tuple[dict[str, object], bytes]:
    data = read_regular(path)
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OSError(f"fixes.json 无效：{exc}") from exc
    if not isinstance(value, dict):
        raise OSError("fixes.json 顶层必须是对象。")
    return value, data


def archive_prior_state(review_dir: Path, text: str, values: dict[str, str]) -> None:
    history_dir = review_dir / "fix-history"
    if history_dir.is_symlink() or (history_dir.exists() and not history_dir.is_dir()):
        raise OSError("review/fix-history 必须是真实目录。")
    history_dir.mkdir(exist_ok=True)
    target = history_dir / f"{values['review_run_id']}.md"
    payload = text.encode("utf-8")
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file() or read_regular(target) != payload:
            raise OSError("同一 review_run_id 的既有 fix-history 与当前 state 不一致。")
        return
    write_new_bytes(target, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_path")
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        return fail("当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。")
    workflows_root = workflows_dir.resolve()
    requested = Path(args.plan_path).expanduser()
    if requested.is_symlink():
        return fail("PLAN_PATH 不得是 symlink。")
    plan_path = requested.resolve()
    session_dir = plan_path.parent
    review_dir = session_dir / "review"
    if (
        session_dir.parent != workflows_root
        or not valid_session_name(session_dir.name)
        or plan_path.name != "deployment-plan.md"
        or not plan_path.is_file()
        or session_dir.is_symlink()
    ):
        return fail("PLAN_PATH 必须是当前仓库真实时间戳 session 下的 deployment-plan.md。")
    if review_dir.is_symlink() or not review_dir.is_dir():
        return fail("缺少真实 review/ 目录。")

    fixes_path = review_dir / "fixes.json"
    summary_path = review_dir / "summary.md"
    approval_path = review_dir / "_approval.md"
    state_path = review_dir / "fix-state.md"
    if state_path.is_symlink() or (state_path.exists() and not state_path.is_file()):
        return fail("fix-state.md 必须是真实普通文件，或尚不存在。")
    try:
        fixes, fixes_data = load_fixes(fixes_path)
        current_bytes = read_regular(plan_path)
        summary_data = read_regular(summary_path)
        approval_data = read_regular(approval_path)
        summary_text = summary_data.decode("utf-8")
        approval_text = approval_data.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        return fail(str(exc))

    session_id = fixes.get("session_id")
    review_run_id = fixes.get("review_run_id")
    expected_sha = fixes.get("expected_plan_sha256")
    replacements = fixes.get("replacements")
    if session_id != session_dir.name or not isinstance(review_run_id, str) or not isinstance(expected_sha, str):
        return fail("fixes.json 未绑定当前 session/review run。")
    review_match = REVIEW_ID_RE.fullmatch(review_run_id)
    if not review_match or review_match.group(1) != session_id:
        return fail("fixes.json 的 review_run_id 无效。")
    if not SHA256_RE.fullmatch(expected_sha):
        return fail("fixes.json 的 expected_plan_sha256 无效。")
    if not isinstance(replacements, list) or not replacements:
        return fail("fixes.json 的 replacements 必须是非空数组。")

    normalized: list[tuple[list[int], str, str]] = []
    replacement_ids: set[int] = set()
    for index, replacement in enumerate(replacements, start=1):
        if not isinstance(replacement, dict):
            return fail(f"replacement #{index} 不是对象。")
        raw_ids = replacement.get("item_ids")
        old = replacement.get("old")
        new = replacement.get("new")
        if (
            not isinstance(raw_ids, list)
            or not raw_ids
            or any(not isinstance(value, str) or not re.fullmatch(r"#\d+", value) for value in raw_ids)
        ):
            return fail(f"replacement #{index} 的 item_ids 无效。")
        item_ids = [int(value[1:]) for value in raw_ids]
        if len(item_ids) != len(set(item_ids)):
            return fail(f"replacement #{index} 的 item_ids 不得重复。")
        if not isinstance(old, str) or not isinstance(new, str) or not old or old == new:
            return fail(f"replacement #{index} 的 old/new 无效。")
        if (
            "[REVIEW-FIX]" not in new
            or "[[REPLACE:" in new
            or "\x00" in new
            or re.search(r"(?m)^\s*(?:-|\*|\d+[.)])?\s*\.\.\.\s*$", new)
        ):
            return fail(f"replacement #{index} 缺少 [REVIEW-FIX] 或仍含模板标记。")
        for item_id in item_ids:
            if not re.search(rf"(?<!\d)#{item_id}(?!\d)", new):
                return fail(f"replacement #{index} 的 new 缺少来源审查项 #{item_id}。")
        normalized.append((item_ids, old, new))
        replacement_ids.update(item_ids)

    summary_sha = hashlib.sha256(summary_data).hexdigest()
    fixes_sha = hashlib.sha256(fixes_data).hexdigest()
    current_sha = hashlib.sha256(current_bytes).hexdigest()
    approval_sha = hashlib.sha256(approval_data).hexdigest()
    required_approval = {
        "session_id": session_id,
        "review_run_id": review_run_id,
        "plan_sha256": expected_sha,
        "review_summary_sha256": summary_sha,
        "decision": "approved-inline-fixes",
    }
    for name, expected in required_approval.items():
        if field(approval_text, name) != expected:
            return fail(f"_approval.md 的 {name} 与当前 fix bundle 不一致。")
    approved_ids = parse_ids(field(approval_text, "approved_item_ids"))
    if approved_ids is None or set(approved_ids) != replacement_ids:
        return fail("fixes.json 的 item_ids 合集必须与用户 approved_item_ids 精确一致。")
    try:
        summarized_at = parse_iso(field(summary_text, "summarized_at"), "summary.md summarized_at")
        approved_at = parse_iso(field(approval_text, "approved_at"), "_approval.md approved_at")
    except OSError as exc:
        return fail(str(exc))
    if approved_at < summarized_at:
        return fail("_approval.md approved_at 不得早于 summary.md summarized_at。")

    prepared_backup: Path | None = None
    existing_state: str | None = None
    state_values: dict[str, str] | None = None
    if state_path.is_file() and not state_path.is_symlink():
        try:
            existing_state, state_values = load_fix_state(state_path, session_dir, review_dir)
        except OSError as exc:
            return fail(f"无法读取 fix-state.md：{exc}")
        if (
            state_values["session_id"] == session_id
            and state_values["review_run_id"] == review_run_id
            and state_values["base_plan_sha256"] == expected_sha
            and state_values["review_summary_sha256"] == summary_sha
            and state_values["fixes_sha256"] == fixes_sha
            and state_values["review_approval_sha256"] == approval_sha
            and set(parse_ids(state_values["approved_item_ids"]) or []) == replacement_ids
            and int(state_values["applied_replacements"]) == len(replacements)
        ):
            candidate_sha = state_values["candidate_plan_sha256"]
            status = state_values["status"]
            if candidate_sha and current_sha == candidate_sha and status in {
                "prepared",
                "applied-awaiting-post-fix-review",
                "verified",
            }:
                if status == "prepared":
                    values = dict(state_values)
                    values["status"] = "applied-awaiting-post-fix-review"
                    values["applied_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
                    try:
                        atomic_write(state_path, render_state(values))
                    except OSError as exc:
                        return fail(f"plan 已应用但无法修复 fix-state：{exc}")
                print(
                    json.dumps(
                        {
                            "status": "already-verified" if status == "verified" else "already-applied",
                            "new_plan_sha256": candidate_sha,
                            "backup_path": state_values["backup_path"],
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                return 0
            backup_value = state_values["backup_path"]
            if status == "prepared" and current_sha == expected_sha and backup_value:
                candidate_backup = Path(backup_value)
                try:
                    candidate_backup.relative_to(review_dir.resolve())
                except ValueError:
                    return fail("prepared backup_path 越过 review/ 边界。")
                prepared_backup = candidate_backup
            elif status in {"prepared", "applied-awaiting-post-fix-review", "verified"} and current_sha not in {
                expected_sha,
                candidate_sha,
            }:
                return fail("fix-state 与当前 plan hash 冲突，拒绝继续。")
        elif state_values["review_run_id"] == review_run_id:
            return fail("同一 review_run_id 的 fix-state 与当前 summary/fixes/approval 绑定冲突。")

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
        return fail(f"无法运行 review validator：{exc}")
    if checked.returncode != 0:
        return fail(checked.stdout.strip() or checked.stderr.strip() or "review bundle 校验失败。")
    try:
        validation = parse_json_object(checked.stdout, "review validator 输出")
    except OSError as exc:
        return fail(str(exc))
    if (
        validation.get("session_id") != session_id
        or validation.get("review_run_id") != review_run_id
        or validation.get("plan_sha256") != expected_sha
        or validation.get("verdict") != "changes-required"
        or current_sha != expected_sha
    ):
        return fail("fixes.json 未绑定当前需要修复的 review bundle。")

    try:
        updated = current_bytes.decode("utf-8")
    except UnicodeError as exc:
        return fail(f"plan 不是有效 UTF-8：{exc}")
    for index, (_, old, new) in enumerate(normalized, start=1):
        count = updated.count(old)
        if count != 1:
            return fail(f"replacement #{index} 的 old 必须精确匹配一次，实际 {count} 次。")
        updated = updated.replace(old, new, 1)
    updated_bytes = updated.encode("utf-8")
    candidate_sha = hashlib.sha256(updated_bytes).hexdigest()

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
        return fail(f"无法运行 review archiver：{exc}")
    if archived.returncode != 0:
        return fail(archived.stdout.strip() or archived.stderr.strip() or "无法归档当前 review run。")
    try:
        archive_path = parse_json_object(archived.stdout, "review archive 输出").get("path")
    except OSError as exc:
        return fail(str(exc))
    if not isinstance(archive_path, str) or not archive_path:
        return fail("review archive 未返回路径。")

    lock_path = review_dir / ".inline-fix.lock"
    if lock_path.is_symlink():
        return fail("inline-fix lock 不得是 symlink。")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except OSError as exc:
        return fail(f"无法打开 inline-fix lock：{exc}")
    try:
        lock_info = os.fstat(lock_fd)
    except OSError as exc:
        try:
            os.close(lock_fd)
        except OSError as close_exc:
            return fail(f"无法检查 inline-fix lock：{exc}；且无法关闭 lock fd：{close_exc}")
        return fail(f"无法检查 inline-fix lock：{exc}")
    if not stat.S_ISREG(lock_info.st_mode):
        try:
            os.close(lock_fd)
        except OSError as exc:
            return fail(f"inline-fix lock 不是普通文件，且无法关闭 lock fd：{exc}")
        return fail("inline-fix lock 必须是普通文件。")
    try:
        lock_handle = os.fdopen(lock_fd, "a+b", closefd=True)
    except OSError as exc:
        try:
            os.close(lock_fd)
        except OSError as close_exc:
            return fail(f"无法包装 inline-fix lock fd：{exc}；且无法关闭 fd：{close_exc}")
        return fail(f"无法包装 inline-fix lock fd：{exc}")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        original_bytes = read_regular(plan_path)
        if hashlib.sha256(original_bytes).hexdigest() != expected_sha:
            return fail("plan hash 已变化，拒绝套用旧修复。")
        original_mode = stat.S_IMODE(os.stat(plan_path, follow_symlinks=False).st_mode)

        if existing_state is not None and state_values is not None and state_values["review_run_id"] != review_run_id:
            try:
                archive_prior_state(review_dir, existing_state, state_values)
            except OSError as exc:
                return fail(f"无法归档上一轮 fix-state：{exc}")

        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d-%H%M%S")
        backup_path = prepared_backup
        if backup_path is not None:
            if backup_path.is_symlink() or not backup_path.is_file() or hashlib.sha256(read_regular(backup_path)).hexdigest() != expected_sha:
                return fail("prepared fix-state 的 backup_path 无效。")
        else:
            base_backup = review_dir / "deployment-plan.before-inline-fix.md"
            suffix = 0
            while True:
                candidate = base_backup if suffix == 0 else review_dir / f"deployment-plan.before-inline-fix.{timestamp}-{suffix}.md"
                try:
                    write_new_bytes(candidate, original_bytes)
                    backup_path = candidate
                    break
                except FileExistsError:
                    suffix += 1
        assert backup_path is not None

        prepared_values = {
            "session_id": session_id,
            "review_run_id": review_run_id,
            "base_plan_sha256": expected_sha,
            "candidate_plan_sha256": candidate_sha,
            "review_summary_sha256": summary_sha,
            "fixes_sha256": fixes_sha,
            "review_approval_sha256": approval_sha,
            "approved_item_ids": ", ".join(f"#{item}" for item in sorted(replacement_ids)),
            "archive_path": archive_path,
            "backup_path": str(backup_path.resolve()),
            "applied_replacements": str(len(replacements)),
            "status": "prepared",
            "prepared_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        try:
            atomic_write(state_path, render_state(prepared_values))
        except OSError as exc:
            return fail(f"无法写入 prepared fix-state：{exc}")

        fd, temp_name = tempfile.mkstemp(prefix="deployment-plan.candidate-", suffix=".md", dir=session_dir)
        candidate_error: OSError | None = None
        try:
            with os.fdopen(fd, "wb") as candidate_file:
                os.fchmod(candidate_file.fileno(), original_mode)
                candidate_file.write(updated_bytes)
                candidate_file.flush()
                os.fsync(candidate_file.fileno())
            if hashlib.sha256(read_regular(plan_path)).hexdigest() != expected_sha:
                raise OSError("plan 在候选文件准备期间发生变化，拒绝替换。")
            os.replace(temp_name, plan_path)
        except OSError as exc:
            candidate_error = exc
            try:
                os.close(fd)
            except OSError:
                pass
        cleanup_error = cleanup_temp(Path(temp_name))
        if candidate_error is not None:
            detail = f"；{cleanup_error}" if cleanup_error else ""
            raise OSError(f"{candidate_error}{detail}") from candidate_error
        if cleanup_error:
            raise OSError(cleanup_error)

        new_sha = hashlib.sha256(read_regular(plan_path)).hexdigest()
        if new_sha != candidate_sha:
            return fail("plan 原子替换后的 hash 与候选内容不一致。")
        applied_values = dict(prepared_values)
        applied_values["status"] = "applied-awaiting-post-fix-review"
        applied_values.pop("prepared_at")
        applied_values["applied_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            atomic_write(state_path, render_state(applied_values))
        except OSError as exc:
            return fail(f"plan 已应用且 prepared state 可恢复，但无法写入 applied state：{exc}")
        print(
            json.dumps(
                {
                    "status": "applied-awaiting-post-fix-review",
                    "new_plan_sha256": new_sha,
                    "backup_path": str(backup_path.resolve()),
                    "archive_path": archive_path,
                    "applied_replacements": len(replacements),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except OSError as exc:
        return fail(str(exc))
    finally:
        lock_cleanup_errors: list[str] = []
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        except OSError as exc:
            lock_cleanup_errors.append(f"无法释放 inline-fix lock：{exc}")
        try:
            lock_handle.close()
        except OSError as exc:
            lock_cleanup_errors.append(f"无法关闭 inline-fix lock：{exc}")
        if lock_cleanup_errors:
            print(
                json.dumps(
                    {"status": "cleanup-warning", "message": "；".join(lock_cleanup_errors)},
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )


if __name__ == "__main__":
    try:
        exit_code = main()
    except OSError as exc:
        exit_code = fail(f"未受控文件系统操作已收口：{exc}")
    raise SystemExit(exit_code)
