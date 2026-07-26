# 源码 Review 路线

先加载 `review-loop-core.md`。

## 只读边界

允许 Grep、Read、Glob，以及参数已验证不会越过当前授权仓库根、不会写缓存/锁/构建产物/外部状态的只读命令。常见允许项：

- `test -e/-f/-d`、`stat`
- 边界受控的 `find`
- `git ls-files`、`git --no-optional-locks status --short`、`git diff --check`
- `sha256sum`
- `bash -n`（只解析文件或 stdin）
- Python `compile()` 内存语法检查
- 工具官方保证无写入的 `--check` / `--validate` / `--dry-run`

命令名在白名单内不代表任意参数都安全。路径参数、`-exec`、输出选项、配置加载、插件和环境变量都必须检查；任何可能越界或写状态的组合改为静态证据或 UNVERIFIABLE。

## source snapshot 闸门

snapshot 对当前 Git worktree 的 HEAD、porcelain v2 状态、tracked 与未忽略 untracked 路径的内容、受支持文件类型和可执行位做长度分帧绑定；clean submodule 还必须绑定 index gitlink 与实际 HEAD。dirty / 缺失 / 无法检查的 submodule，以及任何 Git-visible FIFO/socket/device、非 submodule 目录或其他特殊节点，都会使 snapshot 降级为 unverifiable。不要把单独的 `git status`、文件名列表或内容 hash 当作完整 snapshot。

`_run.md.source_snapshot_status` 非 confirmed 时：

- synthetic source-snapshot item 必须 FAIL 或 UNVERIFIABLE，说明当前源码状态无法稳定绑定。
- 所有依赖当前本地实现的 item 不能 PASS。
- 只依赖 plan 自身跨章节一致性的 item 仍可审查，但证据必须明确来自 plan snapshot，而不是当前源码。

## 路径与操作语义

从 plan 每个路径/命令出发，先判定 create / modify / delete / move / backup / restore / unknown：

- create：目标不存在通常是预期；已存在且会冲突 → CONFLICT/FAIL。
- modify/delete/backup：目标应存在；不存在 → MISSING/FAIL。
- move：源应存在，目标不应冲突。
- restore：输入必须能唯一追溯到 backup 产物；无法唯一确定 → UNVERIFIABLE，对不上 → FAIL。
- unknown：不猜测，写 UNVERIFIABLE。

对目标符号双向追踪 callers/callees，默认最多 2 层；HIGH-candidate 可再深入 1 层。plan 提到的所有路径都要做存在性验证；需要存在的目标才要求 Read。

## 三类专项检查

1. 静态语法：Bash 用 `bash -n`；inline 片段只经 stdin；Python 用内存 `compile()`；配置用只读解析器。无法无写入解析则 UNVERIFIABLE。
2. 安全 dry-run：仅在确认不会写缓存、锁、构建物或外部状态后运行；结果与 plan 不符 → confirmed/FAIL。
3. backup/restore 对账：产物名、路径、时间戳和恢复输入必须一致；不一致 → confirmed/FAIL。

## plan 自身一致性

- 调研摘要/关键缺口是否落到前置检查、步骤或风险。
- 每个不可逆步骤是否有回滚或真实替代补救。
- 执行步骤影响范围是否被风险清单覆盖。
- 步骤依赖和顺序是否自洽、可幂等重试。

## Git/PWF/隐藏目录

不要硬编码“某类文件永远不能 push”。读取当前仓库 Agent Markdown、`.gitignore`、tracked 状态和用户授权：

- 明确要求跟踪且无敏感内容 → 可按仓库 policy 判定。
- 含凭据、私有数据、本机绝对路径或未授权运行产物 → FAIL。
- 规则缺失且影响重大 → UNVERIFIABLE，要求确认。
- force push、受保护历史覆盖、生产发布按真实可逆性/范围/权限定 severity；普通分支 push 不自动 HIGH。

## 证据等级

- 直接读到/解析/dry-run 证据：confirmed。
- 只有文件名、grep 命中或间接推断：unverified → UNVERIFIABLE。
- 本地证据互相冲突或与 plan 断言冲突：CONFLICT → FAIL。
- 必须存在的对象缺失：MISSING → FAIL。
