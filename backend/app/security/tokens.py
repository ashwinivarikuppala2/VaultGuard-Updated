import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from jose import JWTError, jwt
from app.core.config import settings
from app.core.exceptions import TokenValidationException


def create_access_token(
    subject: str,
    role: str,
    organization_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate cryptographically signed short-lived JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "org_id": organization_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate claims in access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise TokenValidationException("Invalid token type. Access token expected.")
        return payload
    except JWTError as e:
        raise TokenValidationException(f"Token signature verification failed: {str(e)}")


def generate_refresh_token_string() -> str:
    """Generate high-entropy random refresh token."""
    return f"{uuid.uuid4().hex}{uuid.uuid4().hex}"


def hash_token(token: str) -> str:
    """Deterministic SHA-256 hash for database token lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

