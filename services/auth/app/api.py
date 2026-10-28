"""Authentication HTTP endpoints."""

import uuid
from datetime import timedelta
from hmac import compare_digest
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import (
    ACCESS_TOKEN_SECONDS,
    JWT_ISSUER,
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_SECURE,
    REFRESH_TOKEN_SECONDS,
)
from app.db import get_db, prepare_sqlite_write
from app.errors import api_error
from app.models import RefreshToken, User
from app.rate_limit import IpRateLimiter
from app.schemas import AccessTokenResponse, Credentials
from app.security import (
    SigningKeys,
    ensure_utc,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    perform_dummy_password_verify,
    provide_signing_keys,
    refresh_token_id,
    utc_now,
    verify_password,
)

router = APIRouter()
credential_limiter = IpRateLimiter()
DatabaseSession = Annotated[Session, Depends(get_db)]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)]
KeyStore = Annotated[SigningKeys, Depends(provide_signing_keys)]


def _normalized_email(email: str) -> str:
    normalized = email.strip().lower()
    local, separator, domain = normalized.partition("@")
    if not local or separator != "@" or "." not in domain or len(normalized) > 320:
        raise api_error(422, "INVALID_EMAIL", "A valid email address is required")
    return normalized


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=REFRESH_TOKEN_SECONDS,
        httponly=True,
        secure=REFRESH_COOKIE_SECURE,
        samesite="lax",
        path="/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=REFRESH_COOKIE_SECURE,
        samesite="lax",
        path="/auth",
    )


def _issue_session(
    session: Session, response: Response, user: User, keys: SigningKeys
) -> AccessTokenResponse:
    token_id = uuid.uuid4()
    raw_token = new_refresh_token(token_id)
    session.add(
        RefreshToken(
            id=token_id,
            user_id=user.id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=utc_now() + timedelta(seconds=REFRESH_TOKEN_SECONDS),
            revoked_at=None,
        )
    )
    user.last_activity_at = utc_now()
    session.commit()
    _set_refresh_cookie(response, raw_token)
    return AccessTokenResponse(
        access_token=keys.issue_access_token(user.id, user.kind),
        expires_in=ACCESS_TOKEN_SECONDS,
    )


def _find_refresh_token(session: Session, raw_token: str) -> RefreshToken | None:
    token_id = refresh_token_id(raw_token)
    if token_id is None:
        return None
    token = session.get(RefreshToken, token_id)
    if token is None or not compare_digest(
        token.token_hash, hash_refresh_token(raw_token)
    ):
        return None
    return token


