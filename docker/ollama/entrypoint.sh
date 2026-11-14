#!/bin/sh
set -e

# ==============================================================================
# Auto-provisioning Entrypoint for Dockerized Ollama
# 1. Starts the Ollama daemon in the background
# 2. Waits for health readiness on port 11434
# 3. Pulls required chat and embedding models on first launch (Zero-API-key reviewer requirement)
# 4. Hands over control to keep the daemon running
# ==============================================================================

echo ">>> [Ollama Entrypoint] Starting Ollama server in background..."
/bin/ollama serve &
PID=$!

echo ">>> [Ollama Entrypoint] Waiting for Ollama daemon to listen on port 11434..."
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done
echo ">>> [Ollama Entrypoint] Ollama daemon is ready!"

CHAT_MODEL="${OLLAMA_CHAT_MODEL:-qwen2.5:1.5b}"
EMBED_MODEL="${OLLAMA_EMBED_MODEL:-nomic-embed-text}"

echo ">>> [Ollama Entrypoint] Checking and pulling chat model: ${CHAT_MODEL}..."
ollama pull "${CHAT_MODEL}"

echo ">>> [Ollama Entrypoint] Checking and pulling embedding model: ${EMBED_MODEL}..."
ollama pull "${EMBED_MODEL}"

echo ">>> [Ollama Entrypoint] All models ready! Ollama container is healthy and serving."

# Wait for background process to keep container running
wait $PID
