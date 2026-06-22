# 联网 Review Subagent 专项强化

加载此文件前，先加载 `review-loop-core.md`。本文件是联网取证路线的 3 个专项强化，叠加在 6+3 基础上。

## 工具

Read（仅限读取 heavy-review reference 文件）+ 当前宿主内置 WebSearch / WebFetch 等价工具 + Write（仅限输出契约指定的 review 报告文件）

---

## 专项强化 4：4 类查询（审查专属查询类型）

对每个属于联网取证路线的 checklist item，从以下 4 类查询类型中选择与 item 直接相关的查询；HIGH-candidate 和关键外部依赖优先覆盖，normal item 只做必要查询，避免预算被低风险项耗尽。

1. **版本号验证**：plan 引用的工具/SDK 版本是否还存在、是否受支持、是否已 EOL；只有当 plan 声称“最新”时才验证是否 latest
2. **API deprecation**：plan 调用的 API 是否被官方标记为 deprecated / breaking change
3. **已知坑 / 已知 bug**：plan 用法是否撞到该工具的已知 issue（查 GitHub Issues / changelog）
4. **行为正确性**：plan 假设的工具行为是否与官方文档当前版本一致

**必须新增的反向词扫描**：对每个 plan 操作动词（如"删除 X"、"重启 Y"、"修改 Z 配置"），加上反向词搜索：
```
工具名或操作 deprecated / breaking change / data loss / known issue / CVE / regression
```
实际查询时必须把 `工具名或操作` 替换为 plan 中真实工具名、API 名、命令或操作动词，不得按字面搜索模板文字或尖括号占位。

**引用溯源规则（审查独有）**：plan 中所有外部公开 URL / 第三方工具版本号 / 公开 API 名 / 公开 CLI flag 都视为"公开引用"，每个公开引用必须能通过当前宿主内置 web search 命中或 web fetch 直连公开官方/权威来源验证。在联网工具可用、且已实际尝试 web search / web fetch 后仍无法通过任一路径验证时，标记 `MISSING`（本身即 FAIL 发现项）。若联网工具不可用、被阻断或超出路线能力，标记 `UNVERIFIABLE`，不得伪装成 `MISSING`。

本地私有路径、内网 URL、仓库内脚本参数、用户自定义命令、尚未公开的项目内部接口不适用 WebSearch 命中规则；这些应交给源码取证路线或标为 UNVERIFIABLE。

---

## 专项强化 5：三路并行查询扩展

对 HIGH-candidate 或关键外部依赖 item，同时发出 3 个查询变体并行执行：

1. **关键词查询**：直接提取 plan 中的工具名 / API 名 / 版本号
2. **HyDE 变体**：写一段"假设性失败模式"或"假设性 changelog"作为检索输入
   - 例：验证"rsync 3.2.7 支持 X"→ HyDE 文档写"rsync 3.2.7 release notes mentioning X"
   - 注意：HyDE 必须与关键词 + 分解三路并行，不能单独使用（避免知识泄漏拉远召回）
3. **分解变体**：拆"工具名 + 版本号 + 关键功能/限制"

合并本 item 实际发出的查询变体结果，去重后进入提取步骤。

对 normal item，默认先发关键词查询；只有结果不足、疑似冲突或涉及版本/API 变更时，才补 HyDE 或分解变体。预算不得被低风险 item 的三路查询耗尽。

---

## 专项强化 6：来源优先级 + Wide → Deep 双模式

**来源优先级**（审查场景特有排序）：
官方 changelog/release notes/security advisory > 项目 issue tracker（优先 closed/resolved）> 官方主文档 > 知名技术博客 > 社区论坛

**来源三角验证**：每条关键结论必须满足：
- ≥2 个独立来源印证 → `confirmed`
- 仅 1 个来源 → `unverified`
- 多个来源矛盾 → `CONFLICT`（两种说法都保留，不自行裁决）
- 来源日期 > 12 个月 → `STALE`（时效敏感场景需重查）
- 联网工具可用且已实际尝试 web search / web fetch 后，plan 引用的公开资源仍无法在官方或权威来源验证 → `MISSING`
- 联网工具不可用、被阻断或超出路线能力 → `UNVERIFIABLE`

**反对声音强制查询**：每个 plan 关键决策必须尝试找至少 1 条反对/质疑来源。若未找到，记录查询词和结果为空；不得把“未找到反对声音”直接当作 PASS。

**Wide → Deep 双模式**：
- **Wide 阶段**：覆盖官方文档 + GitHub release notes + GitHub issues + 知名技术博客
- **Deep 切换条件**（命中以下任一即必须 WebFetch 完整页）：
  - 命中官方 changelog / migration guide → 必须读完整页（避免漏掉 breaking changes）
  - 命中 GitHub issue 标题含 plan 关键词 → 必须读完整 thread（确认 open/closed 状态 + 最新 comment）
  - 命中 deprecation 公告 → 必须读完整页（核对生效日期）

---

## 注意事项

- plan 中的"具体值"（版本/命令/URL）= 联网验证靶子；抽象表述（"使用合适的工具"）= 源码取证路线判定
- 时效性敏感的 item（版本号、API 变更）优先查最近 12 个月的内容
- 不引用无法验证来源的内容（无日期页面、匿名论坛）
