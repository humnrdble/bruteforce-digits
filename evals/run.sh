#!/bin/bash
# Builds the task image into a local registry and runs the task through METR's Inspect bridge.
#
# Usage: MODEL=anthropic/<model> [EPOCHS=3] evals/run.sh
# API keys (e.g. ANTHROPIC_API_KEY) can be put in evals/.env, see evals/.env.example.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f evals/.env ]; then set -a; . evals/.env; set +a; fi
: "${MODEL:?set MODEL, e.g. MODEL=anthropic/<model-name> (or mockllm/model for a pipeline smoke test)}"
EPOCHS=${EPOCHS:-1}
REGISTRY=${REGISTRY:-localhost:5001/tasks}
TASK_DIR=bruteforce_digits
VERSION=$(awk '/^version:/ {print $2}' "$TASK_DIR/manifest.yaml")
BRIDGE=third_party/inspect-metr-task-bridge

if [ ! -f "$BRIDGE/pyproject.toml" ]; then
    git submodule update --init "$BRIDGE"
fi
uv --project "$BRIDGE" sync --quiet

# Task images are OCI artifacts, which Docker's classic local image store cannot hold: use a registry.
if ! docker ps --format '{{.Names}}' | grep -qx task-registry; then
    docker rm -f task-registry >/dev/null 2>&1 || true
    docker run -d --restart=always -p 127.0.0.1:5001:5000 --name task-registry registry:3 >/dev/null
fi

uv --project "$BRIDGE" run mtb-build --platform linux/amd64 --push -r "$REGISTRY" "./$TASK_DIR"

export INSPECT_METR_TASK_BRIDGE_REPOSITORY="$REGISTRY"
uv --project "$BRIDGE" run inspect eval mtb/bridge \
    -T "image_tag=${TASK_DIR}-${VERSION}" \
    --sample-id "$TASK_DIR" \
    --model "$MODEL" \
    --epochs "$EPOCHS" \
    --working-limit "${WORKING_LIMIT:-600}" \
    --log-dir evals/logs
