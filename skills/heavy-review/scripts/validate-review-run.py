#!/usr/bin/env python3
"""Validate the current heavy-review parent contract, reports, and optional summary."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from fix_state_contract import parse_json_object


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVIEW_ID_RE = re.compile(r"^(.+)-review-([0-9a-f]{16})$")
MODES = {"initial", "resume", "rerun-after-feedback", "post-fix"}
ROUTES = {"联网", "源码", "都需要"}
RISK_DIMENSIONS = {"权限", "回滚", "数据影响", "依赖", "顺序", "跨章节一致性"}
RISK_HINTS = {"HIGH-candidate", "normal"}
FRESHNESS = {"time-sensitive", "stable"}
CONCLUSIONS = {"PASS", "FAIL", "UNVERIFIABLE"}
EVIDENCE_LEVELS = {"confirmed", "unverified", "CONFLICT", "STALE", "MISSING"}
REQUIRED_PLAN_HEADINGS = (
    "目标",
    "调研摘要",
    "关键缺口处理",
    "前置检查",
    "执行步骤",
    "回滚方案",
    "风险清单",
)


class ContractError(ValueError):
    pass


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
        raise ContractError(f"路径不得是 symlink：{path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ContractError(f"无法打开普通文件 {path}：{exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ContractError(f"路径不是普通文件：{path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def read_text(path: Path) -> tuple[str, bytes]:
    data = read_regular(path)
    try:
        return data.decode("utf-8"), data
    except UnicodeError as exc:
        raise ContractError(f"文件不是有效 UTF-8：{path}: {exc}") from exc


def field(text: str, name: str) -> str:
    matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
    if len(matches) != 1:
        raise ContractError(f"字段 {name!r} 必须且只能出现一次。")
    value = matches[0].strip()
    if not value or "[[REPLACE:" in value or value in {"...", "…"}:
        raise ContractError(f"字段 {name!r} 为空或仍含模板占位。")
    return value


def parse_iso(value: str, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ContractError(f"字段 {name!r} 不是合法 ISO-8601 时间。") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(f"字段 {name!r} 必须带时区。")
    return parsed


def parse_ids(value: str, name: str, allow_none: bool = True) -> list[int]:
    if allow_none and value == "none":
        return []
    if not re.fullmatch(r"#\d+(?:\s*,\s*#\d+)*", value):
        raise ContractError(f"字段 {name!r} 必须是 none 或逗号分隔的 #N 列表。")
    result = [int(item) for item in re.findall(r"#(\d+)", value)]
    if len(result) != len(set(result)):
        raise ContractError(f"字段 {name!r} 含重复编号。")
    return result


def safe_summary(value: str) -> bool:
    return (
        1 <= len(value) <= 240
        and "\r" not in value
        and "\n" not in value
        and "[[REPLACE:" not in value
        and not re.match(r"^#{1,6}\s", value)
        and not re.match(r"^-\s+[A-Za-z_][A-Za-z0-9_-]*\s*:", value)
    )


def expected_statement_hash(locator: str, snapshot_data: bytes) -> str:
    line_match = re.fullmatch(r"lines\s+(\d+)-(\d+)", locator)
    if line_match:
        start, end = map(int, line_match.groups())
        lines = snapshot_data.splitlines(keepends=True)
        if start < 1 or end < start or end > len(lines):
            raise ContractError(f"plan_locator 超出 snapshot 行范围：{locator}")
        payload = b"".join(lines[start - 1:end])
    elif re.fullmatch(
        r"synthetic:(?:missing-section|plan-structure|provenance|source-snapshot):[^\s:][^\r\n]*",
        locator,
    ):
        payload = locator.encode("utf-8")
    else:
        raise ContractError(f"非法 plan_locator：{locator}")
    return hashlib.sha256(payload).hexdigest()


def parse_checklist(run_text: str, snapshot_data: bytes) -> dict[int, dict[str, str]]:
    match = re.search(r"(?ms)^## Review Checklist\s*\n(.*?)(?=^##\s|\Z)", run_text)
    if not match:
        raise ContractError("_run.md 缺少 ## Review Checklist。")
    blocks = list(re.finditer(r"(?ms)^### 审查项 #(\d+)\s*\n(.*?)(?=^### 审查项 #|\Z)", match.group(1)))
    if not blocks:
        raise ContractError("Review Checklist 至少需要一个审查项。")
    result: dict[int, dict[str, str]] = {}
    names = (
        "statement_summary",
        "statement_sha256",
        "plan_locator",
        "evidence_route",
        "risk_dimensions",
        "risk_hint",
        "evidence_freshness",
    )
    for block in blocks:
        item_id = int(block.group(1))
        if item_id in result:
            raise ContractError(f"Review Checklist 重复编号 #{item_id}。")
        body = block.group(2)
        values = {name: field(body, name) for name in names}
        if not safe_summary(values["statement_summary"]):
            raise ContractError(f"审查项 #{item_id} 的 statement_summary 不是安全单行。")
        if not SHA256_RE.fullmatch(values["statement_sha256"]):
            raise ContractError(f"审查项 #{item_id} 的 statement_sha256 无效。")
        if values["statement_sha256"] != expected_statement_hash(values["plan_locator"], snapshot_data):
            raise ContractError(f"审查项 #{item_id} 的 statement hash 与 plan locator 不一致。")
        if values["evidence_route"] not in ROUTES:
            raise ContractError(f"审查项 #{item_id} 的 evidence_route 无效。")
        dimensions = [part.strip() for part in values["risk_dimensions"].split(",")]
        if not dimensions or len(dimensions) != len(set(dimensions)) or any(value not in RISK_DIMENSIONS for value in dimensions):
            raise ContractError(f"审查项 #{item_id} 的 risk_dimensions 无效。")
        if values["risk_hint"] not in RISK_HINTS or values["evidence_freshness"] not in FRESHNESS:
            raise ContractError(f"审查项 #{item_id} 的 risk_hint/evidence_freshness 无效。")
        result[item_id] = values
    if sorted(result) != list(range(1, len(result) + 1)):
        raise ContractError("Review Checklist 编号必须从 #1 连续递增。")
    return result


def require_synthetic(
    checklist: dict[int, dict[str, str]],
    locator: str,
    reason: str,
) -> int:
    matches = [item_id for item_id, item in checklist.items() if item["plan_locator"] == locator]
    if len(matches) != 1:
        raise ContractError(f"{reason} 时 checklist 必须且只能包含 synthetic locator {locator!r}。")
    item = checklist[matches[0]]
    if item["evidence_route"] != "源码" or item["risk_hint"] != "HIGH-candidate":
        raise ContractError(f"synthetic item {locator!r} 必须走源码路线并标为 HIGH-candidate。")
    return matches[0]


def subsection(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^{re.escape(heading)}\s*\n(.*?)(?=^#{{1,3}}\s|\Z)", text)
    if not match:
        raise ContractError(f"缺少小节 {heading}。")
    return match.group(1).strip()


def status_lines(text: str, path: Path, item_id: int, section_name: str) -> list[str]:
    raw = re.findall(r"(?m)^[ \t]*-[ \t]+状态：([^\r\n]+?)[ \t]*$", text)
    if any(value not in CONCLUSIONS for value in raw):
        raise ContractError(f"{path.name} 审查项 #{item_id} 的 {section_name} 含非法状态值。")
    return raw


def detail_blocks(text: str, status: str) -> list[str]:
    return [
        match.group(1)
        for match in re.finditer(
            rf"(?ms)^[ \t]*-[ \t]+状态：{re.escape(status)}[ \t]*\r?\n"
            r"(.*?)(?=^[ \t]*-[ \t]+状态：(?:PASS|FAIL|UNVERIFIABLE)[ \t]*$|\Z)",
            text,
        )
    ]


def require_block_details(
    blocks: list[str],
    patterns: tuple[str, ...],
    path: Path,
    item_id: int,
    status: str,
) -> None:
    for index, block in enumerate(blocks, start=1):
        for pattern in patterns:
            if not re.search(pattern, block):
                raise ContractError(
                    f"{path.name} 审查项 #{item_id} 的第 {index} 条 {status} 明细字段不完整。"
                )


def is_none_section(text: str) -> bool:
    return text.strip() in {"无", "- 无"}


def validate_summary_body(
    text: str,
    aggregated: dict[str, list[int]],
    verdict: str,
) -> None:
    if len(re.findall(r"(?m)^# Heavy Review Summary\s*$", text)) != 1:
        raise ContractError("summary.md 必须且只能包含一个 Heavy Review Summary H1。")
    if len(re.findall(r"(?m)^## 审查报告：\S.*$", text)) != 1:
        raise ContractError("summary.md 必须且只能包含一个非空审查报告标题。")
    headings = (
        "### HIGH 严重度问题",
        "### MED 严重度问题",
        "### LOW 严重度问题",
        "### 通过项总览",
        "### 无法验证项",
        "### 修复方案汇总",
    )
    for heading in headings:
        if len(re.findall(rf"(?m)^{re.escape(heading)}\s*$", text)) != 1:
            raise ContractError(f"summary.md 必须且只能包含小节 {heading}。")
    severity_sections = [subsection(text, heading) for heading in headings[:3]]
    passing = subsection(text, headings[3])
    unverifiable = subsection(text, headings[4])
    fixes = subsection(text, headings[5])

    def classified_ids(section_text: str, label: str) -> list[int]:
        if is_none_section(section_text):
            return []
        raw_headings = re.findall(r"(?m)^-[ \t]+审查项[ \t]+#", section_text)
        matches = [
            int(value)
            for value in re.findall(r"(?m)^-[ \t]+审查项[ \t]+#(\d+)：\S.*$", section_text)
        ]
        if len(matches) != len(raw_headings) or not matches:
            raise ContractError(f"summary.md 的 {label} 必须按“- 审查项 #N：...”逐项列出或写“无”。")
        if len(matches) != len(set(matches)):
            raise ContractError(f"summary.md 的 {label} 含重复审查项编号。")
        return matches

    severity_ids: list[int] = []
    for index, section_text in enumerate(severity_sections):
        severity_ids.extend(classified_ids(section_text, headings[index]))
    if len(severity_ids) != len(set(severity_ids)) or sorted(severity_ids) != sorted(aggregated["FAIL"]):
        raise ContractError("summary.md 的 HIGH/MED/LOW 分类必须且只能各覆盖一次全部 FAIL 审查项。")
    if sorted(classified_ids(passing, "通过项总览")) != sorted(aggregated["PASS"]):
        raise ContractError("summary.md 的通过项总览必须且只能覆盖全部 PASS 审查项。")
    if sorted(classified_ids(unverifiable, "无法验证项")) != sorted(aggregated["UNVERIFIABLE"]):
        raise ContractError("summary.md 的无法验证项必须且只能覆盖全部 UNVERIFIABLE 审查项。")
    actionable = sorted(aggregated["FAIL"] + aggregated["UNVERIFIABLE"])
    if sorted(classified_ids(fixes, "修复方案汇总")) != actionable:
        raise ContractError("summary.md 的修复方案汇总必须且只能覆盖全部 FAIL/UNVERIFIABLE 审查项。")
    if not aggregated["FAIL"] and not all(is_none_section(value) for value in severity_sections):
        raise ContractError("没有 FAIL 时 HIGH/MED/LOW 三个严重度小节都必须写“无”。")
    if not aggregated["PASS"] and not is_none_section(passing):
        raise ContractError("没有 PASS 时通过项总览必须写“无”。")
    if not aggregated["UNVERIFIABLE"] and not is_none_section(unverifiable):
        raise ContractError("没有 UNVERIFIABLE 时无法验证项必须写“无”。")
    if verdict == "pass" and not is_none_section(fixes):
        raise ContractError("PASS summary 的修复方案汇总必须写“无”。")


def validate_report(
    path: Path,
    route: str,
    assigned: list[int],
    checklist: dict[int, dict[str, str]],
    metadata: dict[str, str],
    ttl_hours: int,
    source_confirmed: bool,
    run_created_at: datetime,
) -> tuple[dict[int, str], bytes, datetime]:
    text, data = read_text(path)
    if "[[REPLACE:" in text or re.search(r"(?m)^\s*(?:-|\*|\d+[.)])?\s*\.\.\.\s*$", text):
        raise ContractError(f"{path.name} 仍含模板占位。")
    if not assigned:
        if len(re.findall(r"(?m)^## 无适用审查项\s*$", text)) != 1 or re.search(r"(?m)^## 审查项 #", text):
            raise ContractError(f"{path.name} 必须是纯空路线占位报告。")
        reason = re.findall(r"(?m)^- 原因：本轮 _run\.md 的 route_items 为 none\s*$", text)
        if len(reason) != 1 or re.search(r"(?m)^\s*-?\s*状态：", text):
            raise ContractError(f"{path.name} 的空路线原因或状态残留无效。")
    else:
        if "## 无适用审查项" in text:
            raise ContractError(f"{path.name} 已分配审查项，不能使用空路线占位。")

    for name, expected in metadata.items():
        if field(text, name) != expected:
            raise ContractError(f"{path.name} 的 {name} 与 _run.md 不一致。")
    captured_at = parse_iso(field(text, "evidence_captured_at"), "evidence_captured_at")
    captured_utc = captured_at.astimezone(timezone.utc)
    created_utc = run_created_at.astimezone(timezone.utc)
    validation_now = datetime.now(timezone.utc)
    if captured_utc < created_utc:
        raise ContractError(f"{path.name} 的 evidence_captured_at 不得早于 _run.md created_at。")
    if captured_utc > validation_now:
        raise ContractError(f"{path.name} 的 evidence_captured_at 不得位于未来。")
    coverage = field(text, "本路线审查项覆盖率")
    expected_coverage = "0/0（无适用项）" if not assigned else f"{len(assigned)}/{len(assigned)}"
    if coverage != expected_coverage:
        raise ContractError(f"{path.name} 的覆盖率必须是 {expected_coverage}。")
    calls = field(text, "tool call 总次数")
    if not re.fullmatch(r"0|[1-9]\d*", calls):
        raise ContractError(f"{path.name} 的 tool call 总次数无效。")
    trace = re.search(r"(?ms)^## 审查轨迹摘要\s*\n(.*?)(?=^##\s|\Z)", text)
    if not trace:
        raise ContractError(f"{path.name} 缺少 ## 审查轨迹摘要。")
    trace_lines = [line for line in trace.group(1).splitlines() if re.match(r"^\s*-\s+\S", line)]
    expected_trace = range(1, 2) if not assigned else range(3, 6)
    if len(trace_lines) not in expected_trace:
        requirement = "1 条" if not assigned else "3-5 条"
        raise ContractError(f"{path.name} 的审查轨迹摘要必须包含 {requirement} bullet。")
    if route == "web" and any(checklist[item]["evidence_freshness"] == "time-sensitive" for item in assigned):
        age = validation_now - captured_utc
        if age.total_seconds() > ttl_hours * 3600:
            raise ContractError("web evidence 已超过 _run.md 声明的 TTL。")

    if not assigned:
        return {}, data, captured_at
    blocks = list(
        re.finditer(
            r"(?ms)^## 审查项 #(\d+)（(HIGH-candidate|normal)）：([^\r\n]+)\n(.*?)(?=^## 审查项 #|^## 元数据|\Z)",
            text,
        )
    )
    ids = [int(block.group(1)) for block in blocks]
    raw_item_headings = re.findall(r"(?m)^## 审查项 #", text)
    if len(raw_item_headings) != len(blocks):
        raise ContractError(f"{path.name} 含无法按契约解析的审查项标题。")
    if sorted(ids) != sorted(assigned) or len(ids) != len(set(ids)):
        raise ContractError(f"{path.name} 的审查项编号集合与 route_items 不一致。")
    conclusions: dict[int, str] = {}
    for block in blocks:
        item_id = int(block.group(1))
        hint = block.group(2)
        summary = block.group(3).strip()
        body = block.group(4)
        item = checklist[item_id]
        if hint != item["risk_hint"] or summary != item["statement_summary"]:
            raise ContractError(f"{path.name} 审查项 #{item_id} 的标题未绑定 checklist。")
        if field(body, "statement_sha256") != item["statement_sha256"]:
            raise ContractError(f"{path.name} 审查项 #{item_id} 的 statement_sha256 不匹配。")
        for heading in ("### 路线结论", "### 发现", "### 通过项", "### 无法验证项"):
            if len(re.findall(rf"(?m)^{re.escape(heading)}\s*$", body)) != 1:
                raise ContractError(f"{path.name} 审查项 #{item_id} 缺少唯一小节 {heading}。")
        conclusion = field(body, "route_conclusion")
        if conclusion not in CONCLUSIONS:
            raise ContractError(f"{path.name} 审查项 #{item_id} 的 route_conclusion 无效。")
        findings = subsection(body, "### 发现")
        passed = subsection(body, "### 通过项")
        unverifiable = subsection(body, "### 无法验证项")
        finding_statuses = status_lines(findings, path, item_id, "发现")
        passed_statuses = status_lines(passed, path, item_id, "通过项")
        unverifiable_statuses = status_lines(unverifiable, path, item_id, "无法验证项")
        if any(value != "FAIL" for value in finding_statuses):
            raise ContractError(f"{path.name} 审查项 #{item_id} 的发现小节只能写 FAIL。")
        if any(value != "PASS" for value in passed_statuses):
            raise ContractError(f"{path.name} 审查项 #{item_id} 的通过项小节只能写 PASS。")
        if any(value != "UNVERIFIABLE" for value in unverifiable_statuses):
            raise ContractError(f"{path.name} 审查项 #{item_id} 的无法验证项小节只能写 UNVERIFIABLE。")
        for section_name, section_text, section_statuses in (
            ("发现", findings, finding_statuses),
            ("通过项", passed, passed_statuses),
            ("无法验证项", unverifiable, unverifiable_statuses),
        ):
            if not section_statuses and not is_none_section(section_text):
                raise ContractError(f"{path.name} 审查项 #{item_id} 的{section_name}无状态时必须精确写“- 无”。")
        statuses = finding_statuses + passed_statuses + unverifiable_statuses
        expected_conclusion = "FAIL" if "FAIL" in statuses else "UNVERIFIABLE" if "UNVERIFIABLE" in statuses else "PASS"
        if conclusion != expected_conclusion or conclusion not in statuses:
            raise ContractError(f"{path.name} 审查项 #{item_id} 的结论与明细状态不一致。")
        raw_levels = re.findall(r"证据级别：([^）)\s]+)", body)
        if any(level not in EVIDENCE_LEVELS for level in raw_levels):
            raise ContractError(f"{path.name} 审查项 #{item_id} 含非法证据级别。")
        fail_blocks = detail_blocks(findings, "FAIL")
        pass_blocks = detail_blocks(passed, "PASS")
        unverifiable_blocks = detail_blocks(unverifiable, "UNVERIFIABLE")
        if len(fail_blocks) != len(finding_statuses) or len(pass_blocks) != len(passed_statuses) or len(unverifiable_blocks) != len(unverifiable_statuses):
            raise ContractError(f"{path.name} 审查项 #{item_id} 的状态明细无法逐条解析。")
        require_block_details(
            fail_blocks,
            (
                r"(?m)^[ \t]+-[ \t]+问题：[ \t]*\S.*$",
                r"(?m)^[ \t]+-[ \t]+证据：[ \t]*\S.*（证据级别：(?:confirmed|CONFLICT|MISSING)）[ \t]*$",
                r"(?m)^[ \t]+-[ \t]+建议修复：[ \t]*\S.*$",
            ),
            path,
            item_id,
            "FAIL",
        )
        require_block_details(
            pass_blocks,
            (
                r"(?m)^[ \t]+-[ \t]+检查点：[ \t]*\S.*$",
                r"(?m)^[ \t]+-[ \t]+证据：[ \t]*\S.*（证据级别：confirmed）[ \t]*$",
            ),
            path,
            item_id,
            "PASS",
        )
        require_block_details(
            unverifiable_blocks,
            (
                r"(?m)^[ \t]+-[ \t]+内容：[ \t]*\S.*$",
                r"(?m)^[ \t]+-[ \t]+原因：[ \t]*\S.*（证据级别：(?:unverified|STALE)）[ \t]*$",
                r"(?m)^[ \t]+-[ \t]+处理要求：[ \t]*\S.*$",
            ),
            path,
            item_id,
            "UNVERIFIABLE",
        )
        plan_only = item["plan_locator"].startswith("synthetic:") or set(
            part.strip() for part in item["risk_dimensions"].split(",")
        ) == {"跨章节一致性"}
        if route == "source" and not source_confirmed and conclusion == "PASS" and not plan_only:
            raise ContractError("source snapshot 不可验证时，依赖当前本地状态的源码路线审查项不能 PASS。")
        conclusions[item_id] = conclusion
    return conclusions, data, captured_at


def aggregate(checklist: dict[int, dict[str, str]], web: dict[int, str], source: dict[int, str]) -> dict[str, list[int]]:
    result = {"PASS": [], "FAIL": [], "UNVERIFIABLE": []}
    for item_id, item in checklist.items():
        values: list[str] = []
        if item["evidence_route"] in {"联网", "都需要"}:
            values.append(web[item_id])
        if item["evidence_route"] in {"源码", "都需要"}:
            values.append(source[item_id])
        conclusion = "FAIL" if "FAIL" in values else "UNVERIFIABLE" if "UNVERIFIABLE" in values else "PASS"
        result[conclusion].append(item_id)
    return result


def ids_text(values: list[int]) -> str:
    return "none" if not values else ", ".join(f"#{value}" for value in values)


def source_signature(payload: object) -> tuple[object, ...]:
    if not isinstance(payload, dict):
        return ("invalid",)
    if payload.get("status") == "confirmed":
        return (
            "confirmed",
            payload.get("repo_root"),
            payload.get("git_head"),
            payload.get("source_snapshot_sha256"),
            payload.get("file_count"),
        )
    return (payload.get("status"), payload.get("reason"))


def validate_fixes(
    path: Path,
    session_id: str,
    review_run_id: str,
    plan_sha: str,
    snapshot_data: bytes,
    actionable: list[int],
) -> tuple[str, bytes]:
    text, data = read_text(path)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ContractError("fixes.json 不是合法 JSON。") from exc
    if not isinstance(payload, dict):
        raise ContractError("fixes.json 顶层必须是对象。")
    expected = {
        "session_id": session_id,
        "review_run_id": review_run_id,
        "expected_plan_sha256": plan_sha,
    }
    for name, value in expected.items():
        if payload.get(name) != value:
            raise ContractError(f"fixes.json 的 {name} 与当前 review run 不一致。")
    replacements = payload.get("replacements")
    if not isinstance(replacements, list) or not replacements:
        raise ContractError("changes-required 时 fixes.json 必须有非空 replacements。")
    try:
        current = snapshot_data.decode("utf-8")
    except UnicodeError as exc:
        raise ContractError("plan snapshot 不是有效 UTF-8。") from exc
    covered: set[int] = set()
    for index, replacement in enumerate(replacements, start=1):
        if not isinstance(replacement, dict):
            raise ContractError(f"fixes.json replacement #{index} 不是对象。")
        raw_ids = replacement.get("item_ids")
        old = replacement.get("old")
        new = replacement.get("new")
        if (
            not isinstance(raw_ids, list)
            or not raw_ids
            or any(not isinstance(value, str) or not re.fullmatch(r"#\d+", value) for value in raw_ids)
        ):
            raise ContractError(f"fixes.json replacement #{index} 的 item_ids 无效。")
        item_ids = [int(value[1:]) for value in raw_ids]
        if len(item_ids) != len(set(item_ids)) or any(item not in actionable for item in item_ids):
            raise ContractError(f"fixes.json replacement #{index} 引用重复或不可修复的 item。")
        if not isinstance(old, str) or not isinstance(new, str) or not old or old == new:
            raise ContractError(f"fixes.json replacement #{index} 的 old/new 无效。")
        if (
            "[REVIEW-FIX]" not in new
            or "[[REPLACE:" in new
            or re.search(r"(?m)^\s*(?:-|\*|\d+[.)])?\s*\.\.\.\s*$", new)
            or "\x00" in new
        ):
            raise ContractError(f"fixes.json replacement #{index} 缺少追踪标记或仍含模板占位。")
        for item_id in item_ids:
            if not re.search(rf"(?<!\d)#{item_id}(?!\d)", new):
                raise ContractError(f"fixes.json replacement #{index} 的 new 缺少来源审查项 #{item_id}。")
        count = current.count(old)
        if count != 1:
            raise ContractError(f"fixes.json replacement #{index} 的 old 必须在候选 plan 中精确匹配一次，实际 {count} 次。")
        current = current.replace(old, new, 1)
        covered.update(item_ids)
    if sorted(covered) != sorted(actionable):
        raise ContractError("fixes.json 的 item_ids 合集必须精确覆盖全部 FAIL/UNVERIFIABLE item。")
    return hashlib.sha256(data).hexdigest(), data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    parser.add_argument("--parent-only", action="store_true")
    parser.add_argument("--require-summary", action="store_true")
    args = parser.parse_args()

    try:
        workflows_dir = Path(".workflows")
        if workflows_dir.is_symlink() or not workflows_dir.is_dir():
            raise ContractError("当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。")
        workflows_root = workflows_dir.resolve()
        requested = Path(args.session_dir).expanduser()
        if requested.is_symlink():
            raise ContractError("SESSION_DIR 不得是 symlink。")
        session_dir = requested.resolve()
        if session_dir.parent != workflows_root or not session_dir.is_dir() or not valid_session_name(session_dir.name):
            raise ContractError("SESSION_DIR 必须是当前仓库真实时间戳 session。")
        review_dir = session_dir / "review"
        if review_dir.is_symlink() or not review_dir.is_dir():
            raise ContractError("缺少真实 review/ 目录。")

        run_path = review_dir / "_run.md"
        run_text, run_data = read_text(run_path)
        session_id = field(run_text, "session_id")
        review_run_id = field(run_text, "review_run_id")
        if session_id != session_dir.name:
            raise ContractError("_run.md 的 session_id 与目录名不一致。")
        review_id_match = REVIEW_ID_RE.fullmatch(review_run_id)
        if not review_id_match or review_id_match.group(1) != session_id:
            raise ContractError("review_run_id 必须绑定 session_id 并使用 16 位随机十六进制后缀。")

        plan_path = session_dir / "deployment-plan.md"
        snapshot_path = review_dir / "plan-snapshot.md"
        if plan_path.is_symlink() or not plan_path.is_file():
            raise ContractError("deployment-plan.md 必须是当前 session 内的真实普通文件。")
        if snapshot_path.is_symlink() or not snapshot_path.is_file():
            raise ContractError("plan-snapshot.md 必须是当前 review/ 内的真实普通文件。")
        if field(run_text, "plan_path") != str(plan_path) or field(run_text, "plan_snapshot_path") != str(snapshot_path):
            raise ContractError("_run.md 的 plan_path/plan_snapshot_path 不是当前 canonical path。")
        plan_data = read_regular(plan_path)
        snapshot_data = read_regular(snapshot_path)
        try:
            snapshot_text = snapshot_data.decode("utf-8")
            plan_data.decode("utf-8")
        except UnicodeError as exc:
            raise ContractError(f"plan/snapshot 不是有效 UTF-8：{exc}") from exc
        plan_sha = field(run_text, "plan_sha256")
        if not SHA256_RE.fullmatch(plan_sha) or hashlib.sha256(plan_data).hexdigest() != plan_sha or hashlib.sha256(snapshot_data).hexdigest() != plan_sha:
            raise ContractError("live plan、plan snapshot 与 _run.md plan_sha256 不一致。")

        repo_root = Path.cwd().resolve()
        if field(run_text, "repo_root") != str(repo_root):
            raise ContractError("_run.md 的 repo_root 必须等于当前仓库根 canonical path。")
        git_head = field(run_text, "git_head")
        source_status = field(run_text, "source_snapshot_status")
        source_sha = field(run_text, "source_snapshot_sha256")
        source_reason = field(run_text, "source_snapshot_reason")
        source_captured_at = field(run_text, "source_snapshot_captured_at")
        if source_status not in {"confirmed", "unverifiable"}:
            raise ContractError("source_snapshot_status 无效。")
        source_snapshot_time: datetime | None = None
        if source_status == "confirmed":
            if not SHA256_RE.fullmatch(source_sha) or source_reason != "none":
                raise ContractError("confirmed source snapshot 必须有合法 hash 且 reason 为 none。")
            source_snapshot_time = parse_iso(source_captured_at, "source_snapshot_captured_at")
        elif source_sha != "none" or source_captured_at != "none" or source_reason == "none" or git_head != "unverifiable":
            raise ContractError("unverifiable source snapshot 必须写 hash/captured_at=none、git_head=unverifiable 和真实 reason。")

        source_script = Path(__file__).with_name("capture-source-snapshot.py")
        current_source = subprocess.run(
            [sys.executable, str(source_script)],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        current_source_data = parse_json_object(current_source.stdout, "当前 source snapshot helper 输出")
        if current_source.returncode != 0:
            raise ContractError("当前 source snapshot helper 执行失败。")
        if source_status == "confirmed":
            if (
                current_source_data.get("status") != "confirmed"
                or current_source_data.get("source_snapshot_sha256") != source_sha
                or current_source_data.get("repo_root") != str(repo_root)
                or current_source_data.get("git_head") != git_head
            ):
                raise ContractError("当前源码状态已变化，旧 review run 失效。")
        elif current_source_data.get("status") != "unverifiable" or current_source_data.get("reason") != source_reason:
            raise ContractError("当前 source snapshot 结果与 _run.md 的 unverifiable 状态不一致。")

        provenance_path = review_dir / "provenance.json"
        provenance_text, provenance_data = read_text(provenance_path)
        provenance = parse_json_object(provenance_text, "provenance.json")
        provenance_status = field(run_text, "provenance_status")
        provenance_sha = field(run_text, "provenance_result_sha256")
        if provenance_status not in {"confirmed", "missing", "mismatch", "unverifiable"}:
            raise ContractError("provenance_status 无效。")
        if not SHA256_RE.fullmatch(provenance_sha):
            raise ContractError("provenance_result_sha256 无效。")
        if provenance.get("status") != provenance_status or hashlib.sha256(provenance_data).hexdigest() != provenance_sha:
            raise ContractError("_run.md 未绑定当前 provenance.json。")
        verifier = Path(__file__).with_name("verify-plan-provenance.py")
        research_script = Path(__file__).resolve().parents[2] / "heavy-research" / "scripts" / "emit-plan-provenance.py"
        verified = subprocess.run(
            [
                sys.executable,
                str(verifier),
                str(plan_path),
                "--snapshot-path",
                str(snapshot_path),
                "--expected-plan-sha256",
                plan_sha,
                "--research-script",
                str(research_script),
            ],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        current_provenance = parse_json_object(verified.stdout, "当前 provenance verifier 输出")
        if verified.returncode != 0 or current_provenance != provenance:
            raise ContractError("provenance.json 不是当前只读 verifier 的真实输出。")

        mode = field(run_text, "mode")
        if mode not in MODES:
            raise ContractError("_run.md 的 mode 无效。")
        ttl_raw = field(run_text, "web_evidence_ttl_hours")
        if not re.fullmatch(r"[1-9]\d*", ttl_raw):
            raise ContractError("web_evidence_ttl_hours 必须是正整数。")
        ttl_hours = int(ttl_raw)
        if ttl_hours > 168:
            raise ContractError("web_evidence_ttl_hours 不得超过 168。")
        created_at = parse_iso(field(run_text, "created_at"), "created_at")
        validation_now = datetime.now(timezone.utc)
        if created_at.astimezone(timezone.utc) > validation_now:
            raise ContractError("_run.md created_at 不得位于未来。")
        if source_snapshot_time is not None and source_snapshot_time.astimezone(timezone.utc) > created_at.astimezone(timezone.utc):
            raise ContractError("source_snapshot_captured_at 不得晚于 _run.md created_at。")

        checklist = parse_checklist(run_text, snapshot_data)
        mandatory_outcomes: dict[int, str] = {}
        h1_count = len(re.findall(r"(?m)^# Deployment Plan:\s+\S.*$", snapshot_text))
        if h1_count != 1:
            locator = "synthetic:plan-structure:missing-h1" if h1_count == 0 else "synthetic:plan-structure:duplicate-h1"
            mandatory_outcomes[require_synthetic(checklist, locator, "plan H1 缺失或重复")] = "FAIL"
        for heading in REQUIRED_PLAN_HEADINGS:
            count = len(re.findall(rf"(?m)^## {re.escape(heading)}\s*$", snapshot_text))
            if count == 0:
                locator = f"synthetic:missing-section:{heading}"
                mandatory_outcomes[require_synthetic(checklist, locator, f"plan 缺少 {heading} 章节")] = "FAIL"
            elif count > 1:
                locator = f"synthetic:plan-structure:duplicate-{heading}"
                mandatory_outcomes[require_synthetic(checklist, locator, f"plan 重复 {heading} 章节")] = "FAIL"
        if provenance_status != "confirmed":
            expected_outcome = "UNVERIFIABLE" if provenance_status == "unverifiable" else "FAIL"
            locator = f"synthetic:provenance:{provenance_status}"
            mandatory_outcomes[require_synthetic(checklist, locator, "Research provenance 非 confirmed")] = expected_outcome
        if source_status == "unverifiable":
            locator = "synthetic:source-snapshot:unverifiable"
            mandatory_outcomes[require_synthetic(checklist, locator, "source snapshot unverifiable")] = "UNVERIFIABLE"
        route_matches = re.findall(
            r"(?ms)^- route_items:\s*\n\s+- web:\s*(.*?)\s*\n\s+- source:\s*(.*?)\s*$",
            run_text,
        )
        if len(route_matches) != 1:
            raise ContractError("_run.md 必须且只能包含一个 route_items web/source block。")
        web_ids = parse_ids(route_matches[0][0].strip(), "route_items.web")
        source_ids = parse_ids(route_matches[0][1].strip(), "route_items.source")
        expected_web = sorted(item for item, data in checklist.items() if data["evidence_route"] in {"联网", "都需要"})
        expected_source = sorted(item for item, data in checklist.items() if data["evidence_route"] in {"源码", "都需要"})
        if sorted(web_ids) != expected_web or sorted(source_ids) != expected_source:
            raise ContractError("route_items 与 checklist evidence_route 不一致。")
        if not web_ids and not source_ids:
            raise ContractError("web/source 路线不能同时为空。")

        if args.parent_only:
            print(
                json.dumps(
                    {
                        "status": "valid-parent",
                        "session_id": session_id,
                        "review_run_id": review_run_id,
                        "plan_sha256": plan_sha,
                        "mode": mode,
                        "route_items": {"web": web_ids, "source": source_ids},
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0

        report_metadata = {
            "session_id": session_id,
            "review_run_id": review_run_id,
            "plan_sha256": plan_sha,
            "source_snapshot_sha256": source_sha,
            "provenance_result_sha256": provenance_sha,
        }
        web_conclusions, web_data, web_captured_at = validate_report(
            review_dir / "web.md",
            "web",
            web_ids,
            checklist,
            report_metadata,
            ttl_hours,
            source_status == "confirmed",
            created_at,
        )
        source_conclusions, source_data, source_evidence_captured_at = validate_report(
            review_dir / "source.md",
            "source",
            source_ids,
            checklist,
            report_metadata,
            ttl_hours,
            source_status == "confirmed",
            created_at,
        )
        aggregated = aggregate(checklist, web_conclusions, source_conclusions)
        for item_id, expected_outcome in mandatory_outcomes.items():
            if item_id not in aggregated[expected_outcome]:
                raise ContractError(
                    f"synthetic 审查项 #{item_id} 必须聚合为 {expected_outcome}，不能被报告为其他结论。"
                )

        summary_data: bytes | None = None
        fixes_data: bytes | None = None
        summary_sha: str | None = None
        if args.require_summary:
            summary_path = review_dir / "summary.md"
            summary_text, summary_data = read_text(summary_path)
            if "[[REPLACE:" in summary_text or re.search(r"(?m)^\s*(?:-|\*|\d+[.)])?\s*\.\.\.\s*$", summary_text):
                raise ContractError("summary.md 仍含模板占位。")
            verdict = "pass" if not aggregated["FAIL"] and not aggregated["UNVERIFIABLE"] else "changes-required"
            validate_summary_body(summary_text, aggregated, verdict)
            actionable = sorted(aggregated["FAIL"] + aggregated["UNVERIFIABLE"])
            fixes_path = review_dir / "fixes.json"
            if verdict == "pass":
                if fixes_path.exists() or fixes_path.is_symlink():
                    raise ContractError("PASS review 不得残留当前根目录 fixes.json；开始新 run 前应先归档/清理旧文件。")
                fixes_sha = "none"
            else:
                fixes_sha, fixes_data = validate_fixes(
                    fixes_path,
                    session_id,
                    review_run_id,
                    plan_sha,
                    snapshot_data,
                    actionable,
                )
            expected_summary = {
                "session_id": session_id,
                "review_run_id": review_run_id,
                "plan_sha256": plan_sha,
                "source_snapshot_sha256": source_sha,
                "provenance_result_sha256": provenance_sha,
                "web_report_sha256": hashlib.sha256(web_data).hexdigest(),
                "source_report_sha256": hashlib.sha256(source_data).hexdigest(),
                "passing_item_ids": ids_text(aggregated["PASS"]),
                "failing_item_ids": ids_text(aggregated["FAIL"]),
                "unverifiable_item_ids": ids_text(aggregated["UNVERIFIABLE"]),
                "fixes_sha256": fixes_sha,
                "verdict": verdict,
            }
            for name, expected in expected_summary.items():
                if field(summary_text, name) != expected:
                    raise ContractError(f"summary.md 的 {name} 与当前 review bundle 不一致。")
            summarized_at = parse_iso(field(summary_text, "summarized_at"), "summarized_at")
            latest_evidence_at = max(web_captured_at, source_evidence_captured_at)
            if summarized_at < latest_evidence_at:
                raise ContractError("summary.md summarized_at 不得早于任一路线 evidence_captured_at。")
            if summarized_at.astimezone(timezone.utc) > datetime.now(timezone.utc):
                raise ContractError("summary.md summarized_at 不得位于未来。")
            summary_sha = hashlib.sha256(summary_data).hexdigest()

        stable_files: dict[Path, bytes] = {
            run_path: run_data,
            plan_path: plan_data,
            snapshot_path: snapshot_data,
            provenance_path: provenance_data,
            review_dir / "web.md": web_data,
            review_dir / "source.md": source_data,
        }
        if summary_data is not None:
            stable_files[review_dir / "summary.md"] = summary_data
        if fixes_data is not None:
            stable_files[review_dir / "fixes.json"] = fixes_data
        for path, expected_data in stable_files.items():
            if read_regular(path) != expected_data:
                raise ContractError(f"{path.name} 在 review 验证期间发生变化。")

        final_source = subprocess.run(
            [sys.executable, str(source_script)],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        final_source_data = parse_json_object(final_source.stdout, "最终 source snapshot 复核输出")
        if final_source.returncode != 0 or source_signature(final_source_data) != source_signature(current_source_data):
            raise ContractError("源码状态在 review 验证期间发生变化。")

        final_verified = subprocess.run(
            [
                sys.executable,
                str(verifier),
                str(plan_path),
                "--snapshot-path",
                str(snapshot_path),
                "--expected-plan-sha256",
                plan_sha,
                "--research-script",
                str(research_script),
            ],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        final_provenance = parse_json_object(final_verified.stdout, "最终 provenance 复核输出")
        if final_verified.returncode != 0 or final_provenance != provenance:
            raise ContractError("Research provenance 在 review 验证期间发生变化。")

        print(
            json.dumps(
                {
                    "status": "valid",
                    "session_id": session_id,
                    "review_run_id": review_run_id,
                    "plan_sha256": plan_sha,
                    "mode": mode,
                    "aggregate": {key.lower(): value for key, value in aggregated.items()},
                    "verdict": "pass" if not aggregated["FAIL"] and not aggregated["UNVERIFIABLE"] else "changes-required",
                    "summary_sha256": summary_sha or "none",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (ContractError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
