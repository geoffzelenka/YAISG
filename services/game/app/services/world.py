"""Atomic, idempotent world creation from private seed content."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.models import Estate, RealmState, RealmStore, WorldState
from app.services.stores import recompute_lines


def create_world(session: Session, content: ContentIndex, now: datetime) -> bool:
    """Claim the singleton marker and seed once in the caller's transaction."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    insert = sqlite_insert if session.get_bind().dialect.name == "sqlite" else pg_insert
    claimed = session.execute(
        insert(WorldState)
        .values(
            id=1,
            seeded_at=now,
            last_caravan_pass=now,
            content_version=content.manifest.version,
        )
        .on_conflict_do_nothing(index_elements=["id"])
        .returning(WorldState.id)
    ).scalar_one_or_none()
    if claimed is None:
        return False
    for seed in sorted(content.world_seed.realms, key=lambda s: s.realm_id):
        template = content.realm(seed.realm_id)
        realm = session.get(RealmState, template.id)
        if realm is None:
            realm = RealmState(
                id=template.id,
                template_id=template.id,
                isolated=False,
                current_node_id=template.starting_node_id,
                treasury=seed.treasury,
                last_tick_at=now,
            )
            session.add(realm)
        else:
            realm.treasury = seed.treasury
        session.flush()
        session.add_all(
            RealmStore(
                realm_id=realm.id, item_id=s.item_id, quantity_milli=s.qty * 1000
            )
            for s in seed.stores
        )
        session.add_all(
            Estate(realm_id=realm.id, form_id=form, owner_character_id=None)
            for form in seed.estates
        )
        session.flush()
        recompute_lines(session, realm, content)
    session.flush()
    return True


def main() -> None:
    """Create the configured world from the command line."""
    from app.content.runtime import CONTENT
    from app.db import SessionLocal

    with SessionLocal.begin() as session:
        create_world(session, CONTENT, datetime.now(UTC))


if __name__ == "__main__":
    main()
