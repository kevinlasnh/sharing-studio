# 联网 Review Subagent 专项强化

加载此文件前，先加载 `review-loop-core.md`。本文件是联网维度的 3 个专项强化，叠加在 6+3 基础上。

## 工具

WebSearch + WebFetch

---

## 专项强化 4：4 类查询（审查专属查询类型）

对每个属于联网维度的 checklist item，按以下 4 类查询类型执行：

1. **版本号验证**：plan 引用的工具/SDK 版本是否还存在、是否最新、是否已 EOL
2. **API deprecation**：plan 调用的 API 是否被官方标记为 deprecated / breaking change
3. **已知坑 / 已知 bug**：plan 用法是否撞到该工具的已知 issue（查 GitHub Issues / changelog）
4. **行为正确性**：plan 假设的工具行为是否与官方文档当前版本一致

**必须新增的反向词扫描**：对每个 plan 操作动词（如"删除 X"、"重启 Y"、"修改 Z 配置"），加上反向词搜索：
```
<工具名/操作> deprecated / breaking change / data loss / known issue / CVE / regression
```

**引用溯源规则（审查独有）**：plan 中所有 URL / 版本号 / API 名 / CLI flag 都视为"引用"，每个引用必须 ≥1 个 WebSearch 命中。无命中即标记 `MISSING`（本身即 FAIL 发现项）。

---

## 专项强化 5：三路并行查询扩展

对每个叶节点 item，同时发出 3 个查询变体，并行执行：

1. **关键词查询**：直接提取 plan 中的工具名 / API 名 / 版本号
2. **HyDE 变体**：写一段"假设性失败模式"或"假设性 changelog"作为检索输入
   - 例：验证"PSScriptAnalyzer v1.21 支持 X"→ HyDE 文档写"PSScriptAnalyzer 1.21 release notes mentioning X"
   - 注意：HyDE 必须与关键词 + 分解三路并行，不能单独使用（避免知识泄漏拉远召回）
3. **分解变体**：拆"工具名 + 版本号 + 关键功能/限制"

合并 3 个变体的结果，去重后进入提取步骤。

---

## 专项强化 6：来源优先级 + Wide → Deep 双模式

**来源优先级**（审查场景特有排序）：
官方 changelog/release notes/security advisory > 项目 issue tracker（优先 closed/resolved）> 官方主文档 > 知名技术博客 > 社区论坛

**来源三角验证**：每条关键结论必须满足：
- ≥2 个独立来源印证 → `confirmed`
- 仅 1 个来源 → `unverified`
- 多个来源矛盾 → `⚠️ CONFLICT`（两种说法都保留，不自行裁决）
- 来源日期 > 12 个月 → `STALE`（时效敏感场景需重查）
- plan 引用的资源在官方处找不到 → `MISSING`

**反对声音强制查询**：每个 plan 关键决策必须找至少 1 条反对/质疑来源。只引用支持性来源等于零审查。

**Wide → Deep 双模式**：
- **Wide 阶段**：覆盖官方文档 + GitHub release notes + GitHub issues + 知名技术博客
- **Deep 切换条件**（命中以下任一即必须 WebFetch 完整页）：
  - 命中官方 changelog / migration guide → 必须读完整页（避免漏掉 breaking changes）
  - 命中 GitHub issue 标题含 plan 关键词 → 必须读完整 thread（确认 open/closed 状态 + 最新 comment）
  - 命中 deprecation 公告 → 必须读完整页（核对生效日期）

---

## 注意事项

- plan 中的"具体值"（版本/命令/URL）= 联网验证靶子；抽象表述（"使用合适的工具"）= 源码维度判定
- 时效性敏感的 item（版本号、API 变更）优先查最近 12 个月的内容
- 不引用无法验证来源的内容（无日期页面、匿名论坛）
