"""Seed a demo session with the sample RoaminRabbit-style conversation this
service was scoped from, so GET /chat/demo-session-1/list returns something
real out of the box instead of an empty list. Run from chat-api/:

    python scripts/seed_demo.py [--session-id demo-session-1] [--reset]
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import ChatMessage  # noqa: E402

def _arg(package_id="", country_id="", order_id="", esim_id="", **extra):
    """Every chip's arg — regardless of chip type — always carries these
    four keys, empty string when not applicable to that chip, so client
    code can always destructure the same shape rather than branching per
    chip type. `extra` covers whatever else that chip's `arg` needs on top
    (isoCode, slug, or the original plain-string choice under "value" for
    chips that used to just be arg: "light"/"ios"/"resolved"/...)."""
    return {
        "packageId": package_id,
        "countryId": country_id,
        "orderId": order_id,
        "esimId": esim_id,
        **extra,
    }

DEMO_MESSAGES = [
    {
        "role": "assistant",
        "text": "We've got eSIMs for 200+ countries and regions, plus regional and global plans for multi-country trips — where are you headed? 🧳",
        "chip": "destinations",
        "isPopup": True,
        "chips": [
            {"number": 1, "text": "Japan 🇯🇵🍣", "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", isoCode="JP")},
            {"number": 2, "text": "Bangkok 🇹🇭🍜", "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", isoCode="TH")},
            {"number": 3, "text": "Europe trip 🇪🇺✈️", "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", isoCode="EU")},
            {"number": 4, "text": "USA 🇺🇸🗽", "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", isoCode="US")},
        ],
    },
    {
        "role": "assistant",
        "text": "We've got eSIMs for 200+ countries and regions, plus regional and global plans for multi-country trips — where are you headed? 🧳",
        "chip": "destinations",
        "isPopup": False,
        "chips": [
            {"number": 1, "text": "Japan 🇯🇵🍣", "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", isoCode="JP")},
            {"number": 2, "text": "Bangkok 🇹🇭🍜", "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", isoCode="TH")},
            {"number": 3, "text": "Europe trip 🇪🇺✈️", "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", isoCode="EU")},
            {"number": 4, "text": "USA 🇺🇸🗽", "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", isoCode="US")},
        ],
    },
    {
        "role": "assistant",
        "text": "Roughly how much will you be online out there? 🗺️",
        "chip": "usage",
        "isPopup": True,
        "chips": [
            {"number": 1, "text": "🗺️ Light — maps & WhatsApp", "arg": _arg(value="light")},
            {"number": 2, "text": "📱 Moderate — social & calls", "arg": _arg(value="moderate")},
            {"number": 3, "text": "📬 Heavy — streaming & work", "arg": _arg(value="heavy")},
        ],
    },
    {
        "role": "assistant",
        "text": "Here's what I've got for Japan 🇯🇵🍣",
        "chip": "plan_choice",
        "isPopup": True,
        "chips": [
            {"number": 1, "text": "1GB · 7 Days · $4.50", "deeplink": "checkout", "requiresLogin": True, "arg": _arg(package_id="98cf5f07-9d99-4ee4-9b61-3a4afd05a963", country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d")},
            {"number": 2, "text": "5GB · 15 Days · $12.00 ⭐", "deeplink": "checkout", "requiresLogin": True, "arg": _arg(package_id="98cf5f07-9d99-4ee4-9b61-3a4afd05a963", country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d")},
            {"number": 3, "text": "10GB · 30 Days · $19.50", "deeplink": "checkout", "requiresLogin": True, "arg": _arg(package_id="98cf5f07-9d99-4ee4-9b61-3a4afd05a963", country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d")},
            {"number": 4, "text": "Browse all Japan eSIMs", "deeplink": "searchResult", "requiresLogin": False, "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", isoCode="JP")},
        ],
    },
    {
        "role": "assistant",
        "text": "One eSIM covers your whole trip — our Asia plan works across 20 areas! 🌏",
        "chip": "region_choice",
        "isPopup": True,
        "chips": [
            {"number": 1, "text": "🌍 Asia 20 Areas eSIM — from $5.00", "deeplink": "checkout", "requiresLogin": False, "arg": _arg(slug="asia-20-areas")},
        ],
    },
    {
        "role": "assistant",
        "text": "For 10 days of maps and messaging, the 5GB 15-day plan is your best match — plenty of headroom without overpaying. 🙌",
        "chip": "cta_plan",
        "isPopup": True,
        "chips": [
            {"number": 1, "text": "🛒 Checkout this eSIM", "deeplink": "checkout", "requiresLogin": True, "arg": _arg(package_id="98cf5f07-9d99-4ee4-9b61-3a4afd05a963", country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d")},
            {"number": 2, "text": "Explore all options", "deeplink": "searchResult", "requiresLogin": False, "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", isoCode="JP")},
        ],
    },
    {
        "role": "assistant",
        "text": "Here's what I found — which one needs help? 📱",
        "chip": "esim_choice",
        "isPopup": True,
        "requiresLogin": True,
        "chips": [
            {"number": 1, "text": "Japan — 5GB 15 Days (active)", "arg": _arg(package_id="98cf5f07-9d99-4ee4-9b61-3a4afd05a963", country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", esim_id="esim_9001")},
            {"number": 2, "text": "Indonesia — 1GB 7 Days (upcoming)", "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", esim_id="esim_9002")},
            {"number": 3, "text": "Singapore — 3GB 7 Days (archived)", "arg": _arg(country_id="0194e73f-32f0-7cca-af0f-3f86cdc2e01d", esim_id="esim_9003")},
        ],
    },
    {
        "role": "assistant",
        "text": "Let's get that sorted — what device are you using? 📱",
        "chip": "device",
        "isPopup": True,
        "chips": [
            {"number": 1, "text": "iPhone", "arg": _arg(value="ios")},
            {"number": 2, "text": "Android", "arg": _arg(value="android")},
        ],
    },
    {
        "role": "assistant",
        "text": "Got it — what does your screen show? 📱",
        "chip": "ios_error",
        "isPopup": True,
        "chips": [
            {"number": 1, "text": "Unable to Activate eSIM", "arg": _arg(value="activation_failed")},
            {"number": 2, "text": "QR code no longer valid / already scanned", "arg": _arg(value="qr_invalid")},
            {"number": 3, "text": "I see something else", "arg": _arg(value="other")},
        ],
    },
    {
        "role": "assistant",
        "text": "Got it — what does your screen show? 📱",
        "chip": "android_error",
        "isPopup": True,
        "chips": [
            {"number": 1, "text": "Download failed / couldn't download SIM", "arg": _arg(value="download_failed")},
            {"number": 2, "text": "SIM not supported / device not compatible", "arg": _arg(value="unsupported")},
            {"number": 3, "text": "I see something else", "arg": _arg(value="other")},
        ],
    },
    {
        "role": "assistant",
        "text": "Try Airplane Mode on for 10 seconds, then off — that clears most stuck connections. ✈️",
        "chip": "troubleshoot_check",
        "isPopup": True,
        "chips": [
            {"number": 1, "text": "It's working now!", "arg": _arg(value="resolved")},
            {"number": 2, "text": "Still not connecting", "arg": _arg(value="unresolved")},
        ],
    },
    {
        "role": "assistant",
        "text": "Your eSIM is on your phone, but the line isn't switched on yet — easy fix! Go to Settings → Cellular, tap your RoaminRabbit eSIM, and turn on 'Turn On This Line'. 📱",
        "chip": "fix_applied",
        "isPopup": True,
        "chips": [
            {"number": 1, "text": "Done — check again", "arg": _arg(value="resolved")},
            {"number": 2, "text": "Still not working", "arg": _arg(value="unresolved")},
        ],
    },
    {
        "role": "assistant",
        "text": "Let's double-check your device supports eSIM first.",
        "chip": "nav_compatibility",
        "isPopup": True,
        "chips": [
            {"number": 1, "text": "Take me to the compatibility checker", "deeplink": "https://www.roaminrabbit.com/guide/device-compability", "arg": _arg()},
        ],
    },
    {
        "role": "assistant",
        "text": "Take a look at every destination we cover.",
        "chip": "nav_destinations",
        "isPopup": True,
        "chips": [{"number": 1, "text": "Browse all destinations", "arg": _arg()}],
    },
    {
        "role": "assistant",
        "text": "Here's the step-by-step install guide.",
        "chip": "nav_install_guide",
        "isPopup": True,
        "chips": [{"number": 1, "text": "Open install guide", "arg": _arg()}],
    },
    {
        "role": "assistant",
        "text": "If you sign in, I can tailor a recommendation to your exact trip — dates, what you'll use online, the works. 😊",
        "chip": "nav_signin",
        "chips": [],
    },
    {
        "role": "assistant",
        "text": "I ran into a problem reaching the assistant. Please message us on WhatsApp at +62 813-6873-703 and we will help you right away.",
        "chip": "whatsapp_only",
        "chips": [],
        "deeplink": "https://wa.me/628136873703",
    },
    {
        "role": "assistant",
        "text": "Got it, thanks for letting me know! 😊",
        "chip": "none",
        "chips": [],
    },
]

def main(session_id: str, reset: bool) -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if reset:
            db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
            db.commit()

        existing = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
        if existing:
            print(f"Session '{session_id}' already has {existing} message(s) — pass --reset to reseed. Nothing done.")
            return

        base_time = datetime.now(timezone.utc)
        for i, payload in enumerate(DEMO_MESSAGES, start=1):
            db.add(
                ChatMessage(
                    session_id=session_id,
                    sequence=i,
                    role=payload["role"],
                    payload=payload,
                    created_at=base_time + timedelta(seconds=i),
                )
            )
        db.commit()
        print(f"Seeded {len(DEMO_MESSAGES)} messages into session '{session_id}'.")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", default="demo-session-1")
    parser.add_argument("--reset", action="store_true", help="Delete this session's existing messages first")
    args = parser.parse_args()
    main(args.session_id, args.reset)
