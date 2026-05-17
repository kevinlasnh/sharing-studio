# gtd-todoist

一个 GTD 脚手架：AI agent 负责推理 Todoist，定时任务只提醒用户启动 review flow。

<p>
  <img alt="GTD" src="https://img.shields.io/badge/method-GTD-0f766e?style=flat-square">
  <img alt="Todoist" src="https://img.shields.io/badge/tool-Todoist-dc2626?style=flat-square">
  <img alt="Reminder only" src="https://img.shields.io/badge/cron-reminder--only-2563eb?style=flat-square">
</p>

<!-- README-I18N:START -->
<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong>
</p>
<!-- README-I18N:END -->

> [!IMPORTANT]
> 这个脚手架里的 cron job 不会修改 Todoist。它们只提醒用户在主聊天 session 中启动 flow，由 agent 提案并等待用户确认。

## 解决什么问题

如果任务标题、标签和日期可以未经审查就被自动改写，Todoist 自动化会很危险。这个脚手架把 agent 保留在主对话中，写操作使用稳定 task ID，并让 cron 只承担提醒层职责。

## 包含内容

```text
gtd-todoist/
├── deployment-plan.md              # Todoist scaffold and cron setup
├── agents-section.md               # router section for an agent workspace
├── skills/
│   ├── gtd-inbox-triage/
│   ├── gtd-daily-review/
│   └── gtd-weekly-review/
└── health-check/
    ├── SKILL.md
    └── scripts/
```

## Skill 清单

| Skill | 目的 |
| :--- | :--- |
| `gtd-inbox-triage` | 澄清 Inbox 条目，并路由到 next action、waiting、project、someday 或 done。 |
| `gtd-daily-review` | 审查今天已完成、未完成、逾期、Inbox 和明天的事项。 |
| `gtd-weekly-review` | 围绕 Get Clear、Get Current、Get Creative 执行 weekly review。 |
| `health-check` | 只读审计 workspace 文件、skill 契约、运行时可见性和只提醒 cron。 |

## 快速开始

1. 阅读 [`deployment-plan.md`](./deployment-plan.md)。
2. 备份当前 Todoist workspace。
3. 创建或核验计划中描述的 projects、labels 和 filters。
4. 将三个 `skills/<name>/SKILL.md` 文件复制到目标 agent workspace。
5. 将 [`agents-section.md`](./agents-section.md) 追加到目标 `AGENTS.md` 或等价 router 文件。
6. 替换 `<TELEGRAM_USER_ID>`、`<BOT_ACCOUNT>` 和 timezone 等占位符。
7. 添加 reminder-only cron jobs。
8. 依赖该设置前先运行 health check。

## 核心规则

- 主聊天 session 拥有执行和用户确认职责。
- Cron reminders 是隔离提示，不是自动化权限。
- Todoist 写操作必须使用稳定 task ID 或 Todoist URL，不能靠任务标题。
- `td task update --labels` 会替换 labels，因此 agent 写入前必须读取并合并现有 labels。
- 破坏性或批量动作需要逐项明确批准。

## 依赖

- Todoist 账号和 API access。
- Todoist CLI，例如 `td`，或具备 project、label、filter、task、completed、upcoming、activity 命令的等价 wrapper。
- 能加载 Markdown 定义 skills 的 agent 运行时。
- 能向主用户 channel 发送提醒的 cron 或 scheduler 层。

## 隐私边界

不要发布：

- Todoist API tokens。
- 真实任务标题、project data、labels、activity logs 或 account IDs。
- 真实 chat delivery IDs、bot accounts、webhook URLs 或 scheduler state。
- 机器专属 hostnames、SSH targets 或 private IP addresses。
