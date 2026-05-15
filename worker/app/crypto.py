import base64
import hashlib
import json
import os

from cryptography.fernet import Fernet


def _fernet() -> Fernet:
    secret = os.environ.get("APP_SECRET", "dev-change-me")
    digest = hashlib.sha256(secret.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def decrypt_token_blob(blob: str | None) -> dict | str | None:
    if not blob:
        return None
    raw = _fernet().decrypt(blob.encode()).decode()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw
