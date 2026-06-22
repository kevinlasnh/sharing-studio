# Main Agent 审查综合模板

取证路线报告准备好后（本次新启动的 subagent Done、main agent 顺序执行写完结果文件、中断恢复复用的旧报告已通过文件校验，或空路线由 main agent 写占位报告），main agent 按此模板综合成统一审查报告。

---

## 综合步骤

1. 综合前重新计算 `<PLAN_PATH>` 当前内容 SHA-256；若与 R1 记录的 `plan_sha256` 不一致，停止综合并重跑审查，因为 review 报告对应的已不是当前 plan
2. 读取 `<SESSION_DIR>/review/_run.md`；该文件必须能解析出 `review_run_id`、`plan_sha256`、`route_items`、有效 `mode` 和完整 `## Review Checklist`，且 checklist 至少包含一个可解析的 `审查项 #N`。每个审查项必须包含 `statement:`、`evidence_route:`、`risk_dimensions:`、`risk_hint:` 四个字段；`evidence_route` 只能是 `联网` / `源码` / `都需要`，`risk_hint` 只能是 `HIGH-candidate` / `normal`。缺失字段、字段值非法、`mode` 保留枚举占位、或 checklist 为空时不得综合，必须重跑审查
3. 读取 `<SESSION_DIR>/review/` 下的 2 份 md 文件（web.md / source.md）；若某文件含 `## 无适用审查项`，必须确认 `_run.md` 中该路线的 `route_items` 值为 `none`，且该占位报告含 `## 元数据`、本轮 `review_run_id`、当前 `plan_sha256` 和 `本路线审查项覆盖率：0/0（无适用项）`，该路线才标注为不适用且不计入通过项；若 `_run.md` 给该路线分配了任何审查项编号但报告却是空路线占位，不得综合，必须重跑该路线。本轮必须有 `review_run_id` 和 `plan_sha256`，两份文件的元数据必须匹配 `_run.md`，且 `plan_sha256` 必须等于 R1 当前 plan hash，否则视为旧轮残留或旧 plan 报告，不得综合
4. `_run.md` 的 `route_items` 必须同时列出 web 和 source；某路线无 item 时值必须为 `none`。web 和 source 不得同时为 `none`，否则说明 R2.1 清单生成失败。缺少路线行、两路线同时为空、保留模板占位、保留尖括号、保留说明文字或省略号时不得综合，因为 main agent 无法区分“空路线”“漏写路线”和“未替换模板”
5. `_run.md` 中 web / source 的 `route_items` 分配必须与 `## Review Checklist` 中每个 item 的 `evidence_route` 字段精确一致：`evidence_route: 联网` 的 item 只能出现在 web；`evidence_route: 源码` 的 item 只能出现在 source；`evidence_route: 都需要` 的 item 必须同时出现在 web 和 source；不得漏掉 checklist item，也不得出现 checklist 中不存在的编号。若不满足，不得综合，必须修正 `_run.md` 或重建本轮审查
6. 若 `_run.md` 中某路线的 `route_items` 为 `none`，对应结果文件必须是空路线占位报告；若该文件残留任何 `## 审查项 #` 非空报告内容，不得综合，必须覆盖为空路线占位报告或重建本轮审查
7. 每份非空路线报告必须覆盖 `_run.md` 中 `route_items` 分配给该路线的所有审查项编号，并且每个被分配审查项都必须保留 `### 路线结论`、`### 发现`、`### 通过项`、`### 无法验证项` 四个小节，写出 `route_conclusion` 字段，字段值只能等于 `PASS`、`FAIL`、`UNVERIFIABLE` 三者之一；审查项标题风险提示必须来自 checklist 的 `risk_hint`，只能写 `HIGH-candidate` / `normal`；证据级别只能写 `confirmed` / `unverified` / `CONFLICT` / `STALE` / `MISSING`。缺失编号、缺少任一必需小节、保留模板说明行、保留任何尖括号占位符或省略号占位、缺失 `route_conclusion`、`route_conclusion` 保留枚举占位 / 同时写多个值、标题风险提示或证据级别缺失 / 非法 / 保留枚举占位、`route_conclusion` 与明细状态不符合 FAIL > UNVERIFIABLE > PASS 判定规则、或 `route_conclusion` 缺少对应明细支撑（PASS 无真实通过项、FAIL 无真实失败发现和建议修复、UNVERIFIABLE 无真实无法验证项和原因）时不得综合
8. 按每个审查项聚合 `route_conclusion`：任一相关取证路线为 `FAIL` → 进入严重度问题；无 FAIL 但任一相关取证路线为 `UNVERIFIABLE` → 进入无法验证项；只有所有相关取证路线均为 `PASS` → 才进入通过项总览。`route_items` 中该路线值为 `none` 的空路线不参与该审查项聚合
9. 按审查项编号对齐：同一编号的 2 条取证路线发现放在一起，并保留风险提示 HIGH-candidate / normal
10. 标注每条发现的来源取证路线
11. 按严重度排序：HIGH → MED → LOW
12. 单独列出 `UNVERIFIABLE`，不得把它们并入通过项；HIGH-candidate 的无法验证项必须进入修复方案汇总
13. 输出统一审查报告到 terminal（不写文件）

严重度由 main agent 在本阶段按 `review-framework.md` 的三轴规则统一判定。subagent 输出中的 PASS / FAIL / UNVERIFIABLE、证据级别和修复建议是判定输入。

---

## 输出格式

```markdown
## 审查报告：<plan 主题>

### HIGH 严重度问题

#### 审查项 #1（HIGH-candidate）：<原文>
- 发现：<问题描述> [联网]
  - 证据：<...>
  - 建议修复：<具体修改>
- 发现：<问题描述> [源码]
  - 证据：<...>
  - 建议修复：<具体修改>

### MED 严重度问题

#### 审查项 #2（normal）：<原文>
- 发现：<问题描述> [联网]
  - 证据：<...>
  - 建议修复：<具体修改>

### LOW 严重度问题

#### 审查项 #3（normal）：<原文>
- 发现：<问题描述> [源码]
  - 证据：<...>
  - 建议修复：<具体修改>

### 通过项总览
- 审查项 #N：所有相关取证路线的 `route_conclusion` 均为 PASS

### 无法验证项
- 审查项 #M（HIGH-candidate）：<无法验证内容> [联网]
  - 原因：<工具不可用 / 信息不足 / 超出取证路线>
  - 处理要求：<补充前置检查 / 人工确认 / 缩小范围 / 接受风险>

### 修复方案汇总
按修复落点分组（前置检查 / 执行步骤 / 回滚方案 / 风险清单）：
- 在「执行步骤 #2」前增加：<...>
- 在「回滚方案」中补充：<...>
- ...
```

上方 `HIGH-candidate`、`normal`、`[联网]`、`[源码]` 都只是示例值。每个审查项标题中的风险提示必须来自 `_run.md` checklist 的 `risk_hint`，只能写 `HIGH-candidate` 或 `normal`；每条发现的路线标签必须写实际来源路线，只能写 `[联网]`、`[源码]` 或 `[双路线]`，不得保留 `HIGH-candidate/normal` 或 `[联网/源码]` 这类斜杠枚举占位。

综合审查报告不得保留任何尖括号占位符或省略号占位，例如 `<plan 主题>`、`<问题描述>`、`<具体修改>`、`<...>`、`...`。无法确认的内容必须进入“无法验证项”并说明处理要求，不得用模板占位代替。

---

## 来源取证路线标注规则

| 标注 | 含义 |
|------|------|
| `[联网]` | 联网取证路线发现 |
| `[源码]` | 本地源码取证路线发现 |
| `[双路线]` | 联网和源码两条取证路线都发现的同一问题 |
| `CONFLICT` | 两条取证路线对同一审查项给出矛盾结论 |

---

## 展示给用户后的交互

报告输出完毕后，按结果分支：

- 若按 R3 聚合后的审查项结果没有任何 `FAIL` 或 `UNVERIFIABLE`（即所有审查项都进入“通过项总览”），说明所有相关取证路线均为 PASS；告知用户 plan 已通过重型审查、无需 inline 修复，任务结束。
- 若存在任何 `FAIL` 或 `UNVERIFIABLE`，询问用户：

> 以上是审查结果与修复方案。请问：
> 1. **修复方案合理** → 我将把修复 inline 改进 deployment-plan.md
> 2. **修复方案不合理** → 请告诉我哪里有问题或想着重审查哪个方向，我们用新的 review_run_id 重新审查

若用户选择修复方案不合理，main agent 必须把用户关注点写入新一轮 prompt 的“用户当前关注点”段，回到 R2 重新取证，并使用新的 `review_run_id`；上一轮 `review/` 报告只能作为旧轮残留处理，不得与新一轮报告混合综合。
