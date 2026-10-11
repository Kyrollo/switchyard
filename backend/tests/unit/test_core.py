from src.switchyard.core.config import settings
from src.switchyard.core.security import (
    create_access_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_api_key,
    verify_password,
)


def test_password_hashing() -> None:
    secret = "SuperSecret123!"
    hashed = hash_password(secret)
    assert hashed != secret
    assert verify_password(secret, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_tokens() -> None:
    payload = {"sub": "user@test.com", "role": "admin"}
    token = create_access_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "user@test.com"
    assert decoded["role"] == "admin"


def test_api_keys() -> None:
    key = generate_api_key()
    assert key.startswith("sk_live_")
    hashed = hash_api_key(key)
    assert verify_api_key(key, hashed) is True
    assert verify_api_key("sk_live_tampered", hashed) is False
