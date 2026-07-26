#!/usr/bin/env python3
"""Validate the final deployment-plan structure and research provenance."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_HEADINGS = (
    "## Workflow Provenance",
    "## 目标",
    "## 调研摘要",
    "## 关键缺口处理",
    "## 前置检查",
    "## 执行步骤",
    "## 回滚方案",
    "## 风险清单",
)
ALLOWED_REVERSIBILITY = {"可逆", "⚠️ 不可逆"}


def fail(issues: list[str]) -> int:
    for issue in issues:
        print(f"ERROR: {issue}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_path")
    args = parser.parse_args()

    plan_path = Path(args.plan_path).expanduser()
    if plan_path.is_symlink() or not plan_path.is_file():
        return fail(["PLAN_PATH 必须是真实普通文件，不能是 symlink。"])
    try:
        text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return fail([f"无法读取 UTF-8 plan：{exc}"])

    issues: list[str] = []
    if not re.search(r"(?m)^# Deployment Plan:\s+\S", text):
        issues.append("缺少非空 Deployment Plan H1。")
    for heading in REQUIRED_HEADINGS:
        count = len(re.findall(rf"(?m)^{re.escape(heading)}\s*$", text))
        if count != 1:
            issues.append(f"标题 {heading!r} 必须且只能出现一次，实际 {count} 次。")
    if "[[REPLACE:" in text:
        issues.append("plan 仍含 [[REPLACE: ...]] 模板标记。")
    if re.search(r"(?m)^\s*(?:-|\*|\d+[.)])?\s*\.\.\.\s*$", text):
        issues.append("plan 仍含独占行省略号占位。")
    if not re.search(r"(?m)^### 步骤 \d+：\S", text):
        issues.append("执行步骤至少需要一个可编号步骤。")

    reversibility = re.findall(r"(?m)^- \*\*可逆性\*\*：\s*(.*?)\s*$", text)
    if not reversibility:
        issues.append("每个执行步骤都需要可逆性字段。")
    for value in reversibility:
        if value not in ALLOWED_REVERSIBILITY:
            issues.append(f"非法可逆性字段：{value}")
    severities = re.findall(r"(?m)^\|\s*[^|]+\|\s*(HIGH|MED|LOW|[^|]+)\s*\|", text)
    for value in severities:
        stripped = value.strip()
        if stripped in {"严重度", "--------"}:
            continue
        if stripped not in {"HIGH", "MED", "LOW"}:
            issues.append(f"风险清单含非法严重度：{stripped}")

    emit_script = Path(__file__).with_name("emit-plan-provenance.py")
    completed = subprocess.run(
        [sys.executable, str(emit_script), str(plan_path.parent)],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        issues.append(completed.stderr.strip() or "无法生成 research provenance。")
    else:
        section = re.search(r"(?ms)^## Workflow Provenance\s*\n(.*?)(?=^##\s|\Z)", text)
        actual = f"## Workflow Provenance\n{section.group(1).rstrip()}\n" if section else ""
        expected = completed.stdout.rstrip() + "\n"
        if actual != expected:
            issues.append("Workflow Provenance 与当前 research bundle 不一致。")

    return fail(issues) if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
