"""Request authentication.

``AUTH_MODE=stub`` — one shared bearer maps every request to ``STUB_USER_ID``.
Local development only; production startup refuses this mode.

``AUTH_MODE=jwt`` — Bearer is a JWT. ``sub`` becomes the LOOM user id, so each
person (or Clerk/Supabase subject) gets an isolated data partition. Verify with
``JWT_SECRET`` (HS256) and/or ``JWT_JWKS_URL`` (RS256 / Clerk / Supabase).
"""

from __future__ import annotations

import logging
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import settings

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=True)
_jwks_client: PyJWKClient | None = None


def _algorithms() -> list[str]:
    return [part.strip() for part in settings.jwt_algorithms.split(",") if part.strip()]


def _jwks() -> PyJWKClient | None:
    global _jwks_client
    if not settings.jwt_jwks_url:
        return None
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.jwt_jwks_url)
    return _jwks_client


def decode_user_id_from_jwt(token: str) -> str:
    """Return the JWT ``sub`` claim after signature verification."""
    options = {"require": ["sub", "exp"]}
    audience = settings.jwt_audience or None
    issuer = settings.jwt_issuer or None
    algorithms = _algorithms()

    try:
        jwks = _jwks()
        if jwks is not None:
            signing_key = jwks.get_signing_key_from_jwt(token).key
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=algorithms or ["RS256"],
                audience=audience,
                issuer=issuer,
                options=options,
            )
        else:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=algorithms or ["HS256"],
                audience=audience,
                issuer=issuer,
                options=options,
            )
    except jwt.PyJWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject.strip()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> str:
    mode = (settings.auth_mode or "stub").strip().lower()
    token = credentials.credentials

    if mode == "jwt":
        return decode_user_id_from_jwt(token)

    if mode != "stub":
        logger.error("Unknown AUTH_MODE %r; refusing the request.", settings.auth_mode)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server auth is misconfigured",
        )

    if token != settings.stub_auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return settings.stub_user_id


CurrentUserId = Annotated[str, Depends(get_current_user_id)]


def assert_auth_safe_for_environment() -> None:
    """Call from app lifespan. Production must not run shared stub auth."""
    env = (settings.environment or "development").strip().lower()
    mode = (settings.auth_mode or "stub").strip().lower()
    if env == "production" and mode == "stub":
        raise RuntimeError(
            "Refusing to start: ENVIRONMENT=production with AUTH_MODE=stub. "
            "Set AUTH_MODE=jwt and issue per-user tokens (Clerk/Supabase/mint_dev_jwt) "
            "before serving real users."
        )
    if mode == "stub":
        logger.warning(
            "AUTH_MODE=stub — every client shares user %r. Not safe for multi-user release.",
            settings.stub_user_id,
        )
    else:
        logger.info("AUTH_MODE=%s (JWT subjects map to LOOM user ids).", mode)
