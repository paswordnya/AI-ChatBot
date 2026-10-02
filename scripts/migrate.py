"""Apply the SQLAlchemy models to the database — the only "migration"
mechanism this service has (no Alembic). Non-destructive: only creates
tables that don't exist yet (`checkfirst=True` is create_all's default),
never drops or alters an existing one. Run from chat-api/:

    python scripts/migrate.py

Assumes the target Postgres database (see DATABASE_URL in .env) already
exists — create it yourself first, e.g. `createdb chat_api`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Base, engine  # noqa: E402
from app import models  # noqa: E402,F401

def main() -> None:
    Base.metadata.create_all(engine)
    print("Schema up to date:", ", ".join(sorted(Base.metadata.tables.keys())))

if __name__ == "__main__":
    main()
