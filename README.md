# LLM Stack — Ollama + AnythingLLM

A simple, modular Docker Compose setup. No custom images to build or maintain.

## Directory structure

```
llm-stack/
├── docker-compose.yml
├── .env                          # shared config (ports, URLs)
├── manage.sh                     # helper script
├── anythingllm/
│   └── .env                      # AnythingLLM-specific overrides
└── ollama/
    └── modelfiles/               # ← your custom Modelfiles live here
        └── my-assistant.Modelfile
```

## Quick start

```bash
chmod +x manage.sh
./manage.sh up          # start everything
./manage.sh pull llama3 # download a base model
```

## Custom Ollama models (no rebuild!)

1. **Create / edit** a Modelfile in `ollama/modelfiles/`:

   ```
   FROM llama3
   PARAMETER temperature 0.5
   SYSTEM "You are a pirate assistant. Respond in pirate speak."
   ```

2. **Build it** (one command):

   ```bash
   ./manage.sh create my-assistant
   # or directly:
   docker exec ollama ollama create my-assistant -f /modelfiles/my-assistant.Modelfile
   ```

3. **Use it** — select `my-assistant` in AnythingLLM or call the API:

   ```bash
   curl http://localhost:11434/api/generate -d '{"model":"my-assistant","prompt":"hello"}'
   ```

Repeat steps 1-2 any time you want to tweak the model. No image rebuild needed.

## Key improvements over the original

| Before | After |
|---|---|
| Custom images (`my-ollama`, `my-allm`) that need rebuilding | Upstream images — nothing to build |
| Hard-coded host paths (`/data/...`) | Named Docker volumes (portable) |
| `localhost` for inter-container comms (breaks without `network_mode: host`) | Service name `ollama` via Docker DNS |
| Config baked into compose file | `.env` files for easy tuning |
| Manual `docker exec` commands | `manage.sh` helper script |

## GPU support

Uncomment the `deploy` block in `docker-compose.yml` under the `ollama` service to enable NVIDIA GPU passthrough.
