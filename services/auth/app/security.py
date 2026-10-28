"""Password, refresh-token, and RSA access-token primitives."""

import base64
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import (
    ACCESS_TOKEN_SECONDS,
    AUTH_KEYS_DIR,
    JWT_ISSUER,
    REFRESH_TOKEN_SECONDS,
)

_password_hasher = PasswordHasher()
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$uaLbg4bD2rybxdbbmiRmjQ$"
    "YXM48rYPkdq4OADO1e7mARVoJThY2YJZ2khEoDrNgtk"
)


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC value."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Restore UTC tzinfo when SQLite returns a naive datetime."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def hash_password(password: str) -> str:
    """Hash a password using Argon2's recommended parameters."""
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Safely verify a password without leaking malformed hash errors."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def perform_dummy_password_verify(password: str) -> None:
    """Spend one Argon2 verification to obscure whether an account exists."""
    verify_password(_DUMMY_PASSWORD_HASH, password)


def new_refresh_token(token_id: uuid.UUID) -> str:
    """Create an opaque credential whose identifier supports indexed lookup."""
    return f"{token_id}.{secrets.token_urlsafe(48)}"


def refresh_token_id(token: str) -> uuid.UUID | None:
    """Extract a refresh-token identifier, or return None if malformed."""
    try:
        return uuid.UUID(token.split(".", maxsplit=1)[0])
    except (ValueError, AttributeError):
        return None


def hash_refresh_token(token: str) -> str:
    """Hash an opaque refresh credential for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _base64url_uint(value: int) -> str:
    data = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class SigningKeys:
    """Load or create the auth service's persistent RSA signing keypair."""

    def __init__(self, keys_dir: Path = AUTH_KEYS_DIR) -> None:
        self._private_path = keys_dir / "private.pem"
        self._public_path = keys_dir / "public.pem"
        self._load_or_create()

    def _load_or_create(self) -> None:
        self._private_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._private_path.exists():
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            private_bytes = private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            self._private_path.write_bytes(private_bytes)
            self._private_path.chmod(0o600)
            self._public_path.write_bytes(
                private_key.public_key().public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )
        loaded_key = serialization.load_pem_private_key(
            self._private_path.read_bytes(), password=None
        )
        if not isinstance(loaded_key, rsa.RSAPrivateKey):
            raise ValueError(f"Signing key is not RSA: {self._private_path}")
        self.private_key: rsa.RSAPrivateKey = loaded_key
        self.public_key: rsa.RSAPublicKey = loaded_key.public_key()
        public_der = self.public_key.public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.key_id = hashlib.sha256(public_der).hexdigest()[:16]

    def issue_access_token(self, user_id: uuid.UUID, kind: str = "full") -> str:
        """Issue a 15-minute RS256 access token for a user."""
        now = utc_now()
        claims = {
            "sub": str(user_id),
            "kind": kind,
            "session_exp": int(
                (now + timedelta(seconds=REFRESH_TOKEN_SECONDS)).timestamp()
            ),
            "iat": now,
            "exp": now + timedelta(seconds=ACCESS_TOKEN_SECONDS),
            "iss": JWT_ISSUER,
        }
        return jwt.encode(
            claims, self.private_key, algorithm="RS256", headers={"kid": self.key_id}
        )

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        """Return the active public key in JSON Web Key Set format."""
        numbers = self.public_key.public_numbers()
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": self.key_id,
                    "n": _base64url_uint(numbers.n),
                    "e": _base64url_uint(numbers.e),
                }
            ]
        }


@lru_cache(maxsize=1)
def get_signing_keys() -> SigningKeys:
    """Lazily load the process-wide signing keys on first use."""
    return SigningKeys()


async def provide_signing_keys() -> SigningKeys:
    """Provide lazy signing keys without FastAPI thread-pool handoff."""
    return get_signing_keys()