@router.post("/auth/register", response_model=AccessTokenResponse, status_code=201)
async def register(
    credentials: Credentials,
    request: Request,
    response: Response,
    session: DatabaseSession,
    keys: KeyStore,
) -> AccessTokenResponse:
    """Create an account and immediately establish a login session."""
    credential_limiter.check(request)
    prepare_sqlite_write(session)
    if len(credentials.password) < 10:
        raise api_error(422, "WEAK_PASSWORD", "Password must be at least 10 characters")
    user = User(
        email=_normalized_email(credentials.email),
        password_hash=hash_password(credentials.password),
        created_at=utc_now(),
        status="active",
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise api_error(
            409, "EMAIL_TAKEN", "An account already uses this email"
        ) from error
    return _issue_session(session, response, user, keys)


@router.post("/auth/login", response_model=AccessTokenResponse)
async def login(
    credentials: Credentials,
    request: Request,
    response: Response,
    session: DatabaseSession,
    keys: KeyStore,
) -> AccessTokenResponse:
    """Verify credentials and establish a login session."""
    credential_limiter.check(request)
    prepare_sqlite_write(session)
    try:
        email = _normalized_email(credentials.email)
    except HTTPException:
        perform_dummy_password_verify(credentials.password)
        raise api_error(
            401, "INVALID_CREDENTIALS", "Email or password is incorrect"
        ) from None
    user = session.scalar(select(User).where(User.email == email).with_for_update())
    if user is None:
        perform_dummy_password_verify(credentials.password)
        raise api_error(401, "INVALID_CREDENTIALS", "Email or password is incorrect")
    if user.password_hash is None or not verify_password(
        user.password_hash, credentials.password
    ):
        raise api_error(401, "INVALID_CREDENTIALS", "Email or password is incorrect")
    if user.status != "active":
        raise api_error(401, "ACCOUNT_INACTIVE", "Account is not active")
    return _issue_session(session, response, user, keys)


@router.post("/auth/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response,
    session: DatabaseSession,
    keys: KeyStore,
    refresh_token: RefreshCookie = None,
) -> AccessTokenResponse:
    """Rotate a valid refresh token and return a new access token."""
    prepare_sqlite_write(session)
    if refresh_token is None:
        raise api_error(401, "INVALID_REFRESH_TOKEN", "Refresh token is missing")
    stored_token = _find_refresh_token(session, refresh_token)
    if stored_token is None:
        raise api_error(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid")
    user = session.scalar(
        select(User)
        .where(User.id == stored_token.user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None:
        raise api_error(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid")
    now = utc_now()
    if ensure_utc(stored_token.expires_at) <= now:
        if stored_token.revoked_at is None:
            stored_token.revoked_at = now
            session.commit()
        raise api_error(401, "REFRESH_TOKEN_EXPIRED", "Refresh token has expired")
    if stored_token.revoked_at is not None:
        session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == stored_token.user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        session.commit()
        raise api_error(401, "REFRESH_TOKEN_REUSED", "Refresh token reuse detected")
    rotated_token_id = session.scalar(
        update(RefreshToken)
        .where(
            RefreshToken.id == stored_token.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
        .returning(RefreshToken.id)
    )
    if rotated_token_id is None:
        session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == stored_token.user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        session.commit()
        raise api_error(401, "REFRESH_TOKEN_REUSED", "Refresh token reuse detected")
    user = session.get(User, stored_token.user_id)
    if user is None:
        session.rollback()
        raise api_error(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid")
    return _issue_session(session, response, user, keys)


@router.post("/auth/logout", status_code=204)
async def logout(
    response: Response,
    session: DatabaseSession,
    refresh_token: RefreshCookie = None,
) -> None:
    """Revoke the presented refresh token and remove its cookie."""
    if refresh_token is not None:
        stored_token = _find_refresh_token(session, refresh_token)
        if stored_token is not None and stored_token.revoked_at is None:
            stored_token.revoked_at = utc_now()
            session.commit()
    _clear_refresh_cookie(response)


@router.get("/.well-known/jwks.json")
async def jwks(keys: KeyStore) -> dict[str, list[dict[str, str]]]:
    """Publish public signing keys for access-token verifiers."""
    return keys.jwks()


@router.post("/auth/guest", response_model=AccessTokenResponse, status_code=201)
async def guest(
    request: Request, response: Response, session: DatabaseSession, keys: KeyStore
) -> AccessTokenResponse:
    """Create a credential-free guest using the normal session lifecycle."""
    credential_limiter.check(request)
    prepare_sqlite_write(session)
    user = User(
        kind="guest",
        email=None,
        password_hash=None,
        created_at=utc_now(),
        last_activity_at=utc_now(),
        status="active",
    )
    session.add(user)
    session.flush()
    return _issue_session(session, response, user, keys)


@router.post("/auth/upgrade", response_model=AccessTokenResponse)
async def upgrade(
    credentials: Credentials,
    request: Request,
    response: Response,
    session: DatabaseSession,
    keys: KeyStore,
) -> AccessTokenResponse:
    """Attach credentials to the verified guest without replacing its identity."""
    credential_limiter.check(request)
    prepare_sqlite_write(session)
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    try:
        if scheme.lower() != "bearer":
            raise ValueError("Missing bearer token")
        claims = jwt.decode(
            token,
            keys.public_key,
            algorithms=["RS256"],
            issuer=JWT_ISSUER,
            options={"require": ["sub", "exp", "iss"]},
        )
        identifier = uuid.UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise api_error(
            401, "UNAUTHORIZED", "A valid access token is required"
        ) from None
    user = session.scalar(select(User).where(User.id == identifier).with_for_update())
    if user is None or user.status != "active":
        raise api_error(401, "UNAUTHORIZED", "A valid access token is required")
    if user.kind != "guest":
        raise api_error(409, "ACCOUNT_ALREADY_FULL", "Account already has credentials")
    if len(credentials.password) < 10:
        raise api_error(422, "WEAK_PASSWORD", "Password must be at least 10 characters")
    user.email = _normalized_email(credentials.email)
    user.password_hash = hash_password(credentials.password)
    user.kind = "full"
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise api_error(
            409, "EMAIL_TAKEN", "An account already uses this email"
        ) from error
    return _issue_session(session, response, user, keys)
