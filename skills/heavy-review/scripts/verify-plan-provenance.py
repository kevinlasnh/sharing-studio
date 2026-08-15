#!/usr/bin/env python3
"""Verify snapshot-bound deployment-plan provenance against the research bundle."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys


SESSION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{6})(?:-([1-9]\d*))?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_FIELDS = (
    "session_id",
    "topic_sha256",
    "research_run_id",
    "research_run_sha256",
    "web_report_sha256",
    "memory_report_sha256",
    "source_report_sha256",
    "research_summary_sha256",
    "research_approval_sha256",
)
OUTPUT_PATH: Path | None = None


def valid_session_name(name: str) -> bool:
    match = SESSION_RE.fullmatch(name)
    if not match:
        return False
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d-%H%M%S")
    except ValueError:
        return False
    return True


def parse_fields(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in EXPECTED_FIELDS:
        matches = re.findall(rf"(?m)^-\s+{re.escape(name)}:\s*(.*?)\s*$", text)
        if len(matches) == 1:
            values[name] = matches[0].strip()
    return values


def cleanup_temp(path: Path) -> str | None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return f"无法清理临时 provenance 文件 {path}：{exc}"
    return None


def output(status: str, issues: list[str], expected: dict[str, str] | None = None) -> int:
    payload = json.dumps(
        {"status": status, "issues": issues, "expected": expected or {}},
        ensure_ascii=False,
        sort_keys=True,
    )
    if OUTPUT_PATH is not None:
        if OUTPUT_PATH.is_symlink():
            print(json.dumps({"status": "unverifiable", "issues": ["输出路径不得是 symlink。"], "expected": {}}, ensure_ascii=False, sort_keys=True))
            return 1
        temp_path = OUTPUT_PATH.with_name(
            f".{OUTPUT_PATH.name}.tmp-{os.getpid()}-{secrets.token_hex(4)}"
        )
        try:
            with temp_path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(payload + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, OUTPUT_PATH)
        except OSError as exc:
            cleanup_error = cleanup_temp(temp_path)
            detail = f"；{cleanup_error}" if cleanup_error else ""
            payload = json.dumps(
                {
                    "status": "unverifiable",
                    "issues": [f"无法持久化 provenance 结果：{exc}{detail}"],
                    "expected": {},
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            print(payload)
            return 1
        cleanup_error = cleanup_temp(temp_path)
        if cleanup_error:
            payload = json.dumps(
                {"status": "unverifiable", "issues": [cleanup_error], "expected": {}},
                ensure_ascii=False,
                sort_keys=True,
            )
            print(payload)
            return 1
    print(payload)
    return 0


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
    global OUTPUT_PATH
    OUTPUT_PATH = None
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_path")
    parser.add_argument("--snapshot-path", required=True)
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--output-path")
    parser.add_argument(
        "--research-script",
        default=str(Path("~/.agents/skills/heavy-research/scripts/emit-plan-provenance.py").expanduser()),
    )
    args = parser.parse_args()
    raw_output = Path(args.output_path).expanduser() if args.output_path else None
    if not SHA256_RE.fullmatch(args.expected_plan_sha256):
        return output("unverifiable", ["expected plan SHA-256 无效。"])

    workflows_dir = Path(".workflows")
    if workflows_dir.is_symlink() or not workflows_dir.is_dir():
        return output("unverifiable", ["当前仓库缺少真实的 .workflows/ 目录，或该路径是 symlink。"])
    workflows_root = workflows_dir.resolve()

    plan_path = Path(os.path.abspath(Path(args.plan_path).expanduser()))
    session_dir = plan_path.parent
    snapshot_path = Path(os.path.abspath(Path(args.snapshot_path).expanduser()))
    expected_snapshot = session_dir / "review" / "plan-snapshot.md"
    if (
        plan_path.is_symlink()
        or session_dir.is_symlink()
        or snapshot_path.is_symlink()
        or snapshot_path.parent.is_symlink()
        or not plan_path.is_file()
        or not snapshot_path.is_file()
        or plan_path.name != "deployment-plan.md"
        or session_dir.parent != workflows_root
        or not valid_session_name(session_dir.name)
        or snapshot_path != expected_snapshot
    ):
        return output("unverifiable", ["PLAN_PATH/snapshot 必须属于当前仓库同一合法 session。"])
    if raw_output is not None:
        expected_output = session_dir / "review" / "provenance.json"
        normalized_output = Path(os.path.abspath(raw_output))
        if raw_output.is_symlink() or normalized_output.parent.is_symlink() or normalized_output != expected_output:
            print(
                json.dumps(
                    {
                        "status": "unverifiable",
                        "issues": ["provenance 输出必须精确为当前 session 的 review/provenance.json。"],
                        "expected": {},
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 1
        OUTPUT_PATH = expected_output

    try:
        snapshot_data = read_regular(snapshot_path)
        live_data = read_regular(plan_path)
        snapshot_text = snapshot_data.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        return output("unverifiable", [f"无法读取稳定 plan snapshot：{exc}"])
    snapshot_sha = hashlib.sha256(snapshot_data).hexdigest()
    live_sha = hashlib.sha256(live_data).hexdigest()
    if snapshot_sha != args.expected_plan_sha256 or live_sha != args.expected_plan_sha256:
        return output("mismatch", ["plan snapshot、live plan 与 expected hash 未保持同一版本。"])

    section_match = re.search(r"(?ms)^## Workflow Provenance\s*\n(.*?)(?=^##\s|\Z)", snapshot_text)
    if not section_match:
        return output("missing", ["plan snapshot 缺少 ## Workflow Provenance。"])
    actual = parse_fields(section_match.group(1))

    requested_research_script = Path(args.research_script).expanduser()
    if requested_research_script.is_symlink():
        return output("unverifiable", [f"provenance 生成脚本不得是 symlink：{requested_research_script}"])
    try:
        research_script = requested_research_script.resolve()
    except OSError as exc:
        return output("unverifiable", [f"无法解析 provenance 生成脚本：{exc}"])
    if not research_script.is_file():
        return output("unverifiable", [f"找不到真实 provenance 生成脚本：{research_script}"])
    try:
        completed = subprocess.run(
            [sys.executable, str(research_script), str(session_dir)],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return output("unverifiable", [f"无法运行 provenance 生成脚本：{exc}"])
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "provenance 生成失败"
        return output("mismatch", [message])
    expected = parse_fields(completed.stdout)

    try:
        rechecked = subprocess.run(
            [sys.executable, str(research_script), str(session_dir)],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return output("unverifiable", [f"无法复核运行 provenance 生成脚本：{exc}"])
    if rechecked.returncode != 0:
        message = rechecked.stderr.strip() or rechecked.stdout.strip() or "provenance 稳定性复核失败"
        return output("mismatch", [message])
    if rechecked.stdout != completed.stdout:
        return output("mismatch", ["research bundle 在 provenance 验证期间发生变化。"])

    try:
        final_snapshot = read_regular(snapshot_path)
        final_live = read_regular(plan_path)
    except OSError as exc:
        return output("unverifiable", [f"无法复核 plan/snapshot 稳定性：{exc}"])
    if (
        hashlib.sha256(final_snapshot).hexdigest() != args.expected_plan_sha256
        or hashlib.sha256(final_live).hexdigest() != args.expected_plan_sha256
        or final_snapshot != snapshot_data
        or final_live != live_data
    ):
        return output("mismatch", ["plan snapshot 或 live plan 在 provenance 验证期间发生变化。"])

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
    try:
        exit_code = main()
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(
            json.dumps(
                {"status": "unverifiable", "issues": [f"文件系统操作失败：{exc}"], "expected": {}},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        exit_code = 1
    raise SystemExit(exit_code)
