# Main Agent 审查综合与决策文件

R2 报告通过 `validate-review-run.py` 后，main agent 按本文件生成 `fixes.json`（如需要）和 `summary.md`。

## 聚合

按 item 编号聚合相关路线：

- 任一路线 FAIL → item FAIL。
- 无 FAIL、任一路线 UNVERIFIABLE → item UNVERIFIABLE。
- 所有相关路线 PASS → item PASS。
- 空路线不参与不属于它的 item。

严重度由 `review-framework.md` 三轴规则确定，按 HIGH → MED → LOW 展示。UNVERIFIABLE 单独列出；HIGH-candidate 的无法验证项必须转化为前置检查、人工确认、缩小范围或补证修复。

## `fixes.json`

verdict 为 changes-required 时，先写合法 JSON：

```json
{
  "session_id": "真实 SESSION_ID",
  "review_run_id": "真实 REVIEW_RUN_ID",
  "expected_plan_sha256": "当前 PLAN_SHA256",
  "replacements": [
    {
      "item_ids": ["#1"],
      "old": "当前 plan 中精确出现一次的完整旧文本",
      "new": "包含 [REVIEW-FIX] 来源标记的完整新文本"
    }
  ]
}
```

约束：

- replacements 按顺序应用；每个 old 在前序替换后的候选 plan 中精确出现一次。
- item_ids 合集精确覆盖全部 FAIL/UNVERIFIABLE item，不能漏项或引用 PASS item。
- new 必须包含 `[REVIEW-FIX]` 和来源 item 编号，不含模板标记。
- 不能用模糊搜索、行号写入或自然语言“请修改”；必须是可恢复的精确替换。
- verdict PASS 时根目录不得存在 `fixes.json`。

## `summary.md`

```markdown
# Heavy Review Summary

## 审查报告：真实 plan 主题

### HIGH 严重度问题
真实问题；无则写“无”。

### MED 严重度问题
真实问题；无则写“无”。

### LOW 严重度问题
真实问题；无则写“无”。

### 通过项总览
- 审查项 #N：全部相关路线 PASS

### 无法验证项
真实内容；无则写“无”。

### 修复方案汇总
逐项说明修改章节和理由；PASS 时写“无”。

## 元数据
- session_id: 真实值
- review_run_id: 真实值
- plan_sha256: 真实值
- source_snapshot_sha256: 真实 hash 或 none
- provenance_result_sha256: provenance.json hash
- web_report_sha256: web.md hash
- source_report_sha256: source.md hash
- fixes_sha256: fixes.json hash 或 none
- passing_item_ids: #N 列表或 none
- failing_item_ids: #N 列表或 none
- unverifiable_item_ids: #N 列表或 none
- verdict: pass 或 changes-required
- summarized_at: 带时区 ISO-8601
```

正文每条发现保留来源路线、证据等级、精确 locator 和建议修复。每个非空分类以 `- 审查项 #N：...` 开头：FAIL 在 HIGH/MED/LOW 合计恰好出现一次，PASS、UNVERIFIABLE 和修复方案分别恰好覆盖自己的元数据集合，不得出现额外或重复编号。不得保留尖括号/枚举/省略号模板占位。

写完必须运行 `validate-review-run.py SESSION_DIR --require-summary`。validator 输出才是 verdict 真源。

## 用户交互

- PASS：无需用户批准；若是 post-fix，先 `mark-fix-verified.py`。
- changes-required：展示 summary 后，让用户批准全部文件化 fixes，或拒绝并补充关注点。
- 批准/拒绝都必须用 `record-review-decision.py` 持久化；聊天中的“同意”不能单独恢复。
- 拒绝后使用新 review id 全量重跑；若更早一轮 fix-state 仍等待验证，mode 保持 `post-fix`，否则用 `rerun-after-feedback`。批准后用事务 helper 应用，再使用新 review id 全量 post-fix 复审。
