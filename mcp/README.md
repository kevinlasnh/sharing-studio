# Basic Memory MCP Example

This is a sanitized project-level MCP snippet for the L2 Second Brain vault.

Use it as a template only. Keep real local paths and provider credentials outside the public repository.

```powershell
basic-memory project add second-brain "<vault-path>" --default --local
```

The vault router requires agents to pass `project: second-brain` explicitly for Basic Memory MCP calls and to use `--project second-brain` for CLI fallback.