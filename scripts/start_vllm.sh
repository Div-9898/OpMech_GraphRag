#!/bin/bash
# Start vLLM server with Qwen2.5-7B-Instruct

MODEL="${1:-Qwen/Qwen2.5-7B-Instruct}"
PORT="${2:-8000}"

echo "Starting vLLM server with model: $MODEL"
echo "Port: $PORT"

cd /home/divyansh/AIF_FInal_Project
source .venv/bin/activate

python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --port "$PORT" \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.85 \
    --max-model-len 4096 \
    --trust-remote-code
