"""World setup for tests that isolate character and estate behavior."""

from dataclasses import replace
from datetime import datetime

from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.services.world import create_world


def create_empty_world(session: Session, content: ContentIndex, now: datetime) -> None:
    """Use an explicit empty seed so unrelated tests own all their test holdings."""
    seed = content.world_seed.model_copy(
        update={
            "realms": tuple(
                realm.model_copy(update={"treasury": 0, "stores": (), "estates": ()})
                for realm in content.world_seed.realms
            )
        }
    )
    create_world(session, replace(content, world_seed=seed), now)
    session.commit()
