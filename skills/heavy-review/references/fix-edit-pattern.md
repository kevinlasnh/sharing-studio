# Inline Fix 事务与 post-fix 闭环

本流程不让 main agent 直接做多次自由 Edit。修复规格、用户批准、备份、替换和验证都必须文件化。

## 入口条件

1. 当前 `summary.md` 已通过 `validate-review-run.py --require-summary`，verdict 为 changes-required。
2. `fixes.json` hash 与 summary 元数据一致，覆盖全部 FAIL/UNVERIFIABLE item。
3. 用户批准已由 `record-review-decision.py` 写入 `_approval.md`，批准 item 集合与 fixes 精确一致。
4. live plan hash 仍等于本轮 plan hash。

任一不满足都不得写 plan。

## 执行

运行：

```bash
python3 ~/.agents/skills/heavy-review/scripts/apply-inline-fixes.py "$PLAN_PATH"
```

helper 会：

- 再次验证 review bundle、summary、fixes 和 approval。
- 把当前 run 归档到 `review/history/<review_run_id>/`。
- 获取 no-follow 文件锁。
- 创建不覆盖的 `deployment-plan.before-inline-fix*.md` 备份。
- 保留原 plan 文件 mode。
- 写 `fix-state.md status: prepared`，绑定 base/candidate hash、summary/fixes、`review_approval_sha256`、批准项、归档和备份路径。
- 原子替换 plan。
- 写 `status: applied-awaiting-post-fix-review`。

中断时重跑 helper：

- live hash 等于 base → 可从 prepared state 继续。
- live hash 等于 candidate → 幂等认定已应用并修复 state。
- 其他 hash → 停止，报告外部修改冲突。
- `prepare-review-run.py` 看到 prepared state 会拒绝开始 post-fix；必须先重跑本 helper，直到 state 为 `applied-awaiting-post-fix-review`。
- 每次开始不同 `review_run_id` 的新修复事务前，旧 `fix-state.md` 原文写入 `review/fix-history/<旧 review_run_id>.md`；同名历史内容不同则停止，不能覆盖审计链。
- 共享 state contract 机械要求时间线单调：initial summary 不晚于 approval，approval 不晚于 prepared/applied，applied 不晚于 post-fix summary，post-fix summary 不晚于 verified。

## post-fix

应用成功不代表 plan 通过。立即开始 mode=`post-fix` 的全新完整 review：新 id、新 plan snapshot、新 source snapshot、新 provenance、全部适用路线重跑。

- 仍有 FAIL/UNVERIFIABLE：生成新 fixes，重新请求批准。
- 全 PASS：运行 `mark-fix-verified.py SESSION_DIR`，将 fix-state 绑定到 post-fix review run 和 summary hash。

只有 `fix-state status: verified` 才能声称“当前修改后的 plan 已通过 Heavy Review”。仍然不能声称部署已执行。
