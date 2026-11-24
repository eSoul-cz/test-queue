# test-queue

A shared queue for test runs on one machine. Several parallel agent sessions (Claude Code, Codex and others) each start `phpunit`, Playwright, Infection or a build; every tool spawns a worker per core and the laptop ends up swapping. `testq` admits test suites and builds in a limited number, runs E2E and mutation testing one at a time, lets cheap checks (lint, a single test file) run at once, and starts nothing new while memory is short.

The repository holds one [Agent Skill](https://skills.sh) (`test-queue`) and the tool it installs:

| Part | Role |
|---|---|
| `testq` (Python 3.8+, no dependencies) | The queue CLI: `run`, `status`, `doctor`, `history`, `config`, `stop`, `vm` |
| Claude Code hook | PreToolUse `Bash` hook that prefixes test and build commands with `testq run -c <class> --` |
| Menu bar widget (macOS 14+, built with `swiftc`) | Rings for CPU, memory, swap and load; running and waiting jobs with stop buttons; pause and limits; Colima memory with a restart button |

Everything lives in [`skills/test-queue/`](skills/test-queue/): `SKILL.md` and `references/` for the agent, `scripts/` for the tool.

## Install

The skill (agent instructions only):

```sh
npx skills add eSoul-cz/test-queue
```

The CLI, the hook and the widget. From a checkout of this repository, or from the installed skill directory:

```sh
sh skills/test-queue/scripts/install.sh               # CLI + Claude Code hook + widget
sh skills/test-queue/scripts/install.sh --no-widget   # without the menu bar app (always the case on Linux)
sh skills/test-queue/scripts/install.sh --no-hook     # queue only when called as `testq run`
```

The installer copies `testq` to `~/.local/share/testq` and links it as `~/.local/bin/testq`, writes limits tuned to the machine's RAM and cores to `~/.local/state/testq/config.json` (existing values are kept), merges the hook into `~/.claude/settings.json` (backup: `settings.json.bak-testq`) and builds the widget when `swiftc` is available. Re-run it after updating. Only new Claude Code sessions load the hook. Check the result with `testq doctor`.

Other harnesses have no hook: add the snippet from [`references/configuration.md`](skills/test-queue/references/configuration.md#other-agents) to their instructions.

## Uninstall

```sh
sh skills/test-queue/scripts/install.sh --uninstall            # keeps the queue state and history
sh skills/test-queue/scripts/install.sh --uninstall --purge    # also deletes ~/.local/state/testq
```

This removes the CLI, the widget and its LaunchAgent, and only the testq entry in the Claude Code settings.

## Requirements

- Python 3.8 or newer (`python3` on `PATH`)
- Claude Code for the hook
- macOS 14+ with Xcode Command Line Tools (`swiftc`) for the widget; the queue itself also runs on Linux
- Optional: Colima for the VM resize feature (`testq vm`)

## Tests

From the repository root:

```sh
python3 -m unittest discover -s skills/test-queue/scripts -p 'test_*.py'
```

`test_testq.py` covers classification, limits, admission, estimates and runs of the CLI; `test_install.py` runs `install.sh` with `HOME` in a temporary directory against a fixture `settings.json` (hook added once, idempotent re-run, `--no-hook`, `--uninstall`, invalid JSON aborts unchanged). The widget compile is not tested.

## CI

Jenkins runs the `Jenkinsfile`: checkout, then `scripts/test`, which runs the command above with the node's `python3`, or in a `python:3-alpine` container when the node has none.

## Licence

MIT, see [LICENSE](LICENSE).
