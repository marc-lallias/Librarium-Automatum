#!/usr/bin/env bash
set -euo pipefail

# ─── Helper script for the LLM stack ───────────────────────────────────────
# Usage:
#   ./manage.sh up            Start the stack
#   ./manage.sh down          Stop the stack
#   ./manage.sh logs [svc]    Tail logs (optionally for one service)
#   ./manage.sh create <name> Build a custom Ollama model from modelfiles/<name>.Modelfile
#   ./manage.sh list          List models loaded in Ollama
#   ./manage.sh pull <model>  Pull a base model (e.g. llama3, mistral)

CMD="${1:-help}"
shift || true

case "$CMD" in
  up)
    docker compose up -d "$@"
    echo "✅ Stack is running."
    echo "   AnythingLLM → http://localhost:${ALLM_PORT:-3001}"
    echo "   Ollama API  → http://localhost:${OLLAMA_PORT:-11434}"
    ;;
  down)
    docker compose down "$@"
    ;;
  logs)
    docker compose logs -f "$@"
    ;;
  create)
    NAME="${1:?Usage: $0 create <model-name>}"
    FILE="/modelfiles/${NAME}.Modelfile"
    echo "⏳ Creating model '$NAME' from $FILE …"
    docker exec ollama ollama create "$NAME" -f "$FILE"
    echo "✅ Model '$NAME' is ready.  Use it in AnythingLLM or via API."
    ;;
  list)
    docker exec ollama ollama list
    ;;
  pull)
    MODEL="${1:?Usage: $0 pull <model>}"
    docker exec ollama ollama pull "$MODEL"
    ;;
  *)
    echo "Usage: $0 {up|down|logs|create|list|pull}"
    exit 1
    ;;
esac
