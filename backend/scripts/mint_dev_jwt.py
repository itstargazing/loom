"""Mint a development JWT for AUTH_MODE=jwt local testing.

Example:
  python -m scripts.mint_dev_jwt --sub alice
  # then: Authorization: Bearer <token>
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sub", required=True, help="User id / JWT subject")
    parser.add_argument("--hours", type=int, default=24 * 7, help="Token lifetime")
    args = parser.parse_args()

    now = datetime.now(UTC)
    payload = {
        "sub": args.sub,
        "iat": now,
        "exp": now + timedelta(hours=args.hours),
    }
    if settings.jwt_audience:
        payload["aud"] = settings.jwt_audience
    if settings.jwt_issuer:
        payload["iss"] = settings.jwt_issuer

    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    print(token)


if __name__ == "__main__":
    main()
