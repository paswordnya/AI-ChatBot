"""Local-model integration for POST /chat/{session_id}/reply.

Talks to any OpenAI-compatible /chat/completions endpoint (Ollama, LM
Studio, ...) via stdlib urllib — same low-dependency convention as
pip-voice-ai-dashboard/backend/app/provider_probe.py, which this module
otherwise has no connection to (separate project, see README.md).

LM Studio (settings.llm_*) is primary; Ollama (settings.llm_fallback_*) is
only tried as backup if LM Studio's two attempts both fail — not load
balancing, a strict primary/backup order.

The model is asked to answer with structured output — one JSON object
shaped like a single item of getChatList's messages[] (see CHIP_CATALOG
below for the exact contract). There is deliberately no real product
catalog behind this (no destinations/packages table in this service) —
DEMO_CATALOG only exists to bias the model toward reusing the same
ids/isoCodes as scripts/seed_demo.py's sample conversation, so a demo
session stays internally consistent. A real integration would swap this
for an actual product-catalog lookup and likely pass it in as retrieved
context per-turn rather than hardcoding it into the prompt.

Never raises past generate_reply — a local model that's unreachable, slow,
or returns unparseable output degrades to FALLBACK_MESSAGE (the same
whatsapp_only chip already used in the sample conversation), rather than
breaking the chat.
"""

import json
import re
import urllib.error
import urllib.request

from app.config import settings

KNOWN_CHIPS = {
    "destinations", "usage", "plan_choice", "region_choice", "cta_plan",
    "esim_choice", "device", "ios_error", "android_error",
    "troubleshoot_check", "fix_applied", "nav_compatibility",
    "nav_destinations", "nav_install_guide", "nav_signin",
    "whatsapp_only", "none",
}

DEMO_CATALOG = {
    "destinations": [
        {"countryId": "0194e73f-32f0-7cca-af0f-3f86cdc2e01d", "isoCode": "JP", "label": "Japan 🇯🇵🍣"},
        {"countryId": "0194e73f-32f0-7cca-af0f-3f86cdc2e01d", "isoCode": "TH", "label": "Bangkok 🇹🇭🍜"},
        {"countryId": "0194e73f-32f0-7cca-af0f-3f86cdc2e01d", "isoCode": "EU", "label": "Europe trip 🇪🇺✈️"},
        {"countryId": "0194e73f-32f0-7cca-af0f-3f86cdc2e01d", "isoCode": "US", "label": "USA 🇺🇸🗽"},
    ],
    "japan_plans": [
        {"packageId": "98cf5f07-9d99-4ee4-9b61-3a4afd05a963", "countryId": "0194e73f-32f0-7cca-af0f-3f86cdc2e01d", "label": "1GB · 7 Days · $4.50"},
        {"packageId": "98cf5f07-9d99-4ee4-9b61-3a4afd05a963", "countryId": "0194e73f-32f0-7cca-af0f-3f86cdc2e01d", "label": "5GB · 15 Days · $12.00 ⭐"},
        {"packageId": "98cf5f07-9d99-4ee4-9b61-3a4afd05a963", "countryId": "0194e73f-32f0-7cca-af0f-3f86cdc2e01d", "label": "10GB · 30 Days · $19.50"},
    ],
    "browse_all_chip": {"label": "Browse all {destination} eSIMs", "deeplink": "searchResult"},
}

FALLBACK_MESSAGE = {
    "role": "assistant",
    "text": "I ran into a problem reaching the assistant. Please message us on WhatsApp at +62 813-6873-703 and we will help you right away.",
    "chip": "whatsapp_only",
    "chips": [],
    "deeplink": "https://wa.me/628136873703",
}

