import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import get_settings


PASSWORD_SCHEME = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    encoded_digest = base64.b64encode(digest).decode("ascii")
    return f"{PASSWORD_SCHEME}${PBKDF2_ITERATIONS}${salt}${encoded_digest}"


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith(f"{PASSWORD_SCHEME}$"):
        try:
            _, iterations, salt, expected_digest = password_hash.split("$", 3)
            digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
            actual_digest = base64.b64encode(digest).decode("ascii")
            return hmac.compare_digest(actual_digest, expected_digest)
        except (TypeError, ValueError):
            return False

    try:
        from passlib.context import CryptContext

        legacy_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return legacy_context.verify(password, password_hash)
    except Exception:
        return False


def create_access_token(user_id: UUID, role: str, minutes: int) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": str(user_id), "role": role, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub")
        if subject is None:
            raise ValueError("Missing token subject")
        return UUID(subject)
    except (JWTError, ValueError) as exc:
        raise ValueError("Invalid authentication token") from exc
