#!/usr/bin/env python3
"""Emit a mechanically verifiable provenance block for deployment-plan.md."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ContractError(ValueError):
    pass


def field(text: str, name: str) -> str:
    matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
    if len(matches) != 1:
        raise ContractError(f"字段 {name!r} 必须且只能出现一次。")
    value = matches[0].strip()
    if not value or "<" in value or ">" in value or "..." in value:
        raise ContractError(f"字段 {name!r} 为空或仍含模板占位。")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_file(path: Path) -> Path:
    if not path.is_file() or path.is_symlink():
        raise ContractError(f"缺少真实文件或路径是 symlink：{path}")
    return path


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
        or not SESSION_RE.match(session_dir.name)
    ):
        raise ContractError("SESSION_DIR 必须是当前仓库 .workflows/ 下的时间戳目录。")
    return session_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    args = parser.parse_args()

    try:
        session_dir = resolve_session(args.session_dir)
        research_dir = session_dir / "research"
        run_path = require_file(research_dir / "_run.md")
        web_path = require_file(research_dir / "web.md")
        memory_path = require_file(research_dir / "memory.md")
        summary_path = require_file(research_dir / "summary.md")
        approval_path = require_file(research_dir / "_approval.md")

        run_text = run_path.read_text(encoding="utf-8")
        run_id = field(run_text, "run_id")
        enabled_dimensions = [part.strip() for part in field(run_text, "enabled_dimensions").split(",")]
        source_enabled = field(run_text, "source_enabled")
        if enabled_dimensions not in (["web", "memory"], ["web", "memory", "source"]):
            raise ContractError("enabled_dimensions 必须精确为 web, memory 或 web, memory, source。")
        if source_enabled not in {"true", "false"}:
            raise ContractError("source_enabled 只能是 true 或 false。")
        if (source_enabled == "true") != ("source" in enabled_dimensions):
            raise ContractError("enabled_dimensions 与 source_enabled 不一致。")

        source_path = research_dir / "source.md"
        source_hash = sha256(require_file(source_path)) if source_enabled == "true" else "none"
        run_hash = sha256(run_path)
        web_hash = sha256(web_path)
        memory_hash = sha256(memory_path)

        summary_text = summary_path.read_text(encoding="utf-8")
        expected_summary_fields = {
            "run_id": run_id,
            "research_run_sha256": run_hash,
            "web_report_sha256": web_hash,
            "memory_report_sha256": memory_hash,
            "source_report_sha256": source_hash,
        }
        for name, expected in expected_summary_fields.items():
            if field(summary_text, name) != expected:
                raise ContractError(f"summary.md 的 {name} 与当前 research bundle 不一致。")

        summary_hash = sha256(summary_path)
        approval_text = approval_path.read_text(encoding="utf-8")
        if field(approval_text, "run_id") != run_id:
            raise ContractError("_approval.md 的 run_id 与 _run.md 不一致。")
        if field(approval_text, "summary_sha256") != summary_hash:
            raise ContractError("_approval.md 的 summary_sha256 与当前 summary.md 不一致。")
        decision = field(approval_text, "decision")
        gap_ids = field(approval_text, "accepted_gap_ids")
        field(approval_text, "approved_at")
        if decision not in {"accepted", "accepted-with-key-gaps"}:
            raise ContractError("decision 只能是 accepted 或 accepted-with-key-gaps。")
        if decision == "accepted" and gap_ids != "none":
            raise ContractError("无关键缺口的 accepted 决策必须写 accepted_gap_ids: none。")
        if decision == "accepted-with-key-gaps" and gap_ids == "none":
            raise ContractError("接受关键缺口时必须列出真实 accepted_gap_ids。")
        if gap_ids != "none" and not re.fullmatch(r"#\d+(?:\s*,\s*#\d+)*", gap_ids):
            raise ContractError("accepted_gap_ids 必须是 none 或逗号分隔的 #N 列表。")

        approval_hash = sha256(approval_path)
        values = {
            "session_id": session_dir.name,
            "research_run_id": run_id,
            "research_run_sha256": run_hash,
            "web_report_sha256": web_hash,
            "memory_report_sha256": memory_hash,
            "source_report_sha256": source_hash,
            "research_summary_sha256": summary_hash,
            "research_approval_sha256": approval_hash,
        }
        if any(name.endswith("sha256") and value != "none" and not SHA256_RE.match(value) for name, value in values.items()):
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
