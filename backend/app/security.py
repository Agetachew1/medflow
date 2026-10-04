from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from backend.app.config import settings
import hashlib

# In a real app, this is loaded from .env. For now, a hardcoded fallback is fine.
SECRET_KEY = getattr(settings, "jwt_secret_key", "temporary-dev-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
    expire_time = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire_time
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