SYSTEM_PROMPT = f"""You are the RoaminRabbit eSIM travel assistant. Reply to the traveler's
last message with EXACTLY ONE JSON object — no prose, no markdown code
fences, nothing before or after the JSON.

The object must have:
- "role": always "assistant"
- "text": a short, friendly reply (may include emoji), matching the
  conversational tone of the examples below
- "chip": one of {sorted(KNOWN_CHIPS)} — pick whichever best matches what
  the traveler needs next in the conversation
- "chips": a list of quick-reply options for this turn (empty list [] if
  none apply, e.g. for "nav_signin", "whatsapp_only", "none"). Each item
  has "number" (1-based), "text", and "arg". "arg" is ALWAYS an object
  containing these four keys — "packageId", "countryId", "orderId",
  "esimId" — using "" for whichever don't apply to that chip. Add other
  keys on top of those four as needed: "isoCode" for a destination/country
  chip, "slug" for a region bundle, or "value" for a chip whose choice
  isn't an id at all (e.g. usage="light", device="ios",
  troubleshoot_check="resolved"). Add "deeplink"/"requiresLogin" on a chip
  when it should navigate somewhere ("checkout" or "searchResult") instead
  of just continuing the conversation. There is no real orders system
  behind this service, so "orderId" is always "" — never invent one.
- Optionally "isPopup": true when these chips should render as a popup
  rather than inline (omit the field entirely when it doesn't apply — do
  not send isPopup: false).
- Optionally "requiresLogin" at the top level (only for "esim_choice").
- Optionally "deeplink" at the top level (only for "whatsapp_only").

Known destinations and Japan plans (reuse these countryIds/isoCodes
verbatim when relevant — don't invent new ones for them). Every
"plan_choice" reply must end its "chips" with browse_all_chip, with
"{{destination}}" swapped for that destination's own name and no
"requiresLogin"/checkout on that one chip specifically (see the
plan_choice example below):
{json.dumps(DEMO_CATALOG, ensure_ascii=False)}

Example turns (for shape only, not literal answers to copy):
{{"role": "assistant", "text": "We've got eSIMs for 200+ countries — where are you headed? 🧳", "chip": "destinations", "isPopup": true, "chips": [{{"number": 1, "text": "Japan 🇯🇵🍣", "arg": {{"packageId": "", "countryId": "0194e73f-32f0-7cca-af0f-3f86cdc2e01d", "orderId": "", "esimId": "", "isoCode": "JP"}}}}]}}
{{"role": "assistant", "text": "Here's what I've got for Japan 🇯🇵🍣", "chip": "plan_choice", "isPopup": true, "chips": [{{"number": 1, "text": "1GB · 7 Days · $4.50", "deeplink": "checkout", "requiresLogin": true, "arg": {{"packageId": "98cf5f07-9d99-4ee4-9b61-3a4afd05a963", "countryId": "0194e73f-32f0-7cca-af0f-3f86cdc2e01d", "orderId": "", "esimId": ""}}}}, {{"number": 2, "text": "Browse all Japan eSIMs", "deeplink": "searchResult", "arg": {{"packageId": "", "countryId": "0194e73f-32f0-7cca-af0f-3f86cdc2e01d", "orderId": "", "esimId": "", "isoCode": "JP"}}}}]}}
{{"role": "assistant", "text": "Roughly how much will you be online out there? 🗺️", "chip": "usage", "isPopup": true, "chips": [{{"number": 1, "text": "🗺️ Light — maps & WhatsApp", "arg": {{"packageId": "", "countryId": "", "orderId": "", "esimId": "", "value": "light"}}}}]}}
{{"role": "assistant", "text": "If you sign in, I can tailor a recommendation to your exact trip. 😊", "chip": "nav_signin", "chips": []}}
{{"role": "assistant", "text": "Got it, thanks for letting me know! 😊", "chip": "none", "chips": []}}

If the traveler's message doesn't clearly map to any chip, use "chip":
"none" with an empty "chips": [] and a short conversational reply.
"""

def _history_to_chat_messages(history: list[dict]) -> list[dict]:
    """Collapse each stored turn's `payload` down to a plain {role, content}
    pair — the model only needs the conversational thread, not the chip
    machinery of prior turns."""
    out = []
    for payload in history:
        role = payload.get("role")
        text = payload.get("text", "")
        if role in ("assistant", "user") and text:
            out.append({"role": role, "content": text})
    return out

