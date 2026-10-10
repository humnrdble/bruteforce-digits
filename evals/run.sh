#!/bin/bash
# Builds the task image into a local registry and runs the task through METR's Inspect bridge.
#
# Usage: MODEL=anthropic/<model> [EPOCHS=3] [MODEL_ARGS='provider={"max_price":{"prompt":50,"completion":50}}'] evals/run.sh
# API keys (e.g. ANTHROPIC_API_KEY) can be put in evals/.env, see evals/.env.example.
#
# MODEL_ARGS is passed to inspect as -M. With openrouter/ models, `provider={"max_price":{...}}` caps the
# price per million tokens (USD): OpenRouter only routes to providers at or below both ceilings, and the request
# fails with a 404 ("No endpoints found that satisfy the max price") if none qualifies, instead of falling
# back to a pricier provider. It limits the per-token price only, not total spend; use a credit limit on the
# OpenRouter API key for that.
# Inspect's basic_agent silently caps samples at 50 messages unless a message or token limit is given, so a very
# large --message-limit is passed to leave the working limit as the only bound.
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
    ${MODEL_ARGS:+-M "$MODEL_ARGS"} \
    --epochs "$EPOCHS" \
    --message-limit "${MESSAGE_LIMIT:-100000}" \
    --working-limit "${WORKING_LIMIT:-600}" \
    --log-dir evals/logs
