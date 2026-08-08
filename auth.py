from typing import Optional

from fastapi import Depends, Header, HTTPException, status

import config
import firebase_client


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    id_token = authorization.split(" ", 1)[1].strip()
    try:
        decoded = firebase_client.verify_id_token(id_token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    profile = firebase_client.get_user_profile(decoded["uid"]) or {}
    email = (decoded.get("email") or profile.get("email") or "").strip().lower()

    return {
        "uid": decoded["uid"],
        "email": email,
        "name": profile.get("name", ""),
        "is_admin": email in config.ADMIN_EMAILS,
    }


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user["is_admin"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user
