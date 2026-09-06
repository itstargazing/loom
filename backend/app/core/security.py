"""Request authentication.

Stub implementation: a single shared bearer token maps every request to one
development user. Account settings, logout, and delete-account live on top of
this. Replace the body of ``get_current_user_id`` when a real IdP is wired;
nothing downstream should change.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_bearer = HTTPBearer(auto_error=True)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> str:
    if credentials.credentials != settings.stub_auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return settings.stub_user_id


CurrentUserId = Annotated[str, Depends(get_current_user_id)]
