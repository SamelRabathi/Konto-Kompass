import base64
import hashlib
import json

from cryptography.fernet import Fernet

from .settings import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.app_secret.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_token_blob(data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data)
    return _fernet().encrypt(payload.encode()).decode()


def decrypt_token_blob(blob: str | None) -> dict | str | None:
    if not blob:
        return None
    raw = _fernet().decrypt(blob.encode()).decode()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw
