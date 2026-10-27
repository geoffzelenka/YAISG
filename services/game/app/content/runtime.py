"""Process-wide validated content index used by non-request fallbacks."""

from app.config import CONTENT_DIR
from app.content.loader import load_content

CONTENT = load_content(CONTENT_DIR)

# Warm the immutable map table at process boot.
_CARAVAN_ROUTES = CONTENT.caravan_routes
