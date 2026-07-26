#!/usr/bin/env python3
"""Validate the final deployment-plan structure and research provenance."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
import re
import stat
import subprocess
import sys
from pathlib import Path


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
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


def valid_session_name(name: str) -> bool:
    match = SESSION_RE.fullmatch(name)
    if not match:
        return False
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d-%H%M%S")
    except ValueError:
        return False
    return True


def section(text: str, heading: str) -> str | None:
    match = re.search(
        rf"(?ms)^{re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)",
        text,
    )
    return match.group(1) if match else None


def metadata_field(text: str, name: str) -> str | None:
    matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
    return matches[0].strip() if len(matches) == 1 else None


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_path")
    args = parser.parse_args()

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        return fail(["当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。"])
    workflows_root = workflows_dir.resolve()
    plan_path = Path(os.path.abspath(Path(args.plan_path).expanduser()))
    session_dir = plan_path.parent
    if (
        plan_path.is_symlink()
        or session_dir.is_symlink()
        or not plan_path.is_file()
        or plan_path.name != "deployment-plan.md"
        or session_dir.parent != workflows_root
        or not valid_session_name(session_dir.name)
    ):
        return fail(["PLAN_PATH 必须是当前仓库真实时间戳 session 中的 deployment-plan.md。"])

    try:
        plan_data = read_regular(plan_path)
        text = plan_data.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        return fail([f"无法读取 UTF-8 plan：{exc}"])

    issues: list[str] = []
    h1_matches = re.findall(r"(?m)^# Deployment Plan:\s+\S.*$", text)
    if len(h1_matches) != 1:
        issues.append(f"非空 Deployment Plan H1 必须且只能出现一次，实际 {len(h1_matches)} 次。")

    goal_text = section(text, "## 目标")
    if goal_text is not None and not re.search(r"(?m)^成功标准：\s*\S.*$", goal_text):
        issues.append("目标章节必须包含非空的“成功标准：”行。")
    summary_section = section(text, "## 调研摘要")
    if summary_section is not None and not summary_section.strip():
        issues.append("调研摘要章节不得为空。")

    heading_positions: list[int] = []
    for heading in REQUIRED_HEADINGS:
        matches = list(re.finditer(rf"(?m)^{re.escape(heading)}\s*$", text))
        if len(matches) != 1:
            issues.append(f"标题 {heading!r} 必须且只能出现一次，实际 {len(matches)} 次。")
        else:
            heading_positions.append(matches[0].start())
    if len(heading_positions) == len(REQUIRED_HEADINGS) and heading_positions != sorted(heading_positions):
        issues.append("必需章节顺序与 deployment-plan 模板不一致。")

    if "[[REPLACE:" in text:
        issues.append("plan 仍含 [[REPLACE: ...]] 模板标记。")
    if re.search(r"(?m)^\s*(?:-|\*|\d+[.)])?\s*\.\.\.\s*$", text):
        issues.append("plan 仍含独占行省略号占位。")

    execution = section(text, "## 执行步骤")
    step_ids: list[int] = []
    if execution is None:
        issues.append("无法解析执行步骤章节。")
    else:
        step_matches = list(re.finditer(r"(?m)^### 步骤 (\d+)：\S.*$", execution))
        step_ids = [int(match.group(1)) for match in step_matches]
        if not step_ids:
            issues.append("执行步骤至少需要一个可编号步骤。")
        elif step_ids != list(range(1, len(step_ids) + 1)):
            issues.append("执行步骤编号必须从 1 连续递增且不重复。")
        for index, match in enumerate(step_matches):
            end = step_matches[index + 1].start() if index + 1 < len(step_matches) else len(execution)
            block = execution[match.start():end]
            for label in ("操作", "影响范围", "可逆性", "预期结果"):
                count = len(re.findall(rf"(?m)^- \*\*{label}\*\*：\s*\S.*$", block))
                if count != 1:
                    issues.append(f"步骤 {step_ids[index]} 的 {label} 字段必须且只能出现一次，实际 {count} 次。")
            reversibility = re.findall(r"(?m)^- \*\*可逆性\*\*：\s*(.*?)\s*$", block)
            if len(reversibility) == 1 and reversibility[0] not in ALLOWED_REVERSIBILITY:
                issues.append(f"步骤 {step_ids[index]} 含非法可逆性字段：{reversibility[0]}")

    rollback = section(text, "## 回滚方案")
    if rollback is None:
        issues.append("无法解析回滚方案章节。")
    elif step_ids:
        rollback_ids = [int(value) for value in re.findall(r"(?m)^\|\s*步骤\s+(\d+)\s*\|", rollback)]
        if rollback_ids != step_ids:
            issues.append("回滚表必须按执行步骤顺序逐项且仅出现一次。")
        irreversible_ids = [
            step_ids[index]
            for index, match in enumerate(step_matches)
            if re.search(r"(?m)^- \*\*可逆性\*\*：\s*⚠️ 不可逆\s*$", execution[match.start():(step_matches[index + 1].start() if index + 1 < len(step_matches) else len(execution))])
        ]
        remedy = re.findall(r"(?m)^不可逆步骤的回滚方案：\s*(\S.*)$", rollback)
        if len(remedy) != 1:
            issues.append("回滚方案必须且只能包含一条不可逆步骤补救说明。")
        elif irreversible_ids and remedy[0].startswith("无不可逆步骤"):
            issues.append("存在不可逆步骤时必须填写真实替代补救措施。")
        elif not irreversible_ids and remedy[0] != "无不可逆步骤。":
            issues.append("不存在不可逆步骤时补救说明必须精确写“无不可逆步骤。”。")

    risk_text = section(text, "## 风险清单")
    if risk_text is None:
        issues.append("无法解析风险清单章节。")
    else:
        rows: list[list[str]] = []
        for line in risk_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|") or not stripped.endswith("|"):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) != 4 or cells[0] == "风险" or all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                continue
            rows.append(cells)
        if not rows:
            issues.append("风险清单至少需要一条真实风险记录。")
        for cells in rows:
            if cells[1] not in {"HIGH", "MED", "LOW"}:
                issues.append(f"风险清单含非法严重度：{cells[1]}")
            if any(not cell for cell in cells):
                issues.append("风险清单不得包含空单元格。")
        risk_names = [cells[0] for cells in rows]
        if rows and not any("权限" in name for name in risk_names):
            issues.append("风险清单缺少权限风险。")
        if rows and not any(re.search(r"数据|覆盖|删除|丢失", name) for name in risk_names):
            issues.append("风险清单缺少数据影响风险。")
        if rows and not any(re.search(r"依赖|版本|兼容", name) for name in risk_names):
            issues.append("风险清单缺少依赖版本风险。")

    prechecks = section(text, "## 前置检查")
    if prechecks is not None:
        for label in ("环境", "权限", "依赖", "备份"):
            count = len(re.findall(rf"(?m)^- \[[ xX]\] {label}：\s*\S.*$", prechecks))
            if count != 1:
                issues.append(f"前置检查的 {label} 项必须且只能出现一次，实际 {count} 次。")

    research_dir = session_dir / "research"
    if research_dir.is_symlink() or not research_dir.is_dir() or research_dir.resolve().parent != session_dir:
        issues.append("research/ 必须是当前 session 内的真实目录。")
        summary_text = ""
    else:
        summary_path = research_dir / "summary.md"
        try:
            summary_text = read_regular(summary_path).decode("utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(f"无法读取真实 UTF-8 research/summary.md：{exc}")
            summary_text = ""
    key_gap_ids = metadata_field(summary_text, "key_gap_ids") if summary_text else None
    gap_text = section(text, "## 关键缺口处理")
    if key_gap_ids is None:
        issues.append("summary.md 缺少唯一 key_gap_ids 元数据。")
    elif gap_text is not None:
        referenced = sorted({int(value) for value in re.findall(r"#(\d+)", gap_text)})
        expected = [] if key_gap_ids == "none" else [int(value) for value in re.findall(r"#(\d+)", key_gap_ids)]
        if expected and referenced != expected:
            issues.append("关键缺口处理引用的编号必须与 summary.md 的 key_gap_ids 精确一致。")
        if not expected and gap_text.strip() != "无":
            issues.append("summary.md 无关键缺口时，关键缺口处理章节必须精确写“无”。")
        if expected:
            gap_blocks = list(re.finditer(r"(?ms)^- (?:子问题 )?#(\d+)：[^\r\n]+\n(.*?)(?=^- (?:子问题 )?#\d+：|\Z)", gap_text))
            block_ids = [int(match.group(1)) for match in gap_blocks]
            if block_ids != expected:
                issues.append("每个关键缺口必须按 key_gap_ids 顺序各有一个独立处理 block。")
            for match in gap_blocks:
                body = match.group(2)
                if len(re.findall(r"(?m)^\s+- 用户接受状态：已明确接受\s*$", body)) != 1:
                    issues.append(f"关键缺口 #{match.group(1)} 缺少唯一用户接受状态。")
                if len(re.findall(r"(?m)^\s+- plan 限制：\s*\S.*$", body)) != 1:
                    issues.append(f"关键缺口 #{match.group(1)} 缺少唯一非空 plan 限制。")

    emit_script = Path(__file__).with_name("emit-plan-provenance.py")
    try:
        completed = subprocess.run(
            [sys.executable, str(emit_script), str(session_dir)],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        issues.append(f"无法运行 research provenance helper：{exc}")
        completed = None
    if completed is None:
        pass
    elif completed.returncode != 0:
        issues.append(completed.stderr.strip() or "无法生成 research provenance。")
    else:
        provenance = section(text, "## Workflow Provenance")
        actual = f"## Workflow Provenance\n{provenance.rstrip()}\n" if provenance is not None else ""
        expected = completed.stdout.rstrip() + "\n"
        if actual != expected:
            issues.append("Workflow Provenance 与当前 research bundle 不一致。")

    try:
        if read_regular(plan_path) != plan_data:
            issues.append("deployment-plan.md 在验证期间发生变化。")
    except OSError as exc:
        issues.append(f"无法复核 deployment-plan.md 稳定性：{exc}")
    try:
        rechecked = subprocess.run(
            [sys.executable, str(emit_script), str(session_dir)],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        issues.append(f"无法复核运行 research provenance helper：{exc}")
        rechecked = None
    if rechecked is None:
        pass
    elif rechecked.returncode != 0:
        issues.append(rechecked.stderr.strip() or "无法复核 research provenance 稳定性。")
    elif completed is not None and completed.returncode == 0 and rechecked.stdout != completed.stdout:
        issues.append("research bundle 在 plan 验证期间发生变化。")
    try:
        if read_regular(plan_path) != plan_data:
            issues.append("deployment-plan.md 在最终 provenance 复核期间发生变化。")
    except OSError as exc:
        issues.append(f"无法完成 deployment-plan.md 最终稳定性复核：{exc}")

    return fail(issues) if issues else 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        exit_code = fail([f"文件系统操作失败：{exc}"])
    raise SystemExit(exit_code)
