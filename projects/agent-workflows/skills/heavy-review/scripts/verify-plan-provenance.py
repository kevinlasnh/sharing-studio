#!/usr/bin/env python3
"""Verify deployment-plan provenance against the current research bundle."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
EXPECTED_FIELDS = (
    "session_id",
    "research_run_id",
    "research_run_sha256",
    "web_report_sha256",
    "memory_report_sha256",
    "source_report_sha256",
    "research_summary_sha256",
    "research_approval_sha256",
)


def parse_fields(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in EXPECTED_FIELDS:
        matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
        if len(matches) == 1:
            values[name] = matches[0].strip()
    return values


def output(status: str, issues: list[str], expected: dict[str, str] | None = None) -> int:
    print(json.dumps({"status": status, "issues": issues, "expected": expected or {}}, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_path")
    parser.add_argument(
        "--research-script",
        default=str(Path("~/.agents/skills/heavy-research/scripts/emit-plan-provenance.py").expanduser()),
    )
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        return output("unverifiable", ["当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。"])
    workflows_root = workflows_dir.resolve()

    requested = Path(args.plan_path).expanduser()
    if requested.is_symlink():
        return output("unverifiable", ["PLAN_PATH 不得是 symlink。"])
    plan_path = requested.resolve()
    session_dir = plan_path.parent
    if (
        not plan_path.is_file()
        or session_dir.parent != workflows_root
        or not SESSION_RE.match(session_dir.name)
        or session_dir.is_symlink()
    ):
        return output("unverifiable", ["PLAN_PATH 必须是当前仓库时间戳 session 中的真实 deployment-plan.md。"])

    research_script = Path(args.research_script).expanduser().resolve()
    if not research_script.is_file():
        return output("unverifiable", [f"找不到 provenance 生成脚本：{research_script}"])

    try:
        plan_text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return output("unverifiable", [f"无法读取 plan：{exc}"])

    section_match = re.search(r"(?ms)^## Workflow Provenance\s*\n(.*?)(?=^##\s|\Z)", plan_text)
    if not section_match:
        return output("missing", ["deployment-plan.md 缺少 ## Workflow Provenance。"])
    actual = parse_fields(section_match.group(1))

    completed = subprocess.run(
        [sys.executable, str(research_script), str(session_dir)],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "provenance 生成失败"
        return output("mismatch", [message])
    expected = parse_fields(completed.stdout)

    issues: list[str] = []
    for name in EXPECTED_FIELDS:
        if name not in actual:
            issues.append(f"plan provenance 缺少字段 {name}。")
        elif name not in expected:
            issues.append(f"生成脚本未返回字段 {name}。")
        elif actual[name] != expected[name]:
            issues.append(f"字段 {name} 与当前 research bundle 不一致。")
    return output("confirmed" if not issues else "mismatch", issues, expected)


if __name__ == "__main__":
    raise SystemExit(main())
