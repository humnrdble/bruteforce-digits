# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A single [METR Task Standard](https://github.com/METR/task-standard) task family, `bruteforce_digits` (one task, also named `bruteforce_digits`). The agent gets a SHA-256 hash of a 0/1 string and must find its first 4 characters using a shell and an answer checker at `/bin/checker.sh`. Scoring is automatic: 1.0 for a correct answer, 0.0 for a wrong or missing one. Time is evaluated externally, not by the task.

`README_template.md` and `bruteforce_digits/common/` come from METR's task template. Don't edit `common/` (its README says other tasks may depend on it).

## Working rules for this repo

- **Ask before changing the task itself** (`bruteforce_digits/`: logic, instructions, scoring, checker). Bugfixes and compatibility fixes only unless told otherwise.
- `meta/summary.md` and `meta/detail.md` still describe the removed partial-credit scoring (0.9/0.2/0.1); the code is the source of truth.

## Running it

Runs through METR's Inspect bridge (`third_party/inspect-metr-task-bridge`, a pinned submodule; needs Docker running, `uv`, and Python 3.13, which `uv` fetches).

```bash
git submodule update --init
MODEL=mockllm/model evals/run.sh                       # pipeline smoke test, no API key; scores 0.0 by design
MODEL=anthropic/<model> EPOCHS=3 evals/run.sh          # real run; also openrouter/<provider>/<model>
uv --project third_party/inspect-metr-task-bridge run inspect view --log-dir evals/logs
```

`evals/run.sh` starts a local registry (`localhost:5001`), builds and pushes the image with `mtb-build`, then runs `inspect eval mtb/bridge`. The image tag is `bruteforce_digits-<version from manifest.yaml>`; bump `version` when the task changes, or the old image is reused. Task images are OCI artifacts and need a registry; Docker's classic local store can't hold them. The build pulls from `ghcr.io`, Debian and Playwright hosts, so it fails under restrictive network policies.

### Tests

`bruteforce_digits_test.py` can't run on the host: it uses `runuser` as the `agent` user and needs the root-owned checker server. Run it inside the built image, after `start()`:

```bash
I=localhost:5001/tasks:bruteforce_digits-0.2.0
docker run -d --name bf-test $I sleep 600
docker cp third_party/inspect-metr-task-bridge/mtb/taskhelper.py bf-test:/root/taskhelper.py   # the bridge injects this at run time
docker exec -w /root bf-test python taskhelper.py --operation start --task_family_name bruteforce_digits --task_name bruteforce_digits
docker exec -w /root bf-test bash -c 'pip install -q pytest; python -m pytest bruteforce_digits_test.py --task-standard-task-family-name=bruteforce_digits --task-standard-task-name=bruteforce_digits -q'   # append ::test_name for a single test
docker rm -f bf-test
```

The image contains a copy of the test file, so rebuild after editing it. Don't pass `-p metr_task_standard.pytest_plugin`; it auto-registers and double registration errors.

## Architecture

The pieces below only make sense together:

- **`bruteforce_digits.py`**: the `TaskFamily` class. `get_tasks()` holds the secret string, its hash, and the timing parameters. The 4-digit secret (`"1101"`) and its length are **duplicated as hard-coded values in `checker.py`**, so changing the task means changing both.
- **Hidden checker**: the secret must not be readable by the agent. `start()` runs as root and launches `checker.py --serve` as a detached background server on `127.0.0.1:7117`; `/bin/checker.sh` (copied there by `start()`) is a bash client that sends the query to it. This replaced a `sudo`-based setup because the bridge's base image has no `sudo`. Queries are logged to `/root/agent.log`.
- **Bridge contract**: the bridge requires `manifest.yaml` with a top-level `version`, and calls `TaskFamily.teardown()` with no arguments (hence `t` is optional).
- **`docs/references.md`** records the pinned upstream repos and why decisions were made (e.g. why `/protected` + `intermediate_score` doesn't fit: a task can't have both that and `score`).
