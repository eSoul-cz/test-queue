---
name: test-queue
description: Use when installing or tuning the shared test queue (`testq`) or its macOS menu bar widget, when tests time out because several agent sessions run suites together, when command output contains `[testq]`, or when the user asks about machine load or swap. Queues test suites, E2E, mutation runs and builds across parallel agent sessions on one machine; ships a Claude Code hook that queues test commands.
---

# Test queue

`testq` is one queue for all agent sessions on the machine. It lets cheap checks run at once, admits test suites and builds in a limited number, runs E2E and mutation testing one at a time, and starts nothing new while memory is short.

Read [references/setup.md](references/setup.md) when installing, updating or tuning the queue or widget, or when the user asks why it exists. It holds the motivation, the parts table, install steps, tuning and the CLI cheat sheet (`testq status`, `doctor`, `history`, `config`, `stop`). Installing changes global user configuration, so do it only when the user asks.

## Working in a session with the queue

- **Keep the `testq run` prefix the hook adds.** The hook rewrites commands like
  `docker compose exec app php artisan test` into
  `~/.local/bin/testq run -c medium -- docker compose exec app php artisan test`.
  Set `TESTQ_BYPASS=1` only when the user asks.
- Run full suites, E2E and mutation tests in the background (in Claude Code:
  `run_in_background`), because time spent waiting in the queue counts towards the Bash tool
  timeout otherwise. Wait for the completion notification instead of polling with `sleep`.
  When the harness offers subagents, a test runner subagent can hold the wait so the main
  session keeps its context.
- Prefer targeted runs: a single test file or `--filter` is `light` and does not wait.
- `[testq] waiting (...)` on stderr is queue state. `testq status` shows what the job waits
  for, so wait for the job to finish instead of starting the same suite again.
- The exit code is the command's own. `143` means someone stopped the run from the widget
  or with `testq stop`.

## Classes

`light` (lint, static analysis, a single test file, `--filter`), `medium` (full suites, builds) and `heavy` (Playwright, Infection, Dusk, Cypress, Stryker, scripts named `*e2e*` or `*mutat*`). `testq rewrite '<cmd>'` shows the decision for a command; `testq config` shows the limits, weights and budget in effect. Detection rules, ordering and how to extend them: [references/classification.md](references/classification.md).

## Limits

- The hook only covers Claude Code. Other harnesses (Codex and others) must call
  `testq run -c <class> -- <cmd>` themselves. Add the snippet from
  [references/configuration.md](references/configuration.md#other-agents) to the agent's
  instructions.
- Claude Code checks permissions on the **rewritten** command. A rule such as
  `Bash(pnpm test:*)` does not match `~/.local/bin/testq run -c medium -- pnpm test`, so
  such a command asks for approval again.
- Stopping a `docker compose exec` job ends the client. The process inside the container
  may finish on its own.
- Tests of the tool itself: `python3 -m unittest discover -s skills/test-queue/scripts -p 'test_*.py'` from the repository root, or `-s "$SKILL_DIR/scripts"` from the installed skill.
