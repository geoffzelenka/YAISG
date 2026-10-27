"""Persistence adapter for pure estate valuations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.engine.estates import Valuation, estate_value
from app.models import Estate, EstateUpgrade, RealmState
from app.services.market import market_contexts, spot_ask


def persisted_estate_value(
    session: Session, estate: Estate, content: ContentIndex
) -> Valuation:
    """Value installed assets without mutating their persisted state."""
    upgrades = list(
        session.scalars(
            select(EstateUpgrade.upgrade_id).where(EstateUpgrade.estate_id == estate.id)
        )
    )
    realm = session.get(RealmState, estate.realm_id)
    contexts = market_contexts(session, realm, content) if realm else {}
    return estate_value(
        estate.form_id,
        upgrades,
        estate.realm_id,
        content,
        lambda realm_id, item_id: (
            spot_ask(contexts[item_id][1]) if item_id in contexts else None
        ),
    )
