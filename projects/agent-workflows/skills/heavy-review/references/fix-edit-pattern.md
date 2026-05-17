# Inline 修复 deployment-plan.md 的规范

用户确认修复方案合理后，main agent 用 Edit 工具直接修改 `<PLAN_PATH>`。

---

## 核心原则

**不新建修复版 plan，直接 Edit 原 deployment-plan.md**。

理由：deployment-plan 是部署的唯一真源，修复必须落到原文，避免出现"原 plan + 修复 patch"两份脱节的文件。

用户确认修复方案后，在任何 R4 写入前（包括写备份前），先重新计算 `<PLAN_PATH>` 当前内容 SHA-256，并与 R3 综合报告使用的 `plan_sha256` 对比。若不一致，说明 plan 已被外部修改；停止 inline 修复，回到 R1/R2 用新的 `review_run_id` 重新审查，避免把旧审查建议套到新 plan 上，也不得写入备份。

首写前 hash 一致后，把 `expected_plan_sha256` 初始化为 R3 使用的 `plan_sha256`，再把原始 plan 复制到 `<SESSION_DIR>/review/deployment-plan.before-inline-fix.md` 作为只读回滚备份。若该文件已存在，不得覆盖，改写入 `<SESSION_DIR>/review/deployment-plan.before-inline-fix.YYYY-MM-DD-HHmmss.md`，同时保留已有备份。该备份写入是 R4 阶段除修改 deployment-plan.md 外唯一允许的额外写入；这不影响 R2 取证阶段按输出契约写入 review 报告。备份只用于撤销 inline 修改，不是新的执行真源，不得在后续部署中引用。

后续每次 Edit 前，都重新计算 `<PLAN_PATH>` 当前 hash，并只与 `expected_plan_sha256` 对比；不再拿 R3 的原始 hash 反复比较。若不一致，说明发生了本流程之外的外部修改，必须停止剩余 Edit 并向用户报告。每次成功 Edit 后，立即重新计算 plan hash 并更新 `expected_plan_sha256`，让本流程自己的上一处修改成为下一处修改的合法基线。

---

## 修复落点的对应关系

每条修复必须落到 plan 的某个章节：

| 修复类型 | 落点章节 |
|---------|---------|
| 缺少环境检查 | `## 前置检查` |
| 步骤遗漏 | `## 执行步骤`（在对应步骤前后插入） |
| 步骤不可逆但无回滚 | `## 回滚方案`（补充替代措施） |
| 未识别的风险 | `## 风险清单`（新增行） |
| 调研摘要中 CONFLICT 未处理 | `## 执行步骤`（增加处理说明） |
| 步骤可逆性标注错误 | 修改对应步骤的 `**可逆性**` 字段 |

---

## 修复标注

每条修复在 plan 中插入时，用引用块标注修复来源，便于追溯：

```markdown
### 步骤 2：<操作名>
- **操作**：...
- **影响范围**：...
- **可逆性**：可逆

> [REVIEW-FIX] 增加前置确认 <项> 已生效。来源：审查项 #N（联网取证路线）
```

---

## Edit 操作的颗粒度

- 一次 Edit 只改一处，避免一次性大改导致冲突
- 修改前先 Read 一次确认 plan 当前状态
- 修改后向用户简短报告："已修复 N 处，详情见 <PLAN_PATH>"

---

## 完成后告知

修改全部完成后，输出：

> 修复已 inline 进 <PLAN_PATH>，共 N 处。可以基于此版本部署。

任务结束。
