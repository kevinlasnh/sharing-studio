# Basic Memory MCP 示例

用于将 Basic Memory 接入 Second Brain scaffold 的脱敏项目级 MCP 片段。

<!-- README-I18N:START -->
<p>
  <a href="./README.md">English</a> | <strong>简体中文</strong>
</p>
<!-- README-I18N:END -->

> [!NOTE]
> 这个目录只能作为模板。真实本机路径、project ID、provider 凭据和运行时状态都必须留在公开仓库之外。

## 包含文件

```text
mcp/
├── README.md
└── basic-memory-mcp.example.json
```

## 设置模式

将 vault 注册为本地 Basic Memory project：

```powershell
basic-memory project add second-brain "<vault-path>" --default --local
```

然后把 [`basic-memory-mcp.example.json`](./basic-memory-mcp.example.json) 的结构复制到你的 agent 运行时 MCP 配置中。

## Router 预期

Vault router 要求 agent 在 Basic Memory MCP 调用中显式传入 `project: second-brain`，CLI fallback 则使用 `--project second-brain`。
