"""Database-shared fixed-window limits for authenticated game mutations."""

import os

from fastapi import Request
from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.auth import DatabaseSession, VerifiedIdentity
from app.clock import ServerNow
from app.errors import api_error
from app.models import MutationWindow
from app.services.realms import prepare_sqlite_write

MUTATION_LIMIT = int(os.getenv("GAME_MUTATION_LIMIT", "120"))
MUTATION_WINDOW_SECONDS = int(os.getenv("GAME_MUTATION_WINDOW_SECONDS", "60"))
if MUTATION_LIMIT < 1 or MUTATION_WINDOW_SECONDS < 1:
    raise ValueError("Game mutation rate limit and window must be positive")


def limit_mutation(request: Request, session: DatabaseSession, now: ServerNow) -> None:
    """Count attempts across routes and processes, including rejected intents.

    The verified account is a stable one-character key, including creation.
    Commit the allowance before game work so a rollback cannot refund attempts.
    Reads, including lazy resolution and polling, never consume this allowance.
    """
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    identity: VerifiedIdentity = request.state.identity
    prepare_sqlite_write(session)
    window = int(now.timestamp()) // MUTATION_WINDOW_SECONDS
    insert = (
        pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
    )
    statement = insert(MutationWindow).values(
        auth_user_id=identity.auth_user_id, window=window, attempts=1
    )
    counted = statement.on_conflict_do_update(
        index_elements=[MutationWindow.auth_user_id],
        set_={
            "window": window,
            "attempts": case(
                (MutationWindow.window != window, 1),
                (
                    MutationWindow.attempts <= MUTATION_LIMIT,
                    MutationWindow.attempts + 1,
                ),
                else_=MutationWindow.attempts,
            ),
        },
    ).returning(MutationWindow.attempts)
    attempts = session.scalar(counted)
    # Expired subjects need no history; this also bounds abandoned creation keys.
    session.execute(delete(MutationWindow).where(MutationWindow.window < window - 1))
    session.commit()
    if attempts is not None and attempts > MUTATION_LIMIT:
        retry_after = (window + 1) * MUTATION_WINDOW_SECONDS - int(now.timestamp())
        error = api_error(429, "RATE_LIMITED", "Too many game mutations")
        error.headers = {"Retry-After": str(retry_after)}
        raise error
