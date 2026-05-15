import os

os.environ.setdefault("APP_SECRET", "test-secret-for-crypto-tests-32chars")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://konto:konto@localhost:5432/konto_kompass")

from api.app.crypto import encrypt_token_blob, decrypt_token_blob


def test_encrypt_decrypt_roundtrip():
    data = {"access": "secret-token", "refresh": "refresh-token"}
    encrypted = encrypt_token_blob(data)
    assert encrypted != str(data)
    decrypted = decrypt_token_blob(encrypted)
    assert decrypted == data
