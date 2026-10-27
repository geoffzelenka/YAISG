"""Persistence adapter for pure estate valuations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.engine.estates import Valuation, estate_value
from app.models import Estate, EstateUpgrade


def persisted_estate_value(
    session: Session, estate: Estate, content: ContentIndex
) -> Valuation:
    """Value installed assets without mutating their persisted state."""
    upgrades = list(
        session.scalars(
            select(EstateUpgrade.upgrade_id).where(EstateUpgrade.estate_id == estate.id)
        )
    )
    return estate_value(estate.form_id, upgrades, estate.realm_id, content)
