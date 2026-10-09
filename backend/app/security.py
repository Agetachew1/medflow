from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from backend.app.config import settings
import hashlib

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"

def hash_password(plain_password: str) -> str:
    hashed_bytes = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed_bytes.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")

    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except ValueError:
        # Support older dev seed data that used plain SHA-256 strings.
        hashed_attempt = hashlib.sha256(password_bytes).hexdigest()
        return hashed_attempt == hashed_password

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire_time = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["token_type"] = "access"
    to_encode["exp"] = expire_time
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("token_type", "access") != "access":
        raise jwt.InvalidTokenError("Invalid access token type")
    return payload


def create_refresh_token(data: dict, *, token_id: str, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload.update(
        {
            "token_type": "refresh",
            "jti": token_id,
            "exp": datetime.now(timezone.utc) + expires_delta,
        }
    )
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_refresh_token(token: str, *, verify_exp: bool = True) -> dict:
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"verify_exp": verify_exp},
    )
    if payload.get("token_type") != "refresh" or not payload.get("jti"):
        raise jwt.InvalidTokenError("Invalid refresh token")
    return payload
