"""Pure estate rules shared by voting and lifecycle callers."""

from app.content.schemas import EstateForm


def vote_weight(estate: EstateForm) -> int:
    """Return the vote weight determined by the estate's resolved form."""
    return 1 if estate.mobility == "mobile" else 9 + estate.tier
