"""Shared read-only validation for Heavy Review inline-fix transaction state."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVIEW_ID_RE = re.compile(r"^(.+)-review-([0-9a-f]{16})$")
ARCHIVE_FILES = {
    "_run.md",
    "plan-snapshot.md",
    "provenance.json",
    "web.md",
    "source.md",
    "summary.md",
    "fixes.json",
    "_approval.md",
}


def field(text: str, name: str) -> str | None:
    matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
    if len(matches) != 1:
        return None
    value = matches[0].strip()
    return value or None


def parse_ids(value: str | None) -> list[int] | None:
    if value == "none":
        return []
    if value is None or not re.fullmatch(r"#\d+(?:\s*,\s*#\d+)*", value):
        return None
    result = [int(item) for item in re.findall(r"#(\d+)", value)]
    return result if len(result) == len(set(result)) else None


def valid_session_name(name: str) -> bool:
    match = SESSION_RE.fullmatch(name)
    if not match:
        return False
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d-%H%M%S")
    except ValueError:
        return False
    return True


def read_regular(path: Path) -> bytes:
    if path.is_symlink():
        raise OSError(f"路径不得是 symlink：{path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
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
        return b"".join(chunks)
    finally:
        os.close(fd)


def parse_iso(value: str | None, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value or "")
    except ValueError as exc:
        raise OSError(f"{name} 无效。") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OSError(f"{name} 必须带时区。")
    return parsed


def parse_json_object(raw: str | bytes, name: str) -> dict[str, object]:
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        value = json.loads(text)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OSError(f"{name} 不是合法 UTF-8 JSON：{exc}") from exc
    if not isinstance(value, dict):
        raise OSError(f"{name} 顶层必须是 object。")
    return value


def canonical_child(raw: str | None, parent: Path, name: str) -> Path:
    if raw is None:
        raise OSError(f"fix-state 缺少 {name}。")
    path = Path(raw)
    if not path.is_absolute() or str(path.resolve()) != raw:
        raise OSError(f"fix-state 的 {name} 必须是 canonical absolute path。")
    resolved_parent = parent.resolve()
    try:
        path.relative_to(resolved_parent)
    except ValueError as exc:
        raise OSError(f"fix-state 的 {name} 越过 {parent.name}/ 边界。") from exc
    return path


def require_exact_manifest_entries(directory: Path, files: dict[str, object], name: str) -> None:
    try:
        entries = {path.name for path in directory.iterdir()}
    except OSError as exc:
        raise OSError(f"{name} 无法枚举：{exc}") from exc
    expected = set(files) | {"manifest.json"}
    if entries != expected:
        raise OSError(f"{name} 含 manifest 之外的额外或缺失文件。")


def validate_archive(values: dict[str, str], review_dir: Path) -> tuple[datetime, datetime]:
    archive_path = canonical_child(values["archive_path"], review_dir / "history", "archive_path")
    if archive_path.name != values["review_run_id"] or archive_path.is_symlink() or not archive_path.is_dir():
        raise OSError("fix-state 的 archive_path 不是当前 review run 的真实 history 目录。")
    manifest_path = archive_path / "manifest.json"
    try:
        manifest = json.loads(read_regular(manifest_path).decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OSError(f"fix-state 的 archive manifest 无效：{exc}") from exc
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(manifest, dict) or manifest.get("review_run_id") != values["review_run_id"] or not isinstance(files, dict):
        raise OSError("fix-state 的 archive manifest 未绑定当前 review_run_id。")
    if not set(files).issubset(ARCHIVE_FILES) or not {
        "_run.md",
        "plan-snapshot.md",
        "provenance.json",
        "web.md",
        "source.md",
        "summary.md",
        "fixes.json",
        "_approval.md",
    }.issubset(files):
        raise OSError("fix-state 的 archive manifest 文件集合无效。")
    require_exact_manifest_entries(archive_path, files, "fix-state 的 archive 目录")
    for name, expected in files.items():
        if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
            raise OSError(f"fix-state 的 archive manifest 含非法 hash：{name}")
        actual = hashlib.sha256(read_regular(archive_path / name)).hexdigest()
        if actual != expected:
            raise OSError(f"fix-state 的 archive 文件已变化：{name}")
    expected_bindings = {
        "plan-snapshot.md": values["base_plan_sha256"],
        "summary.md": values["review_summary_sha256"],
        "fixes.json": values["fixes_sha256"],
        "_approval.md": values["review_approval_sha256"],
    }
    for name, expected in expected_bindings.items():
        if files.get(name) != expected:
            raise OSError(f"fix-state 的 {name} hash 与 archive manifest 不一致。")

    try:
        plan_text = read_regular(archive_path / "plan-snapshot.md").decode("utf-8")
        run_text = read_regular(archive_path / "_run.md").decode("utf-8")
        summary_text = read_regular(archive_path / "summary.md").decode("utf-8")
        approval_text = read_regular(archive_path / "_approval.md").decode("utf-8")
        fixes = json.loads(read_regular(archive_path / "fixes.json").decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OSError(f"fix-state 的 archive 语义文件无效：{exc}") from exc

    run_expected = {
        "session_id": values["session_id"],
        "review_run_id": values["review_run_id"],
        "plan_sha256": values["base_plan_sha256"],
    }
    for name, expected in run_expected.items():
        if field(run_text, name) != expected:
            raise OSError(f"archived _run.md 的 {name} 与 fix-state 不一致。")

    summary_expected = {
        "session_id": values["session_id"],
        "review_run_id": values["review_run_id"],
        "plan_sha256": values["base_plan_sha256"],
        "fixes_sha256": values["fixes_sha256"],
        "verdict": "changes-required",
    }
    for name, expected in summary_expected.items():
        if field(summary_text, name) != expected:
            raise OSError(f"archived summary.md 的 {name} 与 fix-state 不一致。")
    summarized_at = parse_iso(field(summary_text, "summarized_at"), "archived summary.md summarized_at")

    approved_state = parse_ids(values["approved_item_ids"])
    approval_expected = {
        "session_id": values["session_id"],
        "review_run_id": values["review_run_id"],
        "plan_sha256": values["base_plan_sha256"],
        "review_summary_sha256": values["review_summary_sha256"],
        "decision": "approved-inline-fixes",
    }
    for name, expected in approval_expected.items():
        if field(approval_text, name) != expected:
            raise OSError(f"archived _approval.md 的 {name} 与 fix-state 不一致。")
    approval_ids = parse_ids(field(approval_text, "approved_item_ids"))
    if approved_state is None or approval_ids != approved_state:
        raise OSError("archived _approval.md 的 approved_item_ids 与 fix-state 不一致。")
    approved_at = parse_iso(field(approval_text, "approved_at"), "archived _approval.md approved_at")
    if approved_at < summarized_at:
        raise OSError("archived _approval.md approved_at 不得早于 summary.md summarized_at。")

    if not isinstance(fixes, dict):
        raise OSError("archived fixes.json 顶层必须是对象。")
    fixes_expected = {
        "session_id": values["session_id"],
        "review_run_id": values["review_run_id"],
        "expected_plan_sha256": values["base_plan_sha256"],
    }
    for name, expected in fixes_expected.items():
        if fixes.get(name) != expected:
            raise OSError(f"archived fixes.json 的 {name} 与 fix-state 不一致。")
    replacements = fixes.get("replacements")
    if not isinstance(replacements, list) or not replacements:
        raise OSError("archived fixes.json 的 replacements 必须是非空数组。")

    candidate = plan_text
    covered: set[int] = set()
    for index, replacement in enumerate(replacements, start=1):
        if not isinstance(replacement, dict):
            raise OSError(f"archived replacement #{index} 不是对象。")
        raw_ids = replacement.get("item_ids")
        old = replacement.get("old")
        new = replacement.get("new")
        if (
            not isinstance(raw_ids, list)
            or not raw_ids
            or any(not isinstance(value, str) or not re.fullmatch(r"#\d+", value) for value in raw_ids)
        ):
            raise OSError(f"archived replacement #{index} 的 item_ids 无效。")
        item_ids = [int(value[1:]) for value in raw_ids]
        if len(item_ids) != len(set(item_ids)):
            raise OSError(f"archived replacement #{index} 的 item_ids 不得重复。")
        if not isinstance(old, str) or not isinstance(new, str) or not old or old == new:
            raise OSError(f"archived replacement #{index} 的 old/new 无效。")
        if (
            "[REVIEW-FIX]" not in new
            or "[[REPLACE:" in new
            or "\x00" in new
            or re.search(r"(?m)^\s*(?:-|\*|\d+[.)])?\s*\.\.\.\s*$", new)
        ):
            raise OSError(f"archived replacement #{index} 缺少追踪标记或仍含模板占位。")
        for item_id in item_ids:
            if not re.search(rf"(?<!\d)#{item_id}(?!\d)", new):
                raise OSError(f"archived replacement #{index} 的 new 缺少来源审查项 #{item_id}。")
        count = candidate.count(old)
        if count != 1:
            raise OSError(f"archived replacement #{index} 的 old 必须顺序精确匹配一次，实际 {count} 次。")
        candidate = candidate.replace(old, new, 1)
        covered.update(item_ids)

    if sorted(covered) != approved_state:
        raise OSError("archived fixes.json 的 item_ids 合集与 fix-state 批准项不一致。")
    if int(values["applied_replacements"]) != len(replacements):
        raise OSError("fix-state 的 applied_replacements 与 archived fixes.json 不一致。")
    candidate_hash = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    if candidate_hash != values["candidate_plan_sha256"]:
        raise OSError("fix-state 的 candidate plan hash 不能由 archived base plan/fixes 机械重放得到。")
    return summarized_at, approved_at


def validate_post_fix_binding(
    values: dict[str, str],
    review_dir: Path,
    post_fix_run: str,
    post_fix_summary: str,
) -> datetime:
    history_dir = review_dir / "history"
    if history_dir.is_symlink() or (history_dir.exists() and not history_dir.is_dir()):
        raise OSError("verified fix-state 的 review/history 必须是真实目录或尚不存在。")
    history_target = history_dir / post_fix_run
    if history_target.exists() or history_target.is_symlink():
        if history_target.is_symlink() or not history_target.is_dir():
            raise OSError("verified fix-state 的 post-fix history target 无效。")
        manifest_path = history_target / "manifest.json"
        try:
            manifest = json.loads(read_regular(manifest_path).decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise OSError(f"verified fix-state 的 post-fix manifest 无效：{exc}") from exc
        files = manifest.get("files") if isinstance(manifest, dict) else None
        required = {"_run.md", "plan-snapshot.md", "provenance.json", "web.md", "source.md", "summary.md"}
        if (
            not isinstance(manifest, dict)
            or manifest.get("review_run_id") != post_fix_run
            or not isinstance(files, dict)
            or not set(files).issubset(ARCHIVE_FILES)
            or not required.issubset(files)
            or "fixes.json" in files
        ):
            raise OSError("verified fix-state 的 post-fix manifest 文件集合无效。")
        require_exact_manifest_entries(
            history_target, files, "verified fix-state 的 post-fix history 目录"
        )
        for name, expected in files.items():
            if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
                raise OSError(f"post-fix manifest 含非法 hash：{name}")
            if hashlib.sha256(read_regular(history_target / name)).hexdigest() != expected:
                raise OSError(f"post-fix history 文件已变化：{name}")
        if files.get("summary.md") != post_fix_summary:
            raise OSError("verified fix-state 的 post-fix summary hash 与 history manifest 不一致。")
        if files.get("plan-snapshot.md") != values["candidate_plan_sha256"]:
            raise OSError("verified fix-state 的 post-fix plan snapshot 不是 candidate plan。")
        run_data = read_regular(history_target / "_run.md")
        summary_data = read_regular(history_target / "summary.md")
    else:
        run_path = review_dir / "_run.md"
        summary_path = review_dir / "summary.md"
        snapshot_path = review_dir / "plan-snapshot.md"
        try:
            run_data = read_regular(run_path)
            summary_data = read_regular(summary_path)
            snapshot_data = read_regular(snapshot_path)
        except OSError as exc:
            raise OSError("verified fix-state 找不到当前或已归档的 post-fix PASS bundle。") from exc
        if hashlib.sha256(summary_data).hexdigest() != post_fix_summary:
            raise OSError("verified fix-state 的当前 post-fix summary hash 不一致。")
        if hashlib.sha256(snapshot_data).hexdigest() != values["candidate_plan_sha256"]:
            raise OSError("verified fix-state 的当前 post-fix snapshot 不是 candidate plan。")

    try:
        run_text = run_data.decode("utf-8")
        summary_text = summary_data.decode("utf-8")
    except UnicodeError as exc:
        raise OSError(f"verified fix-state 的 post-fix bundle 不是有效 UTF-8：{exc}") from exc
    run_expected = {
        "session_id": values["session_id"],
        "review_run_id": post_fix_run,
        "plan_sha256": values["candidate_plan_sha256"],
        "mode": "post-fix",
    }
    for name, expected in run_expected.items():
        if field(run_text, name) != expected:
            raise OSError(f"post-fix _run.md 的 {name} 与 verified fix-state 不一致。")
    summary_expected = {
        "session_id": values["session_id"],
        "review_run_id": post_fix_run,
        "plan_sha256": values["candidate_plan_sha256"],
        "fixes_sha256": "none",
        "failing_item_ids": "none",
        "unverifiable_item_ids": "none",
        "verdict": "pass",
    }
    for name, expected in summary_expected.items():
        if field(summary_text, name) != expected:
            raise OSError(f"post-fix summary.md 的 {name} 与 verified fix-state 不一致。")
    return parse_iso(field(summary_text, "summarized_at"), "post-fix summary.md summarized_at")


def load_fix_state(state_path: Path, session_dir: Path, review_dir: Path) -> tuple[str, dict[str, str]]:
    if state_path.is_symlink() or not state_path.is_file():
        raise OSError("缺少真实 fix-state.md。")
    try:
        text = read_regular(state_path).decode("utf-8")
    except UnicodeError as exc:
        raise OSError(f"fix-state.md 不是有效 UTF-8：{exc}") from exc
    names = (
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
        "status",
    )
    values = {name: field(text, name) for name in names}
    if any(value is None for value in values.values()):
        raise OSError("fix-state 缺少、重复或包含空控制字段。")
    result = {name: value for name, value in values.items() if value is not None}
    if result["session_id"] != session_dir.name:
        raise OSError("fix-state 的 session_id 与目录不一致。")
    review_match = REVIEW_ID_RE.fullmatch(result["review_run_id"])
    if not review_match or review_match.group(1) != session_dir.name:
        raise OSError("fix-state 的 review_run_id 无效。")
    for name in (
        "base_plan_sha256",
        "candidate_plan_sha256",
        "review_summary_sha256",
        "fixes_sha256",
        "review_approval_sha256",
    ):
        if not SHA256_RE.fullmatch(result[name]):
            raise OSError(f"fix-state 的 {name} 无效。")
    if result["base_plan_sha256"] == result["candidate_plan_sha256"]:
        raise OSError("fix-state 的 base/candidate plan hash 不得相同。")
    approved = parse_ids(result["approved_item_ids"])
    if approved is None or not approved or approved != sorted(approved):
        raise OSError("fix-state 的 approved_item_ids 必须是升序、唯一且非空。")
    if not re.fullmatch(r"[1-9]\d*", result["applied_replacements"]):
        raise OSError("fix-state 的 applied_replacements 必须是正整数。")

    _, approved_at = validate_archive(result, review_dir)
    backup_path = canonical_child(result["backup_path"], review_dir, "backup_path")
    if backup_path.parent != review_dir.resolve() or not backup_path.name.startswith("deployment-plan.before-inline-fix"):
        raise OSError("fix-state 的 backup_path 不是 review/ 下的标准备份文件。")
    if backup_path.is_symlink() or not backup_path.is_file():
        raise OSError("fix-state 的 backup_path 不是普通文件。")
    if hashlib.sha256(read_regular(backup_path)).hexdigest() != result["base_plan_sha256"]:
        raise OSError("fix-state 的 backup 内容与 base plan hash 不一致。")

    status = result["status"]
    prepared_at = field(text, "prepared_at")
    applied_at = field(text, "applied_at")
    verified_at = field(text, "verified_at")
    post_fix_run = field(text, "post_fix_review_run_id")
    post_fix_summary = field(text, "post_fix_summary_sha256")
    if status == "prepared":
        prepared_time = parse_iso(prepared_at, "fix-state prepared_at")
        if prepared_time < approved_at:
            raise OSError("fix-state prepared_at 不得早于 archived approval approved_at。")
        if any(value is not None for value in (applied_at, verified_at, post_fix_run, post_fix_summary)):
            raise OSError("prepared fix-state 含不属于该阶段的字段。")
    elif status == "applied-awaiting-post-fix-review":
        applied_time = parse_iso(applied_at, "fix-state applied_at")
        if applied_time < approved_at:
            raise OSError("fix-state applied_at 不得早于 archived approval approved_at。")
        if any(value is not None for value in (prepared_at, verified_at, post_fix_run, post_fix_summary)):
            raise OSError("applied fix-state 含不属于该阶段的字段。")
    elif status == "verified":
        applied_time = parse_iso(applied_at, "fix-state applied_at")
        verified_time = parse_iso(verified_at, "fix-state verified_at")
        post_match = REVIEW_ID_RE.fullmatch(post_fix_run or "")
        if (
            not post_match
            or post_match.group(1) != session_dir.name
            or post_fix_run == result["review_run_id"]
            or not SHA256_RE.fullmatch(post_fix_summary or "")
            or prepared_at is not None
        ):
            raise OSError("verified fix-state 的 post-fix 绑定无效。")
        if verified_time < applied_time:
            raise OSError("fix-state verified_at 不得早于 applied_at。")
        if applied_time < approved_at:
            raise OSError("fix-state applied_at 不得早于 archived approval approved_at。")
        post_fix_summarized_at = validate_post_fix_binding(
            result, review_dir, post_fix_run or "", post_fix_summary or ""
        )
        if post_fix_summarized_at < applied_time:
            raise OSError("post-fix summary summarized_at 不得早于 fix-state applied_at。")
        if verified_time < post_fix_summarized_at:
            raise OSError("fix-state verified_at 不得早于 post-fix summary summarized_at。")
    else:
        raise OSError("fix-state 的 status 无效。")
    return text, result
