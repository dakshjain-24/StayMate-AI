import base64
import hashlib
import hmac
import secrets

from datetime import datetime, timedelta, timezone

import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import StaffUser


security = HTTPBearer(auto_error=False)



# PASSWORD HASHING

def hash_password(password: str) -> str:

    salt = secrets.token_bytes(16)

    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=64,
    )

    salt_text = base64.urlsafe_b64encode(salt).decode("utf-8")

    digest_text = base64.urlsafe_b64encode(digest).decode("utf-8")

    return (
        f"scrypt$16384$8$1$"
        f"{salt_text}$"
        f"{digest_text}"
    )


def verify_password(password: str, stored_hash: str) -> bool:

    try:
        (
            algorithm,
            n_value,
            r_value,
            p_value,
            salt_text,
            digest_text,
        ) = stored_hash.split("$")

        if algorithm != "scrypt":
            return False

        salt = base64.urlsafe_b64decode(salt_text)

        expected_digest = (base64.urlsafe_b64decode(digest_text))

        actual_digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n_value),
            r=int(r_value),
            p=int(p_value),
            dklen=len(expected_digest),
        )

        return hmac.compare_digest(expected_digest, actual_digest)

    except (ValueError, TypeError):
        return False



# STAFF LOOKUP

def authenticate_staff(db: Session, email: str, password: str) -> StaffUser | None:

    staff = db.scalar(
        select(
            StaffUser
        ).where(
            func.lower(StaffUser.email) == email.strip().lower()
        )
    )

    if not staff:
        return None

    if not staff.is_active:
        return None

    if not verify_password(password, staff.password_hash):
        return None

    return staff



# JWT

def create_access_token(staff: StaffUser) -> str:

    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is not configured.")

    now = datetime.now(timezone.utc)

    expires_at = (now + timedelta(minutes = settings.jwt_expire_minutes))

    payload = {
        "sub": str(staff.id),
        "hotel_id": staff.hotel_id,
        "type": "staff",
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm= settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:

    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is not configured.")

    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm]
    )



# FASTAPI AUTH DEPENDENCY

def get_current_staff(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db)
) -> StaffUser:

    unauthorized = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail=("Staff authentication required"),
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )

    if not credentials:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)

        if payload.get("type") != "staff":
            raise unauthorized

        staff_id = int(payload.get("sub"))

    except (
        jwt.ExpiredSignatureError,
        jwt.InvalidTokenError,
        ValueError,
        TypeError,
    ):

        raise unauthorized

    staff = db.get(StaffUser, staff_id)

    if not staff or not staff.is_active:
        raise unauthorized

    return staff