"""Persistence adapter for pure estate valuations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.engine.estates import Valuation, estate_value
from app.models import Estate, EstateUpgrade


def persisted_estate_value(
    session: Session, estate: Estate, content: ContentIndex
) -> Valuation:
    """Value installed assets and record the selected rebuild path."""
    upgrades = list(
        session.scalars(
            select(EstateUpgrade.upgrade_id).where(EstateUpgrade.estate_id == estate.id)
        )
    )
    value = estate_value(estate.form_id, upgrades, estate.realm_id, content)
    estate.data = {**estate.data, "valuation_path": list(value.path)}
    return value
