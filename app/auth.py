"""One shared-secret gate for every /chat/* route — see Settings.api_key.
Not real per-user auth (no accounts, no tokens, no scopes); this exists
only so this service isn't wide open to anything on the local network
while you develop against it. Swap for real auth before this ever leaves
your machine.
"""

from typing import Optional

from fastapi import Header, HTTPException

from app.config import settings

def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
