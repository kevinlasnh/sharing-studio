# Review Framework — 审查领域知识

main agent 在 R2.1 读取本文件；subagent 不直接读取。目标是把 plan snapshot 中的声明变成可机械绑定的 checklist，而不是复制不可信 Markdown 到父契约控制字段。

## 七元组 checklist

每项必须包含：

```
(statement_summary, statement_sha256, plan_locator,
 evidence_route, risk_dimensions, risk_hint, evidence_freshness)
```

生成规则：

1. 从 `review/plan-snapshot.md` 按章节逐条枚举真实声明。
2. `statement_summary` 只做 1-240 字符安全单行描述，不以 Markdown heading 或 `- field:` 开头。
3. 真实声明使用 `plan_locator: lines N-M`；hash 为这些行保留原换行后的精确 bytes。缺失章节、H1/章节重复等结构问题、provenance/source 状态使用 Skill 规定的 `synthetic:missing-section:*` / `synthetic:plan-structure:*` / `synthetic:provenance:*` / `synthetic:source-snapshot:*`，hash 为 locator UTF-8 bytes。
4. 用 `hash-plan-locator.py` 计算 hash。
5. 标注路线、风险维度、风险提示和证据时效性。
6. 编号必须从 #1 连续递增且唯一；至少一项。

## 路线判定

- 版本、API、URL、公开兼容性、弃用/安全公告：`联网`
- 当前文件路径、调用链、命令与仓库状态、备份/回滚对账、plan 跨章节：`源码`
- 同时依赖公开事实和当前本地实现：`都需要`
- Research provenance 非 confirmed：增加源码路线 synthetic item，审查 plan 是否把来源不明内容误当事实。
- source snapshot unverifiable：增加源码路线 synthetic item，并让所有依赖当前本地状态的 item 无法 PASS。
- plan H1 缺失/重复、必需章节缺失/重复：为每个结构问题增加 validator 指定的源码路线 `HIGH-candidate` synthetic item；不能用一个笼统 item 合并多个 mandatory locator。

## 六个风险维度

| 维度 | 主要问题 |
|------|----------|
| 权限 | 是否声明真实权限层级、遵守最小权限、区分本地/共享/生产权限？ |
| 回滚 | 是否有触发条件、逐步回滚、不可逆步骤的替代补救？ |
| 数据影响 | 哪些文件/数据/外部状态变化，是否需备份，是否混淆配置/缓存/用户数据？ |
| 依赖 | 版本、服务、API、迁移前提、上下游约束是否明确？ |
| 顺序 | 是否存在强依赖、并发冲突、先删后备份等逆序？ |
| 跨章节一致性 | 摘要、关键缺口、步骤、回滚、风险是否互相覆盖且无漂移？ |

关键缺口不会因“用户接受风险”而消失；接受只允许把风险变成明确限制、前置检查、人工确认或降级步骤。

## 风险提示

- `HIGH-candidate`：不可逆、可能数据丢失、生产/共享基础设施、Admin/root/生产凭据、强制覆盖历史或跨边界广泛影响。
- `normal`：未命中以上特征。

风险提示只决定证据深度，不等于最终 severity。

## 严重度（三轴取最大）

| 轴 | LOW | MED | HIGH |
|----|-----|-----|------|
| 可逆性 | 易撤销的文档/单文件编辑 | 需要备份还原、迁移或停机窗口 | 不可逆删除、强制覆盖历史、可能永久数据丢失 |
| 范围 | 单文件/单模块/单仓本地 | 多模块、多仓但隔离、共享开发环境 | 生产、共享基础设施、广泛跨仓或外部用户影响 |
| 权限 | 普通本地用户 | 共享 CI/服务账户 | Admin/root/生产凭据 |

- 任一轴 HIGH → HIGH。
- 无 HIGH、至少一轴 MED → MED。
- 三轴 LOW → LOW。

Git push 不能一概判 HIGH：普通可恢复分支 push 依据范围和保护策略判断；force push、覆盖受保护历史、发布敏感内容或影响生产才可能 HIGH。跨仓也不是个人目录层级的硬编码；按目标仓库和真实共享边界判断。

## 证据等级到结论的映射

| 证据等级 | 可支撑的明细状态 |
|----------|------------------|
| `confirmed` | PASS；或有直接反证时 FAIL |
| `CONFLICT` | FAIL：plan 不能把矛盾事实当确定前提，修复为补证/分支/人工闸门 |
| `MISSING` | FAIL：plan 声称必须存在的资源/路径/备份/公开锚点不存在 |
| `unverified` | UNVERIFIABLE，不得 PASS |
| `STALE` | 时效敏感项为 UNVERIFIABLE，需刷新证据 |

整项路线结论固定 `FAIL > UNVERIFIABLE > PASS`。PASS 必须至少有一条真实 confirmed 明细；FAIL 必须有证据和落到 plan 的修复；UNVERIFIABLE 必须写真实原因和处理要求。

## 仓库策略边界

是否允许提交/push 某路径，按以下顺序判断：

1. 当前仓库已加载的 Agent Markdown 与用户当前授权。
2. `.gitignore`、Git tracked 状态、远端/分支保护策略。
3. 文件是否含秘密、私有数据、本机绝对路径或不应公开的运行产物。

公共 Skill 不得硬编码“所有 PWF/隐藏目录不得 push”或个人 Second Brain 层级。明确的仓库规则优先；没有规则且影响重大时标记 UNVERIFIABLE 并要求确认。
