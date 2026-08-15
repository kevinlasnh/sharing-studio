#!/usr/bin/env python3
"""Emit a mechanically verifiable provenance block for deployment-plan.md."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_MODES = {"initial", "resume", "rerun-after-stage-c"}


class ContractError(ValueError):
    pass


def field(text: str, name: str) -> str:
    matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
    if len(matches) != 1:
        raise ContractError(f"字段 {name!r} 必须且只能出现一次。")
    value = matches[0].strip()
    if not value or "[[REPLACE:" in value or value in {"...", "…"}:
        raise ContractError(f"字段 {name!r} 为空或仍含模板占位。")
    return value


def parse_nonnegative_int(text: str, name: str) -> int:
    value = field(text, name)
    if not re.fullmatch(r"0|[1-9]\d*", value):
        raise ContractError(f"字段 {name!r} 必须是无前导零的非负整数。")
    return int(value)


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
        raise ContractError(f"无法打开真实文件 {path}：{exc}") from exc
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_session(raw_path: str) -> Path:
    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        raise ContractError("当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。")
    workflows_root = workflows_dir.resolve()
    requested = Path(raw_path).expanduser()
    if requested.is_symlink():
        raise ContractError("SESSION_DIR 不得是 symlink。")
    session_dir = requested.resolve()
    if (
        not session_dir.is_dir()
        or session_dir.parent != workflows_root
        or not valid_session_name(session_dir.name)
    ):
        raise ContractError("SESSION_DIR 必须是当前仓库 .workflows/ 下的真实时间戳目录。")
    return session_dir


def parse_json_paths(raw: str, name: str) -> list[str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContractError(f"字段 {name!r} 不是合法 JSON：{exc}") from exc
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ContractError(f"字段 {name!r} 必须是非空字符串组成的 JSON 数组。")
    if len(value) != len(set(value)):
        raise ContractError(f"字段 {name!r} 不得包含重复路径。")
    return value


def canonical_absolute(raw: str, name: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise ContractError(f"{name} 必须是 canonical absolute path：{raw}")
    resolved = path.resolve()
    if str(resolved) != raw:
        raise ContractError(f"{name} 必须使用 canonical absolute path：{raw}")
    return resolved


def parse_outline(run_text: str) -> dict[int, str]:
    outline_match = re.search(r"(?ms)^## Research Outline\s*\n(.*?)(?=^##\s|\Z)", run_text)
    if not outline_match:
        raise ContractError("_run.md 缺少 ## Research Outline。")
    leaves = re.findall(
        r"(?m)^\s*-\s+#(\d+)\s+\[(P[012])\]\s+\[leaf\]\s+(.+?)\s*$",
        outline_match.group(1),
    )
    if not 5 <= len(leaves) <= 15:
        raise ContractError("Research Outline 必须包含 5-15 个 leaf。")
    result: dict[int, str] = {}
    for raw_id, priority, statement in leaves:
        item_id = int(raw_id)
        if item_id in result or not statement.strip() or "[[REPLACE:" in statement:
            raise ContractError("Research Outline 含重复编号、空声明或模板占位。")
        result[item_id] = priority
    if sorted(result) != list(range(1, len(result) + 1)):
        raise ContractError("Research Outline 编号必须从 #1 连续递增。")
    return result


def markdown_section(text: str, heading: str) -> str | None:
    match = re.search(rf"(?ms)^{re.escape(heading)}\s*\n(.*?)(?=^###?\s|\Z)", text)
    return match.group(1).strip() if match else None


def validate_report(
    path: Path,
    session_id: str,
    run_id: str,
    outline: dict[int, str],
) -> tuple[bytes, dict[int, list[str]]]:
    text, data = read_text(path)
    if "[[REPLACE:" in text or re.search(r"(?m)^\s*(?:-|\*|\d+[.)])?\s*\.\.\.\s*$", text):
        raise ContractError(f"{path.name} 仍含模板占位。")
    if field(text, "session_id") != session_id or field(text, "run_id") != run_id:
        raise ContractError(f"{path.name} 的 session_id/run_id 与本轮不一致。")
    calls = field(text, "tool call 总次数")
    if not re.fullmatch(r"0|[1-9]\d*", calls):
        raise ContractError(f"{path.name} 的 tool call 总次数无效。")
    coverage = field(text, "树形覆盖率")
    coverage_match = re.fullmatch(r"(0|[1-9]\d*)/(0|[1-9]\d*)", coverage)
    leaf_count = len(outline)
    if not coverage_match or tuple(map(int, coverage_match.groups())) != (leaf_count, leaf_count):
        raise ContractError(f"{path.name} 的树形覆盖率必须等于 {leaf_count}/{leaf_count}。")
    blocks = list(re.finditer(r"(?ms)^## 子问题 #(\d+)（(P[012])）：[^\r\n]+\n(.*?)(?=^## 子问题 #|^## 元数据|\Z)", text))
    item_ids = [int(block.group(1)) for block in blocks]
    if sorted(item_ids) != list(range(1, leaf_count + 1)) or len(item_ids) != len(set(item_ids)):
        raise ContractError(f"{path.name} 的子问题编号集合与 outline 不一致。")
    evidence: dict[int, list[str]] = {}
    for block in blocks:
        item_id = int(block.group(1))
        if block.group(2) != outline[item_id]:
            raise ContractError(f"{path.name} 子问题 #{item_id} 的优先级与 outline 不一致。")
        body = block.group(3)
        sections = {
            heading: markdown_section(body, heading)
            for heading in ("### 结论与证据", "### 已尝试但未覆盖", "### 未执行")
        }
        if any(value is None for value in sections.values()):
            raise ContractError(f"{path.name} 子问题 #{item_id} 缺少必需小节。")
        nonempty = [value for value in sections.values() if value != "- 无"]
        if not nonempty:
            raise ContractError(f"{path.name} 子问题 #{item_id} 三个分类不能全部为空。")
        conclusion = sections["### 结论与证据"] or ""
        confidences: list[str] = []
        if conclusion != "- 无":
            confidences = re.findall(r"(?m)^\s*-?\s*置信度：(confirmed|unverified|CONFLICT)\s*$", conclusion)
            locators = re.findall(r"(?m)^\s*-?\s*来源：\S.*$", conclusion)
            if not confidences or len(confidences) != len(locators):
                raise ContractError(f"{path.name} 子问题 #{item_id} 的非空结论缺少成对 confidence/locator。")
        evidence[item_id] = confidences
    trace = re.search(r"(?ms)^## 调研轨迹摘要\s*\n(.*?)(?=^##\s|\Z)", text)
    if not trace:
        raise ContractError(f"{path.name} 缺少 ## 调研轨迹摘要。")
    trace_lines = [line for line in trace.group(1).splitlines() if re.match(r"^\s*-\s+\S", line)]
    if not 3 <= len(trace_lines) <= 5:
        raise ContractError(f"{path.name} 的调研轨迹摘要必须包含 3-5 条 bullet。")
    return data, evidence


def parse_iso_timestamp(value: str, name: str) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ContractError(f"字段 {name!r} 不是合法 ISO-8601 时间。") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(f"字段 {name!r} 必须带时区。")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    args = parser.parse_args()

    try:
        session_dir = resolve_session(args.session_dir)
        research_dir = session_dir / "research"
        if research_dir.is_symlink() or not research_dir.is_dir() or research_dir.resolve().parent != session_dir:
            raise ContractError("research/ 必须是当前 session 内的真实目录。")

        state_text, _ = read_text(research_dir / "_state.md")
        session_id = field(state_text, "session_id")
        topic_hash = field(state_text, "topic_sha256")
        state_status = field(state_text, "status")
        state_phase = field(state_text, "phase")
        parse_iso_timestamp(field(state_text, "updated_at"), "updated_at")
        if session_id != session_dir.name or not SHA256_RE.fullmatch(topic_hash):
            raise ContractError("_state.md 的 session_id/topic_sha256 无效。")
        if (state_status, state_phase) not in {
            ("in_progress", "C"),
            ("in_progress", "D"),
            ("complete", "complete"),
        }:
            raise ContractError("只有 C/D 阶段或已完成 session 可生成/验证 plan provenance。")

        run_text, run_data = read_text(research_dir / "_run.md")
        if field(run_text, "session_id") != session_id:
            raise ContractError("_run.md 的 session_id 与 session 目录不一致。")
        if field(run_text, "topic_sha256") != topic_hash:
            raise ContractError("_run.md 的 topic_sha256 与 _state.md 不一致。")
        run_id = field(run_text, "run_id")
        rerun_count = parse_nonnegative_int(run_text, "rerun_count")
        if run_id != f"{session_id}-r{rerun_count}":
            raise ContractError("_run.md 的 run_id 与 session_id/rerun_count 不一致。")
        if field(run_text, "mode") not in RUN_MODES:
            raise ContractError("_run.md 的 mode 无效。")
        field(run_text, "topic_summary")
        field(run_text, "source_reason")

        enabled_dimensions = [part.strip() for part in field(run_text, "enabled_dimensions").split(",")]
        source_enabled = field(run_text, "source_enabled")
        if enabled_dimensions not in (["web", "memory"], ["web", "memory", "source"]):
            raise ContractError("enabled_dimensions 必须精确为 web, memory 或 web, memory, source。")
        if source_enabled not in {"true", "false"}:
            raise ContractError("source_enabled 只能是 true 或 false。")
        if (source_enabled == "true") != ("source" in enabled_dimensions):
            raise ContractError("enabled_dimensions 与 source_enabled 不一致。")

        roots = parse_json_paths(field(run_text, "source_roots_json"), "source_roots_json")
        excludes = parse_json_paths(field(run_text, "source_excludes_json"), "source_excludes_json")
        if source_enabled == "false" and (roots or excludes):
            raise ContractError("未启用 source 时 roots/excludes 必须都是空数组。")
        if source_enabled == "true" and not roots:
            raise ContractError("启用 source 时至少需要一个授权 root。")
        canonical_roots = [canonical_absolute(value, "source root") for value in roots]
        for root in canonical_roots:
            if not root.is_dir():
                raise ContractError(f"授权 source root 当前不是目录：{root}")
        for raw_exclude in excludes:
            exclude = canonical_absolute(raw_exclude, "source exclude")
            if not any(exclude == root or root in exclude.parents for root in canonical_roots):
                raise ContractError(f"source exclude 不在任何授权 root 内：{exclude}")

        attempts = {
            "web": parse_nonnegative_int(run_text, "attempts_web"),
            "memory": parse_nonnegative_int(run_text, "attempts_memory"),
            "source": parse_nonnegative_int(run_text, "attempts_source"),
        }
        for dimension in ("web", "memory"):
            if attempts[dimension] not in {1, 2}:
                raise ContractError(f"启用维度 {dimension} 的 attempts 必须为 1 或 2。")
        if source_enabled == "true" and attempts["source"] not in {1, 2}:
            raise ContractError("启用 source 时 attempts_source 必须为 1 或 2。")
        if source_enabled == "false" and attempts["source"] != 0:
            raise ContractError("未启用 source 时 attempts_source 必须为 0。")

        outline = parse_outline(run_text)
        web_data, web_evidence = validate_report(research_dir / "web.md", session_id, run_id, outline)
        memory_data, memory_evidence = validate_report(research_dir / "memory.md", session_id, run_id, outline)
        if source_enabled == "true":
            source_data, source_evidence = validate_report(
                research_dir / "source.md",
                session_id,
                run_id,
                outline,
            )
        else:
            source_data, source_evidence = None, {}

        run_hash = sha256_bytes(run_data)
        web_hash = sha256_bytes(web_data)
        memory_hash = sha256_bytes(memory_data)
        source_hash = sha256_bytes(source_data) if source_data is not None else "none"

        summary_text, summary_data = read_text(research_dir / "summary.md")
        expected_summary_fields = {
            "session_id": session_id,
            "run_id": run_id,
            "topic_sha256": topic_hash,
            "research_run_sha256": run_hash,
            "web_report_sha256": web_hash,
            "memory_report_sha256": memory_hash,
            "source_report_sha256": source_hash,
        }
        for name, expected in expected_summary_fields.items():
            if field(summary_text, name) != expected:
                raise ContractError(f"summary.md 的 {name} 与当前 research bundle 不一致。")
        key_gap_ids = field(summary_text, "key_gap_ids")
        if key_gap_ids != "none" and not re.fullmatch(r"#\d+(?:\s*,\s*#\d+)*", key_gap_ids):
            raise ContractError("summary.md 的 key_gap_ids 必须是 none 或逗号分隔的 #N 列表。")
        gap_numbers = [] if key_gap_ids == "none" else [int(value) for value in re.findall(r"#(\d+)", key_gap_ids)]
        if len(gap_numbers) != len(set(gap_numbers)) or any(value not in outline for value in gap_numbers):
            raise ContractError("summary.md 的 key_gap_ids 含重复或 outline 外编号。")
        derived_gap_numbers: list[int] = []
        for item_id, priority in outline.items():
            if priority == "P2":
                continue
            all_levels = web_evidence[item_id] + memory_evidence[item_id] + source_evidence.get(item_id, [])
            current_levels = web_evidence[item_id] + source_evidence.get(item_id, [])
            if "CONFLICT" in all_levels or "confirmed" not in current_levels:
                derived_gap_numbers.append(item_id)
        if gap_numbers != derived_gap_numbers:
            expected = "none" if not derived_gap_numbers else ", ".join(f"#{value}" for value in derived_gap_numbers)
            raise ContractError(
                "summary.md 的 key_gap_ids 必须由启用报告中的 P0/P1 confidence 机械推导，"
                f"当前应为 {expected}。"
            )

        summary_hash = sha256_bytes(summary_data)
        approval_text, approval_data = read_text(research_dir / "_approval.md")
        if field(approval_text, "session_id") != session_id:
            raise ContractError("_approval.md 的 session_id 与 session 不一致。")
        if field(approval_text, "run_id") != run_id:
            raise ContractError("_approval.md 的 run_id 与 _run.md 不一致。")
        if field(approval_text, "summary_sha256") != summary_hash:
            raise ContractError("_approval.md 的 summary_sha256 与当前 summary.md 不一致。")
        decision = field(approval_text, "decision")
        accepted_gap_ids = field(approval_text, "accepted_gap_ids")
        parse_iso_timestamp(field(approval_text, "approved_at"), "approved_at")
        if key_gap_ids == "none":
            if decision != "accepted" or accepted_gap_ids != "none":
                raise ContractError("无关键缺口时 approval 必须是 accepted / none。")
        elif decision != "accepted-with-key-gaps" or accepted_gap_ids != key_gap_ids:
            raise ContractError("存在关键缺口时 approval 必须逐项接受 summary.md 的全部 key_gap_ids。")

        values = {
            "session_id": session_id,
            "topic_sha256": topic_hash,
            "research_run_id": run_id,
            "research_run_sha256": run_hash,
            "web_report_sha256": web_hash,
            "memory_report_sha256": memory_hash,
            "source_report_sha256": source_hash,
            "research_summary_sha256": summary_hash,
            "research_approval_sha256": sha256_bytes(approval_data),
        }
        if any(
            name.endswith("sha256") and value != "none" and not SHA256_RE.fullmatch(value)
            for name, value in values.items()
        ):
            raise ContractError("内部错误：生成了非法 SHA-256。")

        print("## Workflow Provenance")
        for name, value in values.items():
            print(f"- {name}: {value}")
        return 0
    except (ContractError, OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
