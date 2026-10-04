# References (researched 2026-10-04)

Upstream code is not copied into this repo. The bridge is a submodule; the others are only read for reference
(`git clone` them into a git-ignored folder if you want the source).

| Repo | Pinned commit | Role |
|---|---|---|
| [METR/inspect-metr-task-bridge](https://github.com/METR/inspect-metr-task-bridge) | `20a430c` (2026-04-16), submodule in `third_party/` | Runs Task Standard tasks in Inspect |
| [METR/task-standard](https://github.com/METR/task-standard) | `03236e9` (2025-02-03), the version the bridge pins | The standard (`STANDARD.md`) |
| [METR/public-tasks](https://github.com/METR/public-tasks) | `5418666` (2026-06-10) | Example tasks; see `hypothesis_testing` |
| [METR/vivaria](https://github.com/METR/vivaria) | n/a | Older runner; METR is moving to Inspect |

Docs: [Inspect](https://inspect.aisi.org.uk/), [bridge README](https://github.com/METR/inspect-metr-task-bridge#readme).

## Findings

- **Bridge requirements:** the task family needs a `manifest.yaml` with a top-level `version` and a `tasks` key.
  Images are tagged `<family>-<version>` and must be pushed to a registry (local registry is fine).
- **No `sudo` in task images.** The bridge's base image does not install it.
- **Hidden checker pattern (METR `hypothesis_testing`):** the secret lives under `/root`, and `TaskFamily.start()`
  (running as root) launches a server on localhost; the agent queries it via `curl`. This task does the same:
  `checker.py --serve` is started by `start()`, and `/bin/checker.sh` forwards queries to it.
- **`/protected` + `intermediate_score()`** exists in the bridge image, but a task may not implement both `score` and
  `intermediate_score`, so it does not fit this task.
- `inspect eval` flags used: `--model`, `--epochs`, `--time-limit`, `--sample-id`, `--log-dir`.
