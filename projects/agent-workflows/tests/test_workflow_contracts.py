from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import unittest
from unittest import mock


WORKFLOWS = Path(__file__).resolve().parents[1]
RESEARCH = WORKFLOWS / "skills" / "heavy-research"
REVIEW = WORKFLOWS / "skills" / "heavy-review"
TOPIC_HASH = hashlib.sha256(b"workflow-contract-test").hexdigest()


def run_script(script: Path, *args: str, cwd: Path, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(script), *map(str, args)],
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def run_command(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def parse_env(output: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def load_script_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"无法加载脚本模块：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def init_repo(root: Path) -> None:
    commands = (
        ("git", "init", "-q"),
        ("git", "config", "user.name", "Workflow Tests"),
        ("git", "config", "user.email", "workflow-tests@example.invalid"),
    )
    for command in commands:
        completed = run_command(root, *command)
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
    write(root / ".gitignore", ".workflows/\n")
    write(root / "app.txt", "base\n")
    for command in (("git", "add", "."), ("git", "commit", "-qm", "initial")):
        completed = run_command(root, *command)
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)


def research_report(dimension: str, session_id: str, run_id: str) -> str:
    priorities = ("P0", "P0", "P1", "P1", "P2")
    blocks: list[str] = []
    for item_id, priority in enumerate(priorities, start=1):
        blocks.append(
            "\n".join(
                [
                    f"## 子问题 #{item_id}（{priority}）：测试问题 {item_id}",
                    "### 结论与证据",
                    f"- {dimension} 结论 {item_id}",
                    f"  - 来源：https://example.invalid/{dimension}/{item_id}",
                    "  - 置信度：confirmed",
                    "  - 推理：测试证据直接支撑该结论",
                    "",
                    "### 已尝试但未覆盖",
                    "- 无",
                    "",
                    "### 未执行",
                    "- 无",
                ]
            )
        )
    return "\n".join(
        [
            f"# {dimension} 调研报告 — 2026-07-26-120000",
            "",
            *blocks,
            "",
            "## 元数据",
            f"- session_id: {session_id}",
            f"- run_id: {run_id}",
            "- tool call 总次数: 5",
            "- 树形覆盖率: 5/5",
            "",
            "## 调研轨迹摘要",
            "- 按 P0 到 P2 顺序验证",
            "- 为每项保留精确 locator",
            "- 完成全部叶节点分类",
            "",
        ]
    )


def create_research_bundle(root: Path, session_name: str = "2026-07-26-120000") -> tuple[Path, Path]:
    session = root / ".workflows" / session_name
    research = session / "research"
    research.mkdir(parents=True)
    run_id = f"{session_name}-r0"
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    write(
        research / "_state.md",
        "\n".join(
            [
                "# Heavy Research Session State",
                "",
                f"- session_id: {session_name}",
                f"- topic_sha256: {TOPIC_HASH}",
                "- status: in_progress",
                "- phase: C",
                f"- updated_at: {now}",
                "",
            ]
        ),
    )
    outline = "\n".join(
        [
            "- [branch] 测试分支",
            "  - #1 [P0] [leaf] 测试问题 1",
            "  - #2 [P0] [leaf] 测试问题 2",
            "  - #3 [P1] [leaf] 测试问题 3",
            "  - #4 [P1] [leaf] 测试问题 4",
            "  - #5 [P2] [leaf] 测试问题 5",
        ]
    )
    write(
        research / "_run.md",
        "\n".join(
            [
                "# Heavy Research Run",
                "",
                f"- session_id: {session_name}",
                f"- run_id: {run_id}",
                f"- topic_sha256: {TOPIC_HASH}",
                "- topic_summary: workflow contract test",
                "- mode: initial",
                "- enabled_dimensions: web, memory",
                "- source_enabled: false",
                "- source_reason: no local source dimension needed",
                "- source_roots_json: []",
                "- source_excludes_json: []",
                "- rerun_count: 0",
                "- attempts_web: 1",
                "- attempts_memory: 1",
                "- attempts_source: 0",
                "",
                "## Research Outline",
                outline,
                "",
            ]
        ),
    )
    write(research / "web.md", research_report("联网", session_name, run_id))
    write(research / "memory.md", research_report("记忆", session_name, run_id))
    run_sha = hashlib.sha256((research / "_run.md").read_bytes()).hexdigest()
    web_sha = hashlib.sha256((research / "web.md").read_bytes()).hexdigest()
    memory_sha = hashlib.sha256((research / "memory.md").read_bytes()).hexdigest()
    write(
        research / "summary.md",
        "\n".join(
            [
                "## 调研摘要：workflow contract test",
                "",
                "### 覆盖结果",
                "- 五个叶节点均有 confirmed 证据",
                "",
                "## 元数据",
                f"- session_id: {session_name}",
                f"- run_id: {run_id}",
                f"- topic_sha256: {TOPIC_HASH}",
                f"- research_run_sha256: {run_sha}",
                f"- web_report_sha256: {web_sha}",
                f"- memory_report_sha256: {memory_sha}",
                "- source_report_sha256: none",
                "- key_gap_ids: none",
                "",
            ]
        ),
    )
    summary_sha = hashlib.sha256((research / "summary.md").read_bytes()).hexdigest()
    write(
        research / "_approval.md",
        "\n".join(
            [
                "# Heavy Research Approval",
                "",
                f"- session_id: {session_name}",
                f"- run_id: {run_id}",
                f"- summary_sha256: {summary_sha}",
                "- decision: accepted",
                "- accepted_gap_ids: none",
                f"- approved_at: {now}",
                "",
            ]
        ),
    )
    emit = run_script(RESEARCH / "scripts" / "emit-plan-provenance.py", str(session), cwd=root)
    if emit.returncode != 0:
        raise AssertionError(emit.stderr)
    plan = session / "deployment-plan.md"
    write(
        plan,
        "\n".join(
            [
                "# Deployment Plan: workflow contract test — 2026-07-26-120000",
                "",
                emit.stdout.rstrip(),
                "",
                "## 目标",
                "验证 workflow contracts。",
                "成功标准：所有验证器通过。",
                "",
                "## 调研摘要",
                "五个叶节点均有 confirmed 证据。",
                "",
                "## 关键缺口处理",
                "无",
                "",
                "## 前置检查",
                "- [ ] 环境：Python 3",
                "- [ ] 权限：普通用户",
                "- [ ] 依赖：Git",
                "- [ ] 备份：Git commit",
                "",
                "## 执行步骤",
                "### 步骤 1：更新 app.txt",
                "- **操作**：将 app.txt 更新为 reviewed",
                "- **影响范围**：app.txt",
                "- **可逆性**：可逆",
                "- **预期结果**：文件内容为 reviewed",
                "",
                "## 回滚方案",
                "| 步骤 | 回滚操作 | 回滚条件 |",
                "|------|----------|----------|",
                "| 步骤 1 | 恢复 Git 中的 app.txt | 内容不符合预期 |",
                "",
                "不可逆步骤的回滚方案：无不可逆步骤。",
                "",
                "## 风险清单",
                "| 风险 | 严重度 | 触发条件 | 缓解措施 |",
                "|------|--------|----------|----------|",
                "| 权限不足 | LOW | 文件不可写 | 前置检查权限 |",
                "| 数据覆盖 | MED | 未备份直接编辑 | 先保留 Git commit |",
                "| 依赖版本不符 | MED | Python/Git 不可用 | 检查版本 |",
                "",
            ]
        ),
    )
    validator = run_script(RESEARCH / "scripts" / "validate-deployment-plan.py", str(plan), cwd=root)
    if validator.returncode != 0:
        raise AssertionError(validator.stderr)
    for phase in ("D", "complete"):
        updated = run_script(
            RESEARCH / "scripts" / "update-session-state.py",
            str(session),
            "--phase",
            phase,
            cwd=root,
        )
        if updated.returncode != 0:
            raise AssertionError(updated.stderr)
    return session, plan


def empty_review_report(
    route: str,
    session_id: str,
    review_run_id: str,
    plan_sha: str,
    source_sha: str,
    provenance_sha: str,
) -> str:
    return "\n".join(
        [
            f"# {route}审查报告 — 2026-07-26-120000",
            "",
            "## 无适用审查项",
            "- 原因：本轮 _run.md 的 route_items 为 none",
            "",
            "## 元数据",
            f"- session_id: {session_id}",
            f"- review_run_id: {review_run_id}",
            f"- plan_sha256: {plan_sha}",
            f"- source_snapshot_sha256: {source_sha}",
            f"- provenance_result_sha256: {provenance_sha}",
            f"- evidence_captured_at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            "- tool call 总次数: 0",
            "- 本路线审查项覆盖率: 0/0（无适用项）",
            "",
            "## 审查轨迹摘要",
            "- 本路线无适用项，未执行取证",
            "",
        ]
    )


def source_review_report(
    conclusion: str,
    evidence_level: str,
    session_id: str,
    review_run_id: str,
    plan_sha: str,
    source_sha: str,
    provenance_sha: str,
    statement_sha: str,
) -> str:
    if conclusion == "PASS":
        findings = ["### 发现", "- 无"]
        passed = [
            "### 通过项",
            "- 状态：PASS",
            "  - 检查点：app.txt 操作可被当前仓库验证",
            f"  - 证据：app.txt（证据级别：{evidence_level}）",
        ]
        unverifiable = ["### 无法验证项", "- 无"]
    elif conclusion == "FAIL":
        findings = [
            "### 发现",
            "- 状态：FAIL",
            "  - 问题：原步骤缺少审查标记",
            f"  - 证据：deployment-plan.md（证据级别：{evidence_level}）",
            "  - 建议修复：在操作字段加入 [REVIEW-FIX] 标记",
        ]
        passed = ["### 通过项", "- 无"]
        unverifiable = ["### 无法验证项", "- 无"]
    else:
        findings = ["### 发现", "- 无"]
        passed = ["### 通过项", "- 无"]
        unverifiable = [
            "### 无法验证项",
            "- 状态：UNVERIFIABLE",
            "  - 内容：当前源码证据不足",
            f"  - 原因：缺少直接读取证据（证据级别：{evidence_level}）",
            "  - 处理要求：执行前补充本地验证",
        ]
    return "\n".join(
        [
            "# 源码审查报告 — 2026-07-26-120000",
            "",
            "## 审查项 #1（normal）：验证 app.txt 更新操作",
            f"- statement_sha256: {statement_sha}",
            "",
            "### 路线结论",
            f"- route_conclusion: {conclusion}",
            "",
            *findings,
            "",
            *passed,
            "",
            *unverifiable,
            "",
            "## 元数据",
            f"- session_id: {session_id}",
            f"- review_run_id: {review_run_id}",
            f"- plan_sha256: {plan_sha}",
            f"- source_snapshot_sha256: {source_sha}",
            f"- provenance_result_sha256: {provenance_sha}",
            f"- evidence_captured_at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            "- tool call 总次数: 2",
            "- 本路线审查项覆盖率: 1/1",
            "",
            "## 审查轨迹摘要",
            "- 定位 plan 操作字段",
            "- 核对当前仓库 source snapshot",
            "- 形成路线结论与修复建议",
            "",
        ]
    )


def build_review_bundle(root: Path, session: Path, plan: Path, mode: str, conclusion: str, evidence_level: str) -> dict[str, str]:
    ensure = run_script(REVIEW / "scripts" / "ensure-review-dir.py", str(session), cwd=root)
    if ensure.returncode != 0:
        raise AssertionError(ensure.stderr)
    prepared = run_script(REVIEW / "scripts" / "prepare-review-run.py", str(session), "--mode", mode, cwd=root)
    if prepared.returncode != 0:
        raise AssertionError(prepared.stderr)
    review_run_id = parse_env(prepared.stdout)["REVIEW_RUN_ID"]
    captured = run_script(REVIEW / "scripts" / "capture-plan.py", str(plan), cwd=root)
    if captured.returncode != 0:
        raise AssertionError(captured.stderr)
    captured_env = parse_env(captured.stdout)
    plan_sha = captured_env["PLAN_SHA256"]
    snapshot = Path(captured_env["PLAN_SNAPSHOT_PATH"])
    provenance_path = session / "review" / "provenance.json"
    provenance = run_script(
        REVIEW / "scripts" / "verify-plan-provenance.py",
        str(plan),
        "--snapshot-path",
        str(snapshot),
        "--expected-plan-sha256",
        plan_sha,
        "--output-path",
        str(provenance_path),
        "--research-script",
        str(RESEARCH / "scripts" / "emit-plan-provenance.py"),
        cwd=root,
    )
    if provenance.returncode != 0 or json.loads(provenance.stdout)["status"] != "confirmed":
        raise AssertionError(provenance.stdout + provenance.stderr)
    provenance_sha = hashlib.sha256(provenance_path.read_bytes()).hexdigest()
    source = run_script(REVIEW / "scripts" / "capture-source-snapshot.py", cwd=root)
    if source.returncode != 0:
        raise AssertionError(source.stderr)
    source_info = json.loads(source.stdout)
    if source_info["status"] != "confirmed":
        raise AssertionError(source.stdout)
    source_sha = source_info["source_snapshot_sha256"]

    lines = snapshot.read_bytes().splitlines(keepends=True)
    line_number = next(index for index, line in enumerate(lines, start=1) if b"**\xe6\x93\x8d\xe4\xbd\x9c**" in line)
    locator = f"lines {line_number}-{line_number}"
    statement_sha = hashlib.sha256(lines[line_number - 1]).hexdigest()
    run_text = "\n".join(
        [
            "# Heavy Review Run",
            "",
            f"- session_id: {session.name}",
            f"- review_run_id: {review_run_id}",
            f"- plan_path: {plan.resolve()}",
            f"- plan_snapshot_path: {snapshot.resolve()}",
            f"- plan_sha256: {plan_sha}",
            f"- repo_root: {root.resolve()}",
            f"- git_head: {source_info['git_head']}",
            "- source_snapshot_status: confirmed",
            f"- source_snapshot_sha256: {source_sha}",
            "- source_snapshot_reason: none",
            f"- source_snapshot_captured_at: {source_info['captured_at']}",
            "- provenance_status: confirmed",
            f"- provenance_result_sha256: {provenance_sha}",
            f"- mode: {mode}",
            "- web_evidence_ttl_hours: 24",
            f"- created_at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            "- route_items:",
            "  - web: none",
            "  - source: #1",
            "",
            "## Review Checklist",
            "### 审查项 #1",
            "- statement_summary: 验证 app.txt 更新操作",
            f"- statement_sha256: {statement_sha}",
            f"- plan_locator: {locator}",
            "- evidence_route: 源码",
            "- risk_dimensions: 数据影响, 回滚",
            "- risk_hint: normal",
            "- evidence_freshness: stable",
            "",
        ]
    )
    review_dir = session / "review"
    write(review_dir / "_run.md", run_text)
    parent = run_script(REVIEW / "scripts" / "validate-review-run.py", str(session), "--parent-only", cwd=root)
    if parent.returncode != 0:
        raise AssertionError(parent.stdout + parent.stderr)
    write(review_dir / "web.md", empty_review_report("联网", session.name, review_run_id, plan_sha, source_sha, provenance_sha))
    write(
        review_dir / "source.md",
        source_review_report(
            conclusion,
            evidence_level,
            session.name,
            review_run_id,
            plan_sha,
            source_sha,
            provenance_sha,
            statement_sha,
        ),
    )
    reports = run_script(REVIEW / "scripts" / "validate-review-run.py", str(session), cwd=root)
    if reports.returncode != 0 and not (conclusion == "PASS" and evidence_level == "unverified"):
        raise AssertionError(reports.stdout + reports.stderr)

    old = "- **操作**：将 app.txt 更新为 reviewed"
    new = "- **操作**：将 app.txt 更新为 reviewed\n\n> [REVIEW-FIX] 来源：审查项 #1；执行前确认操作字段已审查。"
    if conclusion == "FAIL":
        fixes = {
            "session_id": session.name,
            "review_run_id": review_run_id,
            "expected_plan_sha256": plan_sha,
            "replacements": [{"item_ids": ["#1"], "old": old, "new": new}],
        }
        write(review_dir / "fixes.json", json.dumps(fixes, ensure_ascii=False, sort_keys=True) + "\n")
        fixes_sha = hashlib.sha256((review_dir / "fixes.json").read_bytes()).hexdigest()
        passing, failing, unverifiable, verdict = "none", "#1", "none", "changes-required"
    elif conclusion == "UNVERIFIABLE":
        fixes = {
            "session_id": session.name,
            "review_run_id": review_run_id,
            "expected_plan_sha256": plan_sha,
            "replacements": [{"item_ids": ["#1"], "old": old, "new": new}],
        }
        write(review_dir / "fixes.json", json.dumps(fixes, ensure_ascii=False, sort_keys=True) + "\n")
        fixes_sha = hashlib.sha256((review_dir / "fixes.json").read_bytes()).hexdigest()
        passing, failing, unverifiable, verdict = "none", "none", "#1", "changes-required"
    else:
        fixes_sha = "none"
        passing, failing, unverifiable, verdict = "#1", "none", "none", "pass"
    if conclusion == "FAIL":
        high_body, med_body, low_body = "无", "- 审查项 #1：操作字段需要修复", "无"
        passing_body, unverifiable_body = "无", "无"
        fixes_body = "- 审查项 #1：在操作字段加入追踪标记"
    elif conclusion == "UNVERIFIABLE":
        high_body = med_body = low_body = "无"
        passing_body = "无"
        unverifiable_body = "- 审查项 #1：当前源码证据不足"
        fixes_body = "- 审查项 #1：增加执行前本地验证闸门"
    else:
        high_body = med_body = low_body = "无"
        passing_body = "- 审查项 #1：全部相关路线 PASS"
        unverifiable_body = "无"
        fixes_body = "无"
    summary = "\n".join(
        [
            "# Heavy Review Summary",
            "",
            "## 审查报告：workflow contract test",
            "",
            "### HIGH 严重度问题",
            high_body,
            "",
            "### MED 严重度问题",
            med_body,
            "",
            "### LOW 严重度问题",
            low_body,
            "",
            "### 通过项总览",
            passing_body,
            "",
            "### 无法验证项",
            unverifiable_body,
            "",
            "### 修复方案汇总",
            fixes_body,
            "",
            "## 元数据",
            f"- session_id: {session.name}",
            f"- review_run_id: {review_run_id}",
            f"- plan_sha256: {plan_sha}",
            f"- source_snapshot_sha256: {source_sha}",
            f"- provenance_result_sha256: {provenance_sha}",
            f"- web_report_sha256: {hashlib.sha256((review_dir / 'web.md').read_bytes()).hexdigest()}",
            f"- source_report_sha256: {hashlib.sha256((review_dir / 'source.md').read_bytes()).hexdigest()}",
            f"- fixes_sha256: {fixes_sha}",
            f"- passing_item_ids: {passing}",
            f"- failing_item_ids: {failing}",
            f"- unverifiable_item_ids: {unverifiable}",
            f"- verdict: {verdict}",
            f"- summarized_at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            "",
        ]
    )
    write(review_dir / "summary.md", summary)
    return {
        "review_run_id": review_run_id,
        "plan_sha": plan_sha,
        "source_sha": source_sha,
        "provenance_sha": provenance_sha,
        "summary_sha": hashlib.sha256((review_dir / "summary.md").read_bytes()).hexdigest(),
    }


class WorkflowContractTests(unittest.TestCase):
    def test_discovery_double_scan_retries_until_stable(self) -> None:
        review_module = load_script_module(
            REVIEW / "scripts" / "find-latest-plan.py", "workflow_find_latest_plan"
        )
        research_module = load_script_module(
            RESEARCH / "scripts" / "find-latest-session.py", "workflow_find_latest_session"
        )
        older = Path("/tmp/2026-07-26-120000")
        newer = Path("/tmp/2026-07-26-120001")

        review_answers = iter(
            [(older, "complete"), (newer, "complete"), (newer, "complete"), (newer, "complete")]
        )
        review_stable, review_candidate = review_module.stable_latest_candidate(
            Path("."), Path("."), scanner=lambda *_: next(review_answers)
        )
        self.assertTrue(review_stable)
        self.assertEqual(review_candidate, (newer, "complete"))

        research_answers = iter([older, newer, newer, newer])
        research_stable, research_candidate = research_module.stable_latest_candidate(
            Path("."), Path("."), TOPIC_HASH, scanner=lambda *_: next(research_answers)
        )
        self.assertTrue(research_stable)
        self.assertEqual(research_candidate, newer)

        counter = 0

        def oscillating(*_):
            nonlocal counter
            counter += 1
            return older if counter % 2 else newer

        unstable, candidate = research_module.stable_latest_candidate(
            Path("."), Path("."), TOPIC_HASH, scanner=oscillating
        )
        self.assertFalse(unstable)
        self.assertIsNone(candidate)

    def test_review_legacy_requires_pre_provenance_plan(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            modern = root / ".workflows" / "2026-07-26-120001"
            legacy = root / ".workflows" / "2026-07-26-120000"
            write(
                modern / "deployment-plan.md",
                "# Deployment Plan: damaged modern\n\n## Workflow Provenance\n- session_id: missing-state\n",
            )
            write(legacy / "deployment-plan.md", "# Legacy Deployment Plan\n\n旧格式无 provenance。\n")

            rejected = run_script(REVIEW / "scripts" / "ensure-review-dir.py", str(modern), cwd=root)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("complete 或可识别的 legacy", rejected.stderr)
            accepted = run_script(REVIEW / "scripts" / "ensure-review-dir.py", str(legacy), cwd=root)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

            broken_research = root / ".workflows" / "2026-07-26-120002"
            write(broken_research / "deployment-plan.md", "# Damaged legacy-like plan\n\n无 provenance。\n")
            (broken_research / "research").symlink_to(root / "missing-research", target_is_directory=True)
            rejected_broken_research = run_script(
                REVIEW / "scripts" / "ensure-review-dir.py", str(broken_research), cwd=root
            )
            self.assertNotEqual(rejected_broken_research.returncode, 0)

            broken_state = root / ".workflows" / "2026-07-26-120003"
            write(broken_state / "deployment-plan.md", "# Damaged legacy-like plan\n\n无 provenance。\n")
            (broken_state / "research").mkdir()
            (broken_state / "research" / "_state.md").symlink_to(root / "missing-state.md")
            rejected_broken_state = run_script(REVIEW / "scripts" / "ensure-review-dir.py", str(broken_state), cwd=root)
            self.assertNotEqual(rejected_broken_state.returncode, 0)

            latest = run_script(REVIEW / "scripts" / "find-latest-plan.py", cwd=root)
            self.assertEqual(latest.returncode, 0, latest.stderr)
            self.assertEqual(parse_env(latest.stdout)["SESSION_DIR"], str(legacy.resolve()))
            self.assertEqual(parse_env(latest.stdout)["SESSION_STATE"], "legacy")

    def test_timestamp_symlink_and_session_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            workflows = root / ".workflows"
            fake = workflows / "2026-02-30-120000"
            write(fake / "deployment-plan.md", "invalid date\n")
            latest = run_script(REVIEW / "scripts" / "find-latest-plan.py", cwd=root)
            self.assertNotEqual(latest.returncode, 0)

            blocked_pointer = workflows / ".active-session"
            blocked_pointer.mkdir()
            failed_create = run_script(
                RESEARCH / "scripts" / "new-session-dir.py",
                "--topic-hash",
                TOPIC_HASH,
                cwd=root,
            )
            self.assertNotEqual(failed_create.returncode, 0)
            self.assertIn("已回滚新 session", failed_create.stderr)
            self.assertEqual(set(workflows.iterdir()), {fake, blocked_pointer})
            blocked_pointer.rmdir()

            created = run_script(
                RESEARCH / "scripts" / "new-session-dir.py",
                "--topic-hash",
                TOPIC_HASH,
                cwd=root,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            session = Path(parse_env(created.stdout)["SESSION_DIR"])
            skipped = run_script(
                RESEARCH / "scripts" / "update-session-state.py",
                str(session),
                "--phase",
                "B2",
                cwd=root,
            )
            self.assertNotEqual(skipped.returncode, 0)
            for phase in ("B1", "B2", "B3", "B4", "C", "D", "complete"):
                updated = run_script(
                    RESEARCH / "scripts" / "update-session-state.py",
                    str(session),
                    "--phase",
                    phase,
                    cwd=root,
                )
                self.assertEqual(updated.returncode, 0, updated.stderr)
            self.assertFalse((workflows / ".active-session").exists())

            outside = root / "outside-pointer"
            write(outside, f"{session}\n")
            (workflows / ".active-session").symlink_to(outside)
            second = run_script(
                RESEARCH / "scripts" / "new-session-dir.py",
                "--topic-hash",
                TOPIC_HASH,
                cwd=root,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            found = run_script(
                RESEARCH / "scripts" / "find-latest-session.py",
                "--topic-hash",
                TOPIC_HASH,
                cwd=root,
            )
            self.assertEqual(found.returncode, 0, found.stderr)
            self.assertFalse((workflows / ".active-session").is_symlink())

            active_path = workflows / ".active-session"
            latest_session = Path(parse_env(found.stdout)["SESSION_DIR"])
            noncanonical = f"{latest_session.parent}/unused/../{latest_session.name}"
            active_path.write_text(noncanonical + "\n", encoding="utf-8", newline="\n")
            canonicalized = run_script(
                RESEARCH / "scripts" / "find-latest-session.py",
                "--topic-hash",
                TOPIC_HASH,
                cwd=root,
            )
            self.assertEqual(canonicalized.returncode, 0, canonicalized.stderr)
            self.assertEqual(active_path.read_text(encoding="utf-8").strip(), str(latest_session.resolve()))

    def test_concurrent_session_creation_uses_unique_directories(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            def create(_: int) -> subprocess.CompletedProcess[str]:
                return run_script(
                    RESEARCH / "scripts" / "new-session-dir.py",
                    "--topic-hash",
                    TOPIC_HASH,
                    cwd=root,
                )

            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(create, range(4)))
            self.assertTrue(all(result.returncode == 0 for result in results), [result.stderr for result in results])
            sessions = {parse_env(result.stdout)["SESSION_DIR"] for result in results}
            self.assertEqual(len(sessions), 4)
            active = (root / ".workflows" / ".active-session").read_text(encoding="utf-8").strip()
            self.assertIn(active, sessions)

    def test_research_provenance_round_trip_and_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            emitted = run_script(RESEARCH / "scripts" / "emit-plan-provenance.py", str(session), cwd=root)
            self.assertEqual(emitted.returncode, 0, emitted.stderr)
            self.assertIn(f"- topic_sha256: {TOPIC_HASH}", emitted.stdout)
            validated = run_script(RESEARCH / "scripts" / "validate-deployment-plan.py", str(plan), cwd=root)
            self.assertEqual(validated.returncode, 0, validated.stderr)
            with (session / "research" / "web.md").open("a", encoding="utf-8") as handle:
                handle.write("tamper\n")
            tampered = run_script(RESEARCH / "scripts" / "emit-plan-provenance.py", str(session), cwd=root)
            self.assertNotEqual(tampered.returncode, 0)

    def test_research_rejects_invalid_state_and_parent_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            created = run_script(
                RESEARCH / "scripts" / "new-session-dir.py",
                "--topic-hash",
                TOPIC_HASH,
                cwd=root,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            session = Path(parse_env(created.stdout)["SESSION_DIR"])
            state_path = session / "research" / "_state.md"
            original_state = state_path.read_text(encoding="utf-8")
            state_path.write_text(original_state.replace("- phase: B0", "- phase: nonsense"), encoding="utf-8", newline="\n")
            invalid = run_script(
                RESEARCH / "scripts" / "find-latest-session.py",
                "--topic-hash",
                TOPIC_HASH,
                cwd=root,
            )
            self.assertNotEqual(invalid.returncode, 0)

            state_path.write_text(original_state, encoding="utf-8", newline="\n")
            research_dir = session / "research"
            outside = root / "outside-research"
            research_dir.rename(outside)
            research_dir.symlink_to(outside, target_is_directory=True)
            escaped = run_script(
                RESEARCH / "scripts" / "update-session-state.py",
                str(session),
                "--phase",
                "B1",
                cwd=root,
            )
            self.assertNotEqual(escaped.returncode, 0)
            self.assertIn("research/ 必须", escaped.stderr)

    def test_deployment_plan_rejects_duplicate_rollback_and_false_irreversible_remedy(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            _, plan = create_research_bundle(root)
            original = plan.read_text(encoding="utf-8")
            duplicate = original.replace(
                "| 步骤 1 | 恢复 Git 中的 app.txt | 内容不符合预期 |",
                "| 步骤 1 | 恢复 Git 中的 app.txt | 内容不符合预期 |\n| 步骤 1 | 再次恢复 app.txt | 重试 |",
            )
            plan.write_text(duplicate, encoding="utf-8", newline="\n")
            duplicate_result = run_script(RESEARCH / "scripts" / "validate-deployment-plan.py", str(plan), cwd=root)
            self.assertNotEqual(duplicate_result.returncode, 0)
            self.assertIn("逐项且仅出现一次", duplicate_result.stderr)

            irreversible = original.replace("- **可逆性**：可逆", "- **可逆性**：⚠️ 不可逆")
            plan.write_text(irreversible, encoding="utf-8", newline="\n")
            irreversible_result = run_script(RESEARCH / "scripts" / "validate-deployment-plan.py", str(plan), cwd=root)
            self.assertNotEqual(irreversible_result.returncode, 0)
            self.assertIn("真实替代补救措施", irreversible_result.stderr)

    def test_research_key_gaps_are_derived_from_dimension_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, _ = create_research_bundle(root)
            research = session / "research"
            web_path = research / "web.md"
            web_text = web_path.read_text(encoding="utf-8")
            web_path.write_text(web_text.replace("置信度：confirmed", "置信度：unverified", 1), encoding="utf-8", newline="\n")

            summary_path = research / "summary.md"
            summary_text = summary_path.read_text(encoding="utf-8")
            summary_text = re.sub(
                r"(?m)^- web_report_sha256: [0-9a-f]{64}$",
                f"- web_report_sha256: {hashlib.sha256(web_path.read_bytes()).hexdigest()}",
                summary_text,
            )
            summary_path.write_text(summary_text, encoding="utf-8", newline="\n")
            approval_path = research / "_approval.md"
            approval_text = approval_path.read_text(encoding="utf-8")
            approval_text = re.sub(
                r"(?m)^- summary_sha256: [0-9a-f]{64}$",
                f"- summary_sha256: {hashlib.sha256(summary_path.read_bytes()).hexdigest()}",
                approval_text,
            )
            approval_path.write_text(approval_text, encoding="utf-8", newline="\n")

            emitted = run_script(RESEARCH / "scripts" / "emit-plan-provenance.py", str(session), cwd=root)
            self.assertNotEqual(emitted.returncode, 0)
            self.assertIn("当前应为 #1", emitted.stderr)

    def test_plan_and_source_snapshots_detect_changes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            ensured = run_script(REVIEW / "scripts" / "ensure-review-dir.py", str(session), cwd=root)
            self.assertEqual(ensured.returncode, 0, ensured.stderr)
            captured = run_script(REVIEW / "scripts" / "capture-plan.py", str(plan), cwd=root)
            self.assertEqual(captured.returncode, 0, captured.stderr)
            values = parse_env(captured.stdout)
            with plan.open("a", encoding="utf-8") as handle:
                handle.write("external change\n")
            provenance = run_script(
                REVIEW / "scripts" / "verify-plan-provenance.py",
                str(plan),
                "--snapshot-path",
                values["PLAN_SNAPSHOT_PATH"],
                "--expected-plan-sha256",
                values["PLAN_SHA256"],
                "--research-script",
                str(RESEARCH / "scripts" / "emit-plan-provenance.py"),
                cwd=root,
            )
            self.assertEqual(json.loads(provenance.stdout)["status"], "mismatch")

            plan.write_bytes(Path(values["PLAN_SNAPSHOT_PATH"]).read_bytes())
            script_link = root / "linked-provenance.py"
            script_link.symlink_to(RESEARCH / "scripts" / "emit-plan-provenance.py")
            linked_verifier = run_script(
                REVIEW / "scripts" / "verify-plan-provenance.py",
                str(plan),
                "--snapshot-path",
                values["PLAN_SNAPSHOT_PATH"],
                "--expected-plan-sha256",
                values["PLAN_SHA256"],
                "--research-script",
                str(script_link),
                cwd=root,
            )
            self.assertEqual(json.loads(linked_verifier.stdout)["status"], "unverifiable")
            self.assertIn("不得是 symlink", linked_verifier.stdout)

            first = json.loads(run_script(REVIEW / "scripts" / "capture-source-snapshot.py", cwd=root).stdout)
            write(root / "app.txt", "changed\n")
            second = json.loads(run_script(REVIEW / "scripts" / "capture-source-snapshot.py", cwd=root).stdout)
            self.assertNotEqual(first["source_snapshot_sha256"], second["source_snapshot_sha256"])
            app_path = root / "app.txt"
            app_path.chmod(app_path.stat().st_mode | stat.S_IXUSR)
            third = json.loads(run_script(REVIEW / "scripts" / "capture-source-snapshot.py", cwd=root).stdout)
            self.assertNotEqual(second["source_snapshot_sha256"], third["source_snapshot_sha256"])

            untracked = root / "new-tool.sh"
            write(untracked, "#!/bin/sh\nexit 0\n")
            fourth = json.loads(run_script(REVIEW / "scripts" / "capture-source-snapshot.py", cwd=root).stdout)
            untracked.chmod(untracked.stat().st_mode | stat.S_IXUSR)
            fifth = json.loads(run_script(REVIEW / "scripts" / "capture-source-snapshot.py", cwd=root).stdout)
            self.assertNotEqual(fourth["source_snapshot_sha256"], fifth["source_snapshot_sha256"])

            backslash_name = root / ".workflows\\visible.txt"
            write(backslash_name, "first\n")
            sixth = json.loads(run_script(REVIEW / "scripts" / "capture-source-snapshot.py", cwd=root).stdout)
            write(backslash_name, "second\n")
            seventh = json.loads(run_script(REVIEW / "scripts" / "capture-source-snapshot.py", cwd=root).stdout)
            self.assertNotEqual(sixth["source_snapshot_sha256"], seventh["source_snapshot_sha256"])

    def test_review_rejects_reversed_or_future_evidence_timeline(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "PASS", "confirmed")
            source_path = session / "review" / "source.md"
            source = source_path.read_text(encoding="utf-8")
            source_path.write_text(
                re.sub(
                    r"(?m)^- evidence_captured_at: .*?$",
                    "- evidence_captured_at: 2000-01-01T00:00:00+00:00",
                    source,
                ),
                encoding="utf-8",
                newline="\n",
            )
            reversed_evidence = run_script(
                REVIEW / "scripts" / "validate-review-run.py", str(session), cwd=root
            )
            self.assertNotEqual(reversed_evidence.returncode, 0)
            self.assertIn("不得早于 _run.md created_at", reversed_evidence.stdout)
            self.assertNotIn("Traceback", reversed_evidence.stdout + reversed_evidence.stderr)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "PASS", "confirmed")
            summary_path = session / "review" / "summary.md"
            summary = summary_path.read_text(encoding="utf-8")
            summary_path.write_text(
                re.sub(
                    r"(?m)^- summarized_at: .*?$",
                    "- summarized_at: 2999-01-01T00:00:00+00:00",
                    summary,
                ),
                encoding="utf-8",
                newline="\n",
            )
            future_summary = run_script(
                REVIEW / "scripts" / "validate-review-run.py",
                str(session),
                "--require-summary",
                cwd=root,
            )
            self.assertNotEqual(future_summary.returncode, 0)
            self.assertIn("summarized_at 不得位于未来", future_summary.stdout)
            self.assertNotIn("Traceback", future_summary.stdout + future_summary.stderr)

    def test_review_rejects_pass_backed_by_unverified_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "PASS", "unverified")
            invalid = run_script(REVIEW / "scripts" / "validate-review-run.py", str(session), cwd=root)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("PASS 明细字段不完整", invalid.stdout)

    def test_review_rejects_illegal_status_and_duplicate_route_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "PASS", "confirmed")
            review_dir = session / "review"

            source_path = review_dir / "source.md"
            original_source = source_path.read_text(encoding="utf-8")
            source_path.write_text(
                original_source.replace("## 元数据", "- 状态：MAYBE\n\n## 元数据", 1),
                encoding="utf-8",
                newline="\n",
            )
            illegal = run_script(REVIEW / "scripts" / "validate-review-run.py", str(session), cwd=root)
            self.assertNotEqual(illegal.returncode, 0)
            self.assertIn("非法状态值", illegal.stdout)
            source_path.write_text(original_source, encoding="utf-8", newline="\n")

            run_path = review_dir / "_run.md"
            run_text = run_path.read_text(encoding="utf-8")
            duplicate = "- route_items:\n  - web: none\n  - source: #1\n\n"
            run_path.write_text(run_text.replace("## Review Checklist", duplicate + "## Review Checklist", 1), encoding="utf-8", newline="\n")
            invalid_parent = run_script(
                REVIEW / "scripts" / "validate-review-run.py",
                str(session),
                "--parent-only",
                cwd=root,
            )
            self.assertNotEqual(invalid_parent.returncode, 0)
            self.assertIn("只能包含一个 route_items", invalid_parent.stdout)

    def test_json_control_files_require_objects_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "PASS", "confirmed")
            review_dir = session / "review"
            provenance_path = review_dir / "provenance.json"
            provenance_data = b"[]\n"
            provenance_path.write_bytes(provenance_data)
            run_path = review_dir / "_run.md"
            run_text = run_path.read_text(encoding="utf-8")
            run_path.write_text(
                re.sub(
                    r"(?m)^- provenance_result_sha256: [0-9a-f]{64}$",
                    f"- provenance_result_sha256: {hashlib.sha256(provenance_data).hexdigest()}",
                    run_text,
                ),
                encoding="utf-8",
                newline="\n",
            )

            rejected = run_script(REVIEW / "scripts" / "validate-review-run.py", str(session), cwd=root)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("顶层必须是 object", rejected.stdout)
            self.assertNotIn("Traceback", rejected.stdout + rejected.stderr)

        contract_module = load_script_module(
            REVIEW / "scripts" / "fix_state_contract.py", "workflow_fix_state_contract"
        )
        with self.assertRaisesRegex(OSError, "顶层必须是 object"):
            contract_module.parse_json_object("[]", "test JSON")

    def test_review_rejects_forged_provenance_and_missing_mandatory_synthetic_item(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            info = build_review_bundle(root, session, plan, "initial", "PASS", "confirmed")
            review_dir = session / "review"
            provenance_path = review_dir / "provenance.json"
            forged = {"status": "confirmed", "issues": [], "expected": {}}
            write(provenance_path, json.dumps(forged, ensure_ascii=False, sort_keys=True) + "\n")
            run_path = review_dir / "_run.md"
            run_text = run_path.read_text(encoding="utf-8")
            run_text = re.sub(
                r"(?m)^- provenance_result_sha256: [0-9a-f]{64}$",
                f"- provenance_result_sha256: {hashlib.sha256(provenance_path.read_bytes()).hexdigest()}",
                run_text,
            )
            run_path.write_text(run_text, encoding="utf-8", newline="\n")
            forged_result = run_script(
                REVIEW / "scripts" / "validate-review-run.py",
                str(session),
                "--parent-only",
                cwd=root,
            )
            self.assertNotEqual(forged_result.returncode, 0)
            self.assertIn("不是当前只读 verifier", forged_result.stdout)

            with (session / "research" / "web.md").open("a", encoding="utf-8") as handle:
                handle.write("tamper\n")
            refreshed = run_script(
                REVIEW / "scripts" / "verify-plan-provenance.py",
                str(plan),
                "--snapshot-path",
                str(review_dir / "plan-snapshot.md"),
                "--expected-plan-sha256",
                info["plan_sha"],
                "--output-path",
                str(provenance_path),
                "--research-script",
                str(RESEARCH / "scripts" / "emit-plan-provenance.py"),
                cwd=root,
            )
            self.assertEqual(refreshed.returncode, 0, refreshed.stdout + refreshed.stderr)
            self.assertEqual(json.loads(refreshed.stdout)["status"], "mismatch")
            run_text = run_path.read_text(encoding="utf-8")
            run_text = re.sub(r"(?m)^- provenance_status: \S+$", "- provenance_status: mismatch", run_text)
            run_text = re.sub(
                r"(?m)^- provenance_result_sha256: [0-9a-f]{64}$",
                f"- provenance_result_sha256: {hashlib.sha256(provenance_path.read_bytes()).hexdigest()}",
                run_text,
            )
            run_path.write_text(run_text, encoding="utf-8", newline="\n")
            missing_item = run_script(
                REVIEW / "scripts" / "validate-review-run.py",
                str(session),
                "--parent-only",
                cwd=root,
            )
            self.assertNotEqual(missing_item.returncode, 0)
            self.assertIn("synthetic:provenance:mismatch", missing_item.stdout)

    def test_review_fail_cannot_borrow_confirmed_evidence_from_pass_section(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            source_path = session / "review" / "source.md"
            text = source_path.read_text(encoding="utf-8")
            text = text.replace("证据级别：confirmed", "证据级别：unverified", 1)
            text = text.replace(
                "### 通过项\n- 无",
                "### 通过项\n- 状态：PASS\n  - 检查点：另一条独立通过事实\n  - 证据：app.txt（证据级别：confirmed）",
                1,
            )
            source_path.write_text(text, encoding="utf-8", newline="\n")
            result = run_script(REVIEW / "scripts" / "validate-review-run.py", str(session), cwd=root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("FAIL 明细字段不完整", result.stdout)

    def test_review_rejects_summary_extra_classification_and_cross_entry_borrowing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "PASS", "confirmed")
            summary_path = session / "review" / "summary.md"
            summary = summary_path.read_text(encoding="utf-8")
            summary_path.write_text(
                summary.replace(
                    "- 审查项 #1：全部相关路线 PASS",
                    "- 审查项 #1：全部相关路线 PASS\n- 审查项 #2：伪造额外分类",
                ),
                encoding="utf-8",
                newline="\n",
            )
            extra = run_script(
                REVIEW / "scripts" / "validate-review-run.py",
                str(session),
                "--require-summary",
                cwd=root,
            )
            self.assertNotEqual(extra.returncode, 0)
            self.assertIn("通过项总览必须且只能覆盖", extra.stdout)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            source_path = session / "review" / "source.md"
            source = source_path.read_text(encoding="utf-8")
            borrowed = "\n".join(
                [
                    "  - 问题：第一条状态额外问题",
                    "  - 证据：deployment-plan.md（证据级别：confirmed）",
                    "  - 建议修复：第一条状态额外建议",
                    "- 状态：FAIL",
                ]
            )
            source_path.write_text(
                source.replace(
                    "  - 建议修复：在操作字段加入 [REVIEW-FIX] 标记",
                    "  - 建议修复：在操作字段加入 [REVIEW-FIX] 标记\n" + borrowed,
                ),
                encoding="utf-8",
                newline="\n",
            )
            cross_entry = run_script(REVIEW / "scripts" / "validate-review-run.py", str(session), cwd=root)
            self.assertNotEqual(cross_entry.returncode, 0)
            self.assertIn("状态明细无法逐条解析", cross_entry.stdout)

    def test_archive_detects_history_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            info = build_review_bundle(root, session, plan, "initial", "PASS", "confirmed")
            first = run_script(REVIEW / "scripts" / "archive-review-run.py", str(session), cwd=root)
            self.assertEqual(first.returncode, 0, first.stderr)
            archived_source = session / "review" / "history" / info["review_run_id"] / "source.md"
            original_source = archived_source.read_bytes()
            with archived_source.open("a", encoding="utf-8") as handle:
                handle.write("tamper\n")
            second = run_script(REVIEW / "scripts" / "archive-review-run.py", str(session), cwd=root)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("history 内容", second.stderr)

            archived_source.write_bytes(original_source)
            write(archived_source.parent / "unexpected.txt", "unexpected\n")
            extra = run_script(REVIEW / "scripts" / "archive-review-run.py", str(session), cwd=root)
            self.assertNotEqual(extra.returncode, 0)
            self.assertIn("额外或缺失文件", extra.stderr)

    def test_archive_refuses_broken_history_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            info = build_review_bundle(root, session, plan, "initial", "PASS", "confirmed")
            history_dir = session / "review" / "history"
            history_dir.mkdir()
            target = history_dir / info["review_run_id"]
            target.symlink_to(root / "missing-history-target", target_is_directory=True)

            archived = run_script(REVIEW / "scripts" / "archive-review-run.py", str(session), cwd=root)
            self.assertNotEqual(archived.returncode, 0)
            self.assertIn("history target 无效", archived.stderr)
            self.assertTrue(target.is_symlink())

    def test_prepare_can_retire_partial_root_bundle_from_complete_history(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            info = build_review_bundle(root, session, plan, "initial", "PASS", "confirmed")
            archived = run_script(REVIEW / "scripts" / "archive-review-run.py", str(session), cwd=root)
            self.assertEqual(archived.returncode, 0, archived.stderr)

            review_dir = session / "review"
            (review_dir / "source.md").unlink()
            prepared = run_script(
                REVIEW / "scripts" / "prepare-review-run.py",
                str(session),
                "--mode",
                "resume",
                cwd=root,
            )
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            self.assertEqual(
                parse_env(prepared.stdout)["RETIRED_PATH"],
                str((review_dir / "history" / info["review_run_id"]).resolve()),
            )
            for name in (
                "_run.md",
                "plan-snapshot.md",
                "provenance.json",
                "web.md",
                "summary.md",
            ):
                self.assertFalse((review_dir / name).exists(), name)

    def test_mark_verified_requires_post_fix_mode(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            decision = run_script(
                REVIEW / "scripts" / "record-review-decision.py",
                str(session),
                "--decision",
                "approved-inline-fixes",
                "--item-ids",
                "#1",
                cwd=root,
            )
            self.assertEqual(decision.returncode, 0, decision.stderr)
            applied = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            build_review_bundle(root, session, plan, "post-fix", "PASS", "confirmed")
            run_path = session / "review" / "_run.md"
            run_path.write_text(
                run_path.read_text(encoding="utf-8").replace("- mode: post-fix", "- mode: initial"),
                encoding="utf-8",
                newline="\n",
            )
            marked = run_script(REVIEW / "scripts" / "mark-fix-verified.py", str(session), cwd=root)
            self.assertNotEqual(marked.returncode, 0)
            self.assertIn("post-fix review", marked.stderr)

    def test_forged_verified_state_requires_real_post_fix_pass_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            decision = run_script(
                REVIEW / "scripts" / "record-review-decision.py",
                str(session),
                "--decision",
                "approved-inline-fixes",
                "--item-ids",
                "#1",
                cwd=root,
            )
            self.assertEqual(decision.returncode, 0, decision.stderr)
            applied = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            state_path = session / "review" / "fix-state.md"
            state = state_path.read_text(encoding="utf-8")
            forged_run = f"{session.name}-review-ffffffffffffffff"
            forged = state.replace(
                "- status: applied-awaiting-post-fix-review",
                "\n".join(
                    [
                        f"- post_fix_review_run_id: {forged_run}",
                        f"- post_fix_summary_sha256: {'f' * 64}",
                        "- status: verified",
                        f"- verified_at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
                    ]
                ),
            )
            state_path.write_text(forged, encoding="utf-8", newline="\n")
            rejected = run_script(
                REVIEW / "scripts" / "prepare-review-run.py",
                str(session),
                "--mode",
                "initial",
                cwd=root,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("verified fix-state", rejected.stderr)
            self.assertIn("post-fix", rejected.stderr)

    def test_prepare_review_run_requires_recorded_changes_decision(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            skipped = run_script(
                REVIEW / "scripts" / "prepare-review-run.py",
                str(session),
                "--mode",
                "rerun-after-feedback",
                cwd=root,
            )
            self.assertNotEqual(skipped.returncode, 0)
            self.assertIn("尚未记录真实 _approval.md", skipped.stderr)

            decision = run_script(
                REVIEW / "scripts" / "record-review-decision.py",
                str(session),
                "--decision",
                "rejected-retry",
                "--item-ids",
                "none",
                cwd=root,
            )
            self.assertEqual(decision.returncode, 0, decision.stderr)
            prepared = run_script(
                REVIEW / "scripts" / "prepare-review-run.py",
                str(session),
                "--mode",
                "rerun-after-feedback",
                cwd=root,
            )
            self.assertEqual(prepared.returncode, 0, prepared.stderr)

    def test_prepared_fix_state_must_resume_apply_before_post_fix(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            decision = run_script(
                REVIEW / "scripts" / "record-review-decision.py",
                str(session),
                "--decision",
                "approved-inline-fixes",
                "--item-ids",
                "#1",
                cwd=root,
            )
            self.assertEqual(decision.returncode, 0, decision.stderr)
            applied = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            state_path = session / "review" / "fix-state.md"
            state = state_path.read_text(encoding="utf-8")
            backup_match = re.search(r"(?m)^- backup_path: (\S.*)$", state)
            self.assertIsNotNone(backup_match)
            backup = Path(backup_match.group(1))
            plan.write_bytes(backup.read_bytes())
            prepared_state = re.sub(
                r"(?m)^- status: applied-awaiting-post-fix-review$",
                "- status: prepared",
                state,
            )
            prepared_state = re.sub(r"(?m)^- applied_at: (\S.*)$", r"- prepared_at: \1", prepared_state)
            state_path.write_text(prepared_state, encoding="utf-8", newline="\n")

            premature = run_script(
                REVIEW / "scripts" / "prepare-review-run.py",
                str(session),
                "--mode",
                "post-fix",
                cwd=root,
            )
            self.assertNotEqual(premature.returncode, 0)
            self.assertIn("必须先幂等重跑 apply-inline-fixes.py", premature.stderr)

            resumed = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
            self.assertIn(
                "status: applied-awaiting-post-fix-review",
                state_path.read_text(encoding="utf-8"),
            )

    def test_fix_state_rejects_reversed_audit_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            decision = run_script(
                REVIEW / "scripts" / "record-review-decision.py",
                str(session),
                "--decision",
                "approved-inline-fixes",
                "--item-ids",
                "#1",
                cwd=root,
            )
            self.assertEqual(decision.returncode, 0, decision.stderr)
            applied = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            state_path = session / "review" / "fix-state.md"
            state = state_path.read_text(encoding="utf-8")
            state_path.write_text(
                re.sub(
                    r"(?m)^- applied_at: .*?$",
                    "- applied_at: 2000-01-01T00:00:00+00:00",
                    state,
                ),
                encoding="utf-8",
                newline="\n",
            )
            rejected_state = run_script(
                REVIEW / "scripts" / "prepare-review-run.py",
                str(session),
                "--mode",
                "post-fix",
                cwd=root,
            )
            self.assertNotEqual(rejected_state.returncode, 0)
            self.assertIn("不得早于 archived approval", rejected_state.stderr)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            decision = run_script(
                REVIEW / "scripts" / "record-review-decision.py",
                str(session),
                "--decision",
                "approved-inline-fixes",
                "--item-ids",
                "#1",
                cwd=root,
            )
            self.assertEqual(decision.returncode, 0, decision.stderr)
            applied = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            build_review_bundle(root, session, plan, "post-fix", "PASS", "confirmed")
            summary_path = session / "review" / "summary.md"
            summary = summary_path.read_text(encoding="utf-8")
            summary_path.write_text(
                re.sub(
                    r"(?m)^- summarized_at: .*?$",
                    "- summarized_at: 2000-01-01T00:00:00+00:00",
                    summary,
                ),
                encoding="utf-8",
                newline="\n",
            )
            rejected_verified = run_script(REVIEW / "scripts" / "mark-fix-verified.py", str(session), cwd=root)
            self.assertNotEqual(rejected_verified.returncode, 0)
            rejected_output = rejected_verified.stdout + rejected_verified.stderr
            self.assertIn("summarized_at", rejected_output)
            self.assertNotIn("Traceback", rejected_output)

    def test_atomic_write_reports_primary_and_cleanup_failures(self) -> None:
        module = load_script_module(
            REVIEW / "scripts" / "capture-plan.py",
            "heavy_review_capture_plan_cleanup_test",
        )
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "plan-snapshot.md"
            with (
                mock.patch.object(module.os, "replace", side_effect=OSError("replace failed")),
                mock.patch.object(module, "cleanup_temp", return_value="cleanup failed"),
            ):
                with self.assertRaisesRegex(OSError, "replace failed.*cleanup failed"):
                    module.atomic_write_snapshot(target, b"snapshot\n")

    def test_write_helpers_report_permission_failures_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            workflows = root / ".workflows"
            workflows.mkdir()
            workflows.chmod(0o500)
            try:
                created = run_script(
                    RESEARCH / "scripts" / "new-session-dir.py",
                    "--topic-hash",
                    TOPIC_HASH,
                    cwd=root,
                )
            finally:
                workflows.chmod(0o700)
            self.assertNotEqual(created.returncode, 0)
            self.assertIn("无法创建 session 目录", created.stderr)
            self.assertNotIn("Traceback", created.stdout + created.stderr)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            session.chmod(0o500)
            try:
                ensured = run_script(
                    REVIEW / "scripts" / "ensure-review-dir.py",
                    str(session),
                    cwd=root,
                )
            finally:
                session.chmod(0o700)
            self.assertNotEqual(ensured.returncode, 0)
            self.assertIn("无法创建 review/ 目录", ensured.stderr)
            self.assertNotIn("Traceback", ensured.stdout + ensured.stderr)

            ensured = run_script(REVIEW / "scripts" / "ensure-review-dir.py", str(session), cwd=root)
            self.assertEqual(ensured.returncode, 0, ensured.stderr)
            review_dir = session / "review"
            review_dir.chmod(0o500)
            try:
                captured = run_script(REVIEW / "scripts" / "capture-plan.py", str(plan), cwd=root)
            finally:
                review_dir.chmod(0o700)
            self.assertNotEqual(captured.returncode, 0)
            self.assertIn("无法原子写入 plan snapshot", captured.stderr)
            self.assertNotIn("Traceback", captured.stdout + captured.stderr)

    def test_prepare_rejects_tampered_fix_state_archive_binding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            decision = run_script(
                REVIEW / "scripts" / "record-review-decision.py",
                str(session),
                "--decision",
                "approved-inline-fixes",
                "--item-ids",
                "#1",
                cwd=root,
            )
            self.assertEqual(decision.returncode, 0, decision.stderr)
            applied = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            state_path = session / "review" / "fix-state.md"
            state = state_path.read_text(encoding="utf-8")
            state_path.write_text(
                re.sub(
                    r"(?m)^- review_approval_sha256: [0-9a-f]{64}$",
                    "- review_approval_sha256: " + "0" * 64,
                    state,
                ),
                encoding="utf-8",
                newline="\n",
            )
            rejected = run_script(
                REVIEW / "scripts" / "prepare-review-run.py",
                str(session),
                "--mode",
                "post-fix",
                cwd=root,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("archive manifest 不一致", rejected.stderr)

    def test_fix_state_candidate_hash_must_replay_archived_fixes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            decision = run_script(
                REVIEW / "scripts" / "record-review-decision.py",
                str(session),
                "--decision",
                "approved-inline-fixes",
                "--item-ids",
                "#1",
                cwd=root,
            )
            self.assertEqual(decision.returncode, 0, decision.stderr)
            applied = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            forged_plan = b"externally replaced candidate\n"
            plan.write_bytes(forged_plan)
            state_path = session / "review" / "fix-state.md"
            state = state_path.read_text(encoding="utf-8")
            state_path.write_text(
                re.sub(
                    r"(?m)^- candidate_plan_sha256: [0-9a-f]{64}$",
                    f"- candidate_plan_sha256: {hashlib.sha256(forged_plan).hexdigest()}",
                    state,
                ),
                encoding="utf-8",
                newline="\n",
            )
            rejected = run_script(
                REVIEW / "scripts" / "prepare-review-run.py",
                str(session),
                "--mode",
                "post-fix",
                cwd=root,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("机械重放", rejected.stderr)

    def test_review_helpers_reject_parent_and_control_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            first, _ = create_research_bundle(root, "2026-07-26-120000")
            second, second_plan = create_research_bundle(root, "2026-07-26-120001")
            for session in (first, second):
                ensured = run_script(REVIEW / "scripts" / "ensure-review-dir.py", str(session), cwd=root)
                self.assertEqual(ensured.returncode, 0, ensured.stderr)
            captured = run_script(REVIEW / "scripts" / "capture-plan.py", str(second_plan), cwd=root)
            self.assertEqual(captured.returncode, 0, captured.stderr)

            first_review = first / "review"
            first_review.rmdir()
            first_review.symlink_to(second / "review", target_is_directory=True)
            escaped = run_script(
                REVIEW / "scripts" / "hash-plan-locator.py",
                str(first_review / "plan-snapshot.md"),
                "lines 1-1",
                cwd=root,
            )
            self.assertNotEqual(escaped.returncode, 0)
            self.assertIn("父级不得是 symlink", escaped.stderr)

            run_path = second / "review" / "_run.md"
            outside_run = root / "outside-run.md"
            write(outside_run, "- review_run_id: forged\n")
            run_path.symlink_to(outside_run)
            generated = run_script(REVIEW / "scripts" / "new-review-run-id.py", str(second), cwd=root)
            self.assertNotEqual(generated.returncode, 0)
            self.assertIn("_run.md 必须是真实普通文件", generated.stderr)

            session_alias = root / "session-alias"
            session_alias.symlink_to(second, target_is_directory=True)
            for script, extra_args in (
                ("record-review-decision.py", ("--decision", "rejected-retry", "--item-ids", "none")),
                ("archive-review-run.py", ()),
            ):
                rejected = run_script(
                    REVIEW / "scripts" / script,
                    str(session_alias),
                    *extra_args,
                    cwd=root,
                )
                self.assertNotEqual(rejected.returncode, 0)
                self.assertIn("SESSION_DIR 不得是 symlink", rejected.stderr)
                self.assertNotIn("Traceback", rejected.stdout + rejected.stderr)

    def test_review_validator_rejects_symlinked_fixed_plan_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            build_review_bundle(root, session, plan, "initial", "PASS", "confirmed")
            escaped = root / ".workflows" / "escaped-plan.md"
            plan.rename(escaped)
            plan.symlink_to(escaped)
            run_path = session / "review" / "_run.md"
            run_text = run_path.read_text(encoding="utf-8")
            run_path.write_text(
                re.sub(r"(?m)^- plan_path: \S.*$", f"- plan_path: {escaped.resolve()}", run_text),
                encoding="utf-8",
                newline="\n",
            )
            rejected = run_script(
                REVIEW / "scripts" / "validate-review-run.py",
                str(session),
                "--require-summary",
                cwd=root,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("deployment-plan.md 必须是当前 session 内的真实普通文件", rejected.stdout)

    def test_provenance_verifier_detects_plan_drift_during_generator(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            ensured = run_script(REVIEW / "scripts" / "ensure-review-dir.py", str(session), cwd=root)
            self.assertEqual(ensured.returncode, 0, ensured.stderr)
            captured = run_script(REVIEW / "scripts" / "capture-plan.py", str(plan), cwd=root)
            self.assertEqual(captured.returncode, 0, captured.stderr)
            values = parse_env(captured.stdout)
            mutator = root / "mutating-provenance.py"
            write(
                mutator,
                "\n".join(
                    [
                        "from pathlib import Path",
                        "import subprocess",
                        "import sys",
                        f"real = {str(RESEARCH / 'scripts' / 'emit-plan-provenance.py')!r}",
                        "session = Path(sys.argv[1])",
                        "result = subprocess.run([sys.executable, real, str(session)], text=True, capture_output=True)",
                        "sys.stdout.write(result.stdout)",
                        "sys.stderr.write(result.stderr)",
                        "with (session / 'deployment-plan.md').open('a', encoding='utf-8') as handle:",
                        "    handle.write('drift during provenance\\n')",
                        "raise SystemExit(result.returncode)",
                        "",
                    ]
                ),
            )
            checked = run_script(
                REVIEW / "scripts" / "verify-plan-provenance.py",
                str(plan),
                "--snapshot-path",
                values["PLAN_SNAPSHOT_PATH"],
                "--expected-plan-sha256",
                values["PLAN_SHA256"],
                "--research-script",
                str(mutator),
                cwd=root,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            payload = json.loads(checked.stdout)
            self.assertEqual(payload["status"], "mismatch")
            self.assertTrue(any("发生变化" in issue for issue in payload["issues"]))

    def test_source_snapshot_marks_dirty_submodule_unverifiable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "main"
            submodule = base / "submodule"
            root.mkdir()
            submodule.mkdir()
            init_repo(root)
            init_repo(submodule)
            added = run_command(
                root,
                "git",
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "-q",
                str(submodule),
                "deps/submodule",
            )
            self.assertEqual(added.returncode, 0, added.stderr)
            committed = run_command(root, "git", "commit", "-qam", "add submodule")
            self.assertEqual(committed.returncode, 0, committed.stderr)

            clean = json.loads(run_script(REVIEW / "scripts" / "capture-source-snapshot.py", cwd=root).stdout)
            self.assertEqual(clean["status"], "confirmed")
            write(root / "deps" / "submodule" / "app.txt", "dirty\n")
            dirty = json.loads(run_script(REVIEW / "scripts" / "capture-source-snapshot.py", cwd=root).stdout)
            self.assertEqual(dirty["status"], "unverifiable")
            self.assertIn("submodule", dirty["reason"])

    def test_source_snapshot_marks_git_visible_special_file_unverifiable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            tracked = root / "app.txt"
            tracked.unlink()
            os.mkfifo(tracked)

            captured = json.loads(run_script(REVIEW / "scripts" / "capture-source-snapshot.py", cwd=root).stdout)
            self.assertEqual(captured["status"], "unverifiable")
            self.assertIn("不是可精确绑定", captured["reason"])
            self.assertIn("app.txt", captured["reason"])

            contract_module = load_script_module(
                REVIEW / "scripts" / "fix_state_contract.py", "workflow_nonblocking_reader_contract"
            )
            with self.assertRaisesRegex(OSError, "不是普通文件"):
                contract_module.read_regular(tracked)

    def test_inline_fix_rejects_fake_session_before_idempotent_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            review_dir = root / ".workflows" / "2026-02-30-120000" / "review"
            plan = review_dir.parent / "deployment-plan.md"
            base = b"base\n"
            candidate = b"candidate\n"
            write(plan, candidate.decode("utf-8"))
            summary = b"summary\n"
            write(review_dir / "summary.md", summary.decode("utf-8"))
            fixes = {
                "session_id": review_dir.parent.name,
                "review_run_id": f"{review_dir.parent.name}-review-0123456789abcdef",
                "expected_plan_sha256": hashlib.sha256(base).hexdigest(),
                "replacements": [{"item_ids": ["#1"], "old": "base", "new": "[REVIEW-FIX] candidate"}],
            }
            write(review_dir / "fixes.json", json.dumps(fixes, sort_keys=True) + "\n")
            write(
                review_dir / "fix-state.md",
                "\n".join(
                    [
                        "# Heavy Review Inline Fix State",
                        "",
                        f"- session_id: {review_dir.parent.name}",
                        f"- review_run_id: {fixes['review_run_id']}",
                        f"- base_plan_sha256: {fixes['expected_plan_sha256']}",
                        f"- candidate_plan_sha256: {hashlib.sha256(candidate).hexdigest()}",
                        f"- review_summary_sha256: {hashlib.sha256(summary).hexdigest()}",
                        f"- fixes_sha256: {hashlib.sha256((review_dir / 'fixes.json').read_bytes()).hexdigest()}",
                        "- approved_item_ids: #1",
                        "- archive_path: none",
                        "- backup_path: none",
                        "- applied_replacements: 1",
                        "- status: applied-awaiting-post-fix-review",
                        f"- applied_at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
                        "",
                    ]
                ),
            )
            rejected = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("真实时间戳 session", rejected.stdout)

    def test_inline_fix_requires_post_fix_pass_before_verified(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            first = build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            valid = run_script(
                REVIEW / "scripts" / "validate-review-run.py",
                str(session),
                "--require-summary",
                cwd=root,
            )
            self.assertEqual(valid.returncode, 0, valid.stdout)
            decision = run_script(
                REVIEW / "scripts" / "record-review-decision.py",
                str(session),
                "--decision",
                "approved-inline-fixes",
                "--item-ids",
                "#1",
                cwd=root,
            )
            self.assertEqual(decision.returncode, 0, decision.stderr)
            original_mode = stat.S_IMODE(plan.stat().st_mode)
            applied = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            self.assertEqual(stat.S_IMODE(plan.stat().st_mode), original_mode)
            state = (session / "review" / "fix-state.md").read_text(encoding="utf-8")
            self.assertIn("status: applied-awaiting-post-fix-review", state)
            self.assertTrue((session / "review" / "history" / first["review_run_id"]).is_dir())
            self.assertIn("[REVIEW-FIX]", plan.read_text(encoding="utf-8"))

            second = build_review_bundle(root, session, plan, "post-fix", "PASS", "confirmed")
            post_valid = run_script(
                REVIEW / "scripts" / "validate-review-run.py",
                str(session),
                "--require-summary",
                cwd=root,
            )
            self.assertEqual(post_valid.returncode, 0, post_valid.stdout)
            marked = run_script(REVIEW / "scripts" / "mark-fix-verified.py", str(session), cwd=root)
            self.assertEqual(marked.returncode, 0, marked.stderr)
            verified = (session / "review" / "fix-state.md").read_text(encoding="utf-8")
            self.assertIn("status: verified", verified)
            self.assertIn(f"post_fix_review_run_id: {second['review_run_id']}", verified)
            retired = run_script(
                REVIEW / "scripts" / "prepare-review-run.py",
                str(session),
                "--mode",
                "initial",
                cwd=root,
            )
            self.assertEqual(retired.returncode, 0, retired.stderr)
            recovered = run_script(
                REVIEW / "scripts" / "prepare-review-run.py",
                str(session),
                "--mode",
                "initial",
                cwd=root,
            )
            self.assertEqual(recovered.returncode, 0, recovered.stderr)

    def test_multiple_inline_fix_rounds_preserve_fix_history(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            init_repo(root)
            session, plan = create_research_bundle(root)
            first = build_review_bundle(root, session, plan, "initial", "FAIL", "confirmed")
            first_decision = run_script(
                REVIEW / "scripts" / "record-review-decision.py",
                str(session),
                "--decision",
                "approved-inline-fixes",
                "--item-ids",
                "#1",
                cwd=root,
            )
            self.assertEqual(first_decision.returncode, 0, first_decision.stderr)
            first_apply = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertEqual(first_apply.returncode, 0, first_apply.stdout + first_apply.stderr)

            second = build_review_bundle(root, session, plan, "post-fix", "FAIL", "confirmed")
            second_decision = run_script(
                REVIEW / "scripts" / "record-review-decision.py",
                str(session),
                "--decision",
                "approved-inline-fixes",
                "--item-ids",
                "#1",
                cwd=root,
            )
            self.assertEqual(second_decision.returncode, 0, second_decision.stderr)
            second_apply = run_script(REVIEW / "scripts" / "apply-inline-fixes.py", str(plan), cwd=root)
            self.assertEqual(second_apply.returncode, 0, second_apply.stdout + second_apply.stderr)

            prior_state = session / "review" / "fix-history" / f"{first['review_run_id']}.md"
            self.assertTrue(prior_state.is_file())
            self.assertIn("status: applied-awaiting-post-fix-review", prior_state.read_text(encoding="utf-8"))
            current_state = (session / "review" / "fix-state.md").read_text(encoding="utf-8")
            self.assertIn(f"review_run_id: {second['review_run_id']}", current_state)

            build_review_bundle(root, session, plan, "post-fix", "PASS", "confirmed")
            marked = run_script(REVIEW / "scripts" / "mark-fix-verified.py", str(session), cwd=root)
            self.assertEqual(marked.returncode, 0, marked.stderr)

    def test_static_contracts_have_no_known_old_closure(self) -> None:
        review_text = "\n".join(path.read_text(encoding="utf-8") for path in (REVIEW / "references").glob("*.md"))
        skill_text = (REVIEW / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("可以基于此版本部署", review_text + skill_text)
        self.assertNotIn("rerun-after-r3", review_text + skill_text)
        self.assertNotIn("statement: <plan", review_text + skill_text)
        self.assertIn("post-fix", skill_text)
        for script_name in set(re.findall(r"scripts/([A-Za-z0-9_.-]+\.py)", skill_text)):
            candidates = (REVIEW / "scripts" / script_name, RESEARCH / "scripts" / script_name)
            self.assertTrue(any(candidate.is_file() for candidate in candidates), script_name)
        prepare_text = (REVIEW / "scripts" / "prepare-review-run.py").read_text(encoding="utf-8")
        self.assertLess(
            prepare_text.index('with reason_path.open("x"'),
            prepare_text.index("move_invalid_bundle(current, orphan_dir)"),
        )
        for scripts_dir in (RESEARCH / "scripts", REVIEW / "scripts"):
            for path in scripts_dir.glob("*.py"):
                for line in path.read_text(encoding="utf-8").splitlines():
                    if "O_RDONLY" in line and "O_NOFOLLOW" in line:
                        self.assertIn("O_NONBLOCK", line, str(path))


if __name__ == "__main__":
    unittest.main()
