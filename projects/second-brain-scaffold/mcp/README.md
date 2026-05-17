# Basic Memory MCP Example

A sanitized project-level MCP snippet for wiring Basic Memory into the Second Brain scaffold.

<!-- README-I18N:START -->
<p>
  <strong>English</strong> | <a href="./README.zh-CN.md">简体中文</a>
</p>
<!-- README-I18N:END -->

> [!NOTE]
> Use this directory as a template only. Keep real local paths, project IDs, provider credentials, and runtime state outside the public repository.

## Included File

```text
mcp/
├── README.md
└── basic-memory-mcp.example.json
```

## Setup Pattern

Register the vault as a local Basic Memory project:

```powershell
basic-memory project add second-brain "<vault-path>" --default --local
```

Then copy the shape of [`basic-memory-mcp.example.json`](./basic-memory-mcp.example.json) into the MCP configuration for your agent runtime.

## Router Expectation

The vault router expects agents to pass `project: second-brain` explicitly for Basic Memory MCP calls and to use `--project second-brain` for CLI fallback.
