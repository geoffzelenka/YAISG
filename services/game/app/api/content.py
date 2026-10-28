"""Public endpoints for versioned static game content."""

from typing import cast

from fastapi import APIRouter, HTTPException, Request, Response

from app.content.loader import PUBLIC_PACKS, ContentIndex

router = APIRouter(prefix="/content", tags=["content"])
PUBLIC_CONTENT_PATHS = {
    "/content/manifest",
    *(f"/content/{pack}" for pack in PUBLIC_PACKS),
}


def _content(request: Request) -> ContentIndex:
    return cast(ContentIndex, request.app.state.content)


@router.get("/manifest")
def get_manifest(request: Request) -> dict[str, object]:
    """Return the overall content version and public pack hashes."""
    return _content(request).manifest.as_dict()


@router.get("/{pack}")
def get_pack(pack: str, request: Request) -> Response:
    """Return a canonical content pack with a strong hash-based ETag."""
    if pack not in PUBLIC_PACKS:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "CONTENT_PACK_NOT_FOUND",
                    "message": f"Unknown content pack: {pack}",
                }
            },
        )
    content = _content(request)
    etag = f'"{content.manifest.packs[pack]}"'
    cache_headers = {"ETag": etag, "Cache-Control": "public, no-cache"}
    validators = {
        value.strip() for value in request.headers.get("if-none-match", "").split(",")
    }
    if "*" in validators or etag in validators:
        return Response(status_code=304, headers=cache_headers)
    return Response(
        content=content.pack_payloads[pack],
        media_type="application/json",
        headers=cache_headers,
    )
