---
name: brv-query
description: Query ByteRover long-term repository memory via the brv CLI. Use when the user says 查询长期记忆 or explicitly requests brv query; keep it read-only and return a concise summary.
---

# BRV Query

## Overview

Use this skill to query ByteRover long-term memory for the current repository. This skill is read-only: it may run `brv query`, but it must not run `brv curate`, edit `.brv/`, or modify PWF files.

## Workflow

1. Confirm the current working directory is the intended repository.
2. Run `brv status` if repository or ByteRover state is unclear.
3. Convert the user's request into one or more concrete natural-language questions.
4. Run `brv query "<question>"` for each question. Use at most 3 questions unless the user asks for a broader sweep.
5. Summarize the relevant hits and explicitly say when no useful memory was found.
6. Stop after reporting results; wait for the user's next instruction before changing code or files.

## Query Quality

ByteRover query works best with concrete questions, not bare keywords.

Good:

```bash
brv query "How is authentication implemented in this repository?"
brv query "What previous decisions exist about the upload pipeline?"
brv query "Where are API rate limits enforced and why?"
```

Avoid:

```bash
brv query "auth"
brv query "show me code"
brv query "memory"
```

If the user gives only a keyword, infer the likely concrete question from the current task and state that inference before querying.

## Output

Report in this shape:

```markdown
长期记忆查询结果：
- 查询：<question>
- 命中：<N 条或未命中>
- 摘要：<与当前任务有关的结论>
- 证据：<ByteRover 返回的节点名、路径或片段；没有则省略>
```

Keep the answer concise. Do not paste long raw `brv` output unless the user asks for it.
