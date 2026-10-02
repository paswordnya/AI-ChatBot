from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

class ChatMessage(Base):
    """One turn in a chat session. `payload` is the entire message object
    exactly as the chat client should render it — role, text, chip,
    isPopup, chips[] (each possibly carrying arg/deeplink/requiresLogin),
    top-level deeplink/requiresLogin — stored verbatim rather than
    normalized into columns, because each `chip` type (destinations,
    plan_choice, esim_choice, nav_*, ...) shapes that object differently
    and there's no fixed schema across them.

    `role` is duplicated out as its own column purely so it's
    indexable/filterable; the response always comes from `payload`, never
    reconstructed from columns.

    There's no dialogue engine in this service — nothing here decides what
    an assistant message should say next. Whatever produces a session's
    messages (a chat backend elsewhere) is expected to POST each turn to
    /chat/{session_id}/messages as it happens; GET /chat/{session_id}/list
    just replays them in arrival order — that's what makes a session
    "dynamic" rather than a fixed mock.
    """

    __tablename__ = "chat_messages"
    __table_args__ = (UniqueConstraint("session_id", "sequence", name="uq_chat_messages_session_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
