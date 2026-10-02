# chat-api

Standalone `getChatList` / `sendChat` service: its own FastAPI app, its own
SQLAlchemy models, its own Postgres database.

## What it does

Every `/chat/*` route requires an `X-API-Key` header (see Auth below);
`/health` doesn't.

- `GET /chat/{session_id}/list` — full turn-by-turn history for a chat
  session, returned as `{"status": "success", "data": {"messages": [...]}}`.
  Each item in `messages` is returned exactly as it was posted (see below) —
  there's no fixed schema per message, because different `chip` types
  (`destinations`, `plan_choice`, `esim_choice`, `nav_*`, ...) shape the
  object differently (some have `isPopup`, some don't; `chips[].arg` can be
  a string or an object; `deeplink`/`requiresLogin` can live on the message
  or on individual chips).
- `POST /chat/{session_id}/messages` — append one turn to a session. Body is
  the full message object; only `role` (`"assistant"` or `"user"`) is
  validated, everything else is stored verbatim.
- `POST /chat/{session_id}/reply` — free-text send. `{"text": "..."}` in,
  model-generated reply out as `{"status": "success", "data": {"messages":
  [userTurn, assistantTurn]}}`.
- `POST /chat/{session_id}/send` — **sendChat()**, chip-tap send.
  `{"message": "...", "chip": "...", "arg": ...}` in — `message` is the
  chip's display text, `chip`/`arg` are what that chip carried — reply out
  as `{"status": "success", "data": assistantMessage}` (flat, not wrapped
  in a list, since a chip tap replaces the prior turn's chips rather than
  reading as a transcript entry).

`/reply` and `/send` both call a local model (LM Studio primary, Ollama
backups — see `app/llm_client.py`) for structured JSON matching the same
message shape, and both degrade to a `whatsapp_only` fallback message
instead of a 5xx if every local model is unreachable.

`GET`/`POST /messages` have no dialogue engine behind them — nothing there
decides what an assistant message *should* say next; they only persist and
replay turns.

## Auth

One shared secret, not real per-user auth — see `app/auth.py`. Every
`/chat/*` request needs:

```
X-API-Key: <the value of API_KEY in .env>
```

Missing or wrong key → `401`. `/health` is exempt (no key needed).

## Run it

```bash
createdb chat_api   # once, if it doesn't already exist
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root (it is git-ignored):

```bash
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/chat_api

# Required: every /chat/* request must send this as the X-API-Key header.
# Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"
API_KEY=<your-secret>

# Local model servers for POST /chat/{session_id}/reply and /send.
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=lm-studio
LLM_MODEL=google/gemma-4-e4b

LLM_FALLBACK_BASE_URL=http://localhost:11434/v1
LLM_FALLBACK_API_KEY=ollama
LLM_FALLBACK_MODEL=llama3.2

LLM_FALLBACK2_BASE_URL=http://localhost:11434/v1
LLM_FALLBACK2_API_KEY=ollama
LLM_FALLBACK2_MODEL=llama3.2:1b
```

Only `API_KEY` is required; the other values shown are the defaults for local
development (Postgres on localhost, LM Studio primary at `:1234`, Ollama backup
at `:11434`).

```bash
python scripts/migrate.py       # creates chat_messages table
python scripts/seed_demo.py     # optional: seeds session "demo-session-1" with the sample conversation
```

**Start the server** — two options:

```bash
# Plain foreground run, for a quick check:
uvicorn app.main:app --reload --port 8020

# Or the watchdog (recommended while actively developing against this API):
# restarts uvicorn automatically if it ever exits/crashes. Runs as a
# detached Terminal background process, NOT a launchd service — launchd
# agents get denied read access to ~/Documents on this Mac unless their
# binary is manually added to Full Disk Access, so this sidesteps that.
# It does NOT survive a full reboot on its own; re-run it after one.
nohup ./scripts/watchdog.sh > logs/watchdog_nohup.log 2>&1 &
disown
# stop it: pkill -f scripts/watchdog.sh && pkill -f "uvicorn app.main:app"
```

Then:

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8020/chat/demo-session-1/list

curl -X POST http://localhost:8020/chat/demo-session-1/reply \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"text": "I want to go to Japan"}'

curl -X POST http://localhost:8020/chat/demo-session-1/send \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"message": "🗺️ Light — maps & WhatsApp", "chip": "usage", "arg": "light"}'
```
