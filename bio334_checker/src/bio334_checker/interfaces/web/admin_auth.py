"""HTTP Basic auth dependency for /admin* routes.

Per ARCHITECTURE.md §9.1 (v0.3 R-6): single env-var-set credential,
bound to 127.0.0.1, rotated by restart. The 127.0.0.1 bind is enforced
by middleware in ``app.py``; this module only checks the credential.
"""

from __future__ import annotations

import base64
import hmac
import os

from fastapi import HTTPException, Request, status


ADMIN_USER_ENV = "BIO334_ADMIN_USER"
ADMIN_PASS_ENV = "BIO334_ADMIN_PASS"
REALM = "bio334-admin"


def require_admin(request: Request) -> str:
    """Return the admin username on success, or raise 401."""
    user = os.getenv(ADMIN_USER_ENV)
    pwd = os.getenv(ADMIN_PASS_ENV)
    if not user or not pwd:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"admin credentials are not configured "
                f"(set {ADMIN_USER_ENV} and {ADMIN_PASS_ENV})"
            ),
        )

    auth = request.headers.get("authorization") or ""
    expected_prefix = "Basic "
    if not auth.startswith(expected_prefix):
        _challenge()

    encoded = auth[len(expected_prefix):].strip()
    try:
        decoded = base64.b64decode(encoded).decode("utf-8", errors="replace")
    except Exception:
        _challenge()

    if ":" not in decoded:
        _challenge()
    given_user, _, given_pwd = decoded.partition(":")
    if not (hmac.compare_digest(given_user, user) and hmac.compare_digest(given_pwd, pwd)):
        _challenge()
    return given_user


def _challenge() -> None:
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="admin authentication required",
        headers={"WWW-Authenticate": f'Basic realm="{REALM}"'},
    )
