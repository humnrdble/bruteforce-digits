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
Other knobs: `EPOCHS` (repeats), `WORKING_LIMIT` (working seconds, default 600), `MODEL_ARGS` (passed as `-M`, e.g. `'provider={"max_price":{"prompt":1,"completion":5}}'` makes OpenRouter reject providers above those $/M-token prices), `REGISTRY`.

Each time `bruteforce_digits/manifest.yaml`'s `version` changes, a new image tag is built.
