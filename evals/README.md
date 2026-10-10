# Running the task

The task is run with [Inspect](https://inspect.aisi.org.uk/) through METR's
[inspect-metr-task-bridge](https://github.com/METR/inspect-metr-task-bridge), which is a git submodule in
`third_party/` (pinned; `uv sync` there installs Inspect and the METR packages it needs).

Requirements: Docker (running), [uv](https://docs.astral.sh/uv/), and an API key for the model you want to run.

```bash
git submodule update --init
cp evals/.env.example evals/.env   # add your key
MODEL=anthropic/<model-name> EPOCHS=3 evals/run.sh
```

`evals/run.sh` starts a local image registry (`localhost:5001`), builds and pushes the task image with `mtb-build`,
and runs `inspect eval mtb/bridge`. Logs go to `evals/logs/`; view them with
`uv --project third_party/inspect-metr-task-bridge run inspect view --log-dir evals/logs`.

`MODEL=mockllm/model` runs the pipeline without a real model (only useful to check that the task starts).
Other knobs: `EPOCHS` (repeats), `WORKING_LIMIT` (working seconds, default 600), `MESSAGE_LIMIT` (default 100000, i.e. effectively none; without a limit Inspect's agent stops at 50 messages), `MODEL_ARGS` (passed as `-M`, e.g. `'provider={"max_price":{"prompt":1,"completion":5}}'` makes OpenRouter reject providers above those $/M-token prices), `REGISTRY`.

Each time `bruteforce_digits/manifest.yaml`'s `version` changes, a new image tag is built.

## Versions

- 0.2.0: binary scoring (1.0 or 0.0), time judged externally. Runs used the bridge's default agent: tool calls time out after 120 s, a timed-out call is retried by Inspect (about 216 s per timeout), the model is not told, and Inspect's 50-message default applies.
- 0.3.0: same task code as 0.2.0, run with `evals/solver.py`: tool descriptions state the timeout and how to run longer jobs, a timed-out call is not retried (about 120 s, run once), and `run.sh` removes the 50-message cap. Runs carry the tag `tool-timeout-note`.
- The first retry of five Anthropic models (2026-10-10) used the 0.3.0 setup under the 0.2.0 image tag, because it started before the bump. The tag `tool-timeout-note` identifies them.