def _extract_json(raw: str) -> dict:
    """Local models routinely wrap JSON in ```json fences or add stray
    text around it despite instructions — pull out the first {...} block
    before parsing rather than failing on strict json.loads(raw)."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("no JSON object found in model output")
    return json.loads(match.group(0))

def _call_chat_completions(base_url: str, api_key: str, model: str, messages: list[dict]) -> str:
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.4,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=settings.llm_timeout_s) as resp:
        parsed = json.loads(resp.read())
    return parsed["choices"][0]["message"]["content"]

REQUIRED_ARG_KEYS = ("packageId", "countryId", "orderId", "esimId")

def _normalize_chip_arg(chip: dict) -> dict:
    """Guarantee packageId/countryId/orderId/esimId are present on every
    chip's arg, regardless of what the model actually produced — a prompt
    instruction alone isn't a contract a local model reliably follows.
    A missing arg, or one that's still a plain string (old shape, or a
    smaller model reverting to it despite instructions), becomes {"value":
    that string} first; any keys beyond the four required ones (isoCode,
    slug, value, ...) are kept as-is."""
    arg = chip.get("arg")
    if not isinstance(arg, dict):
        arg = {"value": arg} if arg not in (None, "") else {}
    chip["arg"] = {key: arg.get(key, "") for key in REQUIRED_ARG_KEYS} | {
        key: value for key, value in arg.items() if key not in REQUIRED_ARG_KEYS
    }
    return chip

def _validate(candidate: dict) -> dict:
    if not isinstance(candidate, dict):
        raise ValueError("model output is not a JSON object")
    if candidate.get("chip") not in KNOWN_CHIPS:
        raise ValueError(f"unknown or missing chip: {candidate.get('chip')!r}")
    if not isinstance(candidate.get("text"), str) or not candidate["text"].strip():
        raise ValueError("missing/empty text")
    candidate["role"] = "assistant"
    candidate["chips"] = [_normalize_chip_arg(dict(c)) for c in candidate.get("chips", [])]
    return candidate

_CALL_ERRORS = (urllib.error.URLError, OSError, KeyError, ValueError, json.JSONDecodeError)

def _try_provider(base_url: str, api_key: str, model: str, seed_messages: list[dict]) -> dict:
    """Two attempts against one provider: the seeded messages, then once
    more with a corrective nudge if the first reply didn't parse/validate.
    Raises the last error if both attempts fail — caller decides what to
    try next."""
    messages = list(seed_messages)
    last_error: Exception
    for attempt in range(2):
        try:
            raw = _call_chat_completions(base_url, api_key, model, messages)
            return _validate(_extract_json(raw))
        except _CALL_ERRORS as exc:
            last_error = exc
            messages.append({
                "role": "user",
                "content": (
                    "Your last reply wasn't a single valid JSON object matching the "
                    "required shape. Reply again with ONLY the JSON object, no other text."
                ),
            })
    raise last_error

def generate_reply(history: list[dict], user_text: str) -> dict:
    """Ask a local model for the next assistant turn. Tries LM Studio
    (settings.llm_*) first; if both its attempts fail, tries Ollama
    (settings.llm_fallback_*) as backup; if that also fails, degrades to
    FALLBACK_MESSAGE. Never raises — a chat endpoint shouldn't 500 just
    because every local model happens to be down."""
    seed_messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + _history_to_chat_messages(history)
        + [{"role": "user", "content": user_text}]
    )

    try:
        return _try_provider(settings.llm_base_url, settings.llm_api_key, settings.llm_model, seed_messages)
    except _CALL_ERRORS as primary_error:
        print(f"[llm_client] primary ({settings.llm_base_url}) failed, trying fallback: {primary_error!r}")

    try:
        return _try_provider(
            settings.llm_fallback_base_url, settings.llm_fallback_api_key, settings.llm_fallback_model, seed_messages
        )
    except _CALL_ERRORS as fallback_error:
        print(f"[llm_client] fallback ({settings.llm_fallback_base_url}) also failed: {fallback_error!r}")

    return dict(FALLBACK_MESSAGE)
