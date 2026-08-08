import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings
from app.core.crypto import (
    InvalidCipherValue,
    decrypt_field,
    derive_key,
    encrypt_field,
)


def test_round_trip() -> None:
    token = encrypt_field("hola-mundo-123", settings.encryption_key)
    assert decrypt_field(token, settings.encryption_key) == "hola-mundo-123"


def test_unicode_round_trip() -> None:
    token = encrypt_field("pérez-número-ñandú", settings.encryption_key)
    assert decrypt_field(token, settings.encryption_key) == "pérez-número-ñandú"


def test_empty_string() -> None:
    token = encrypt_field("", settings.encryption_key)
    assert decrypt_field(token, settings.encryption_key) == ""


def test_ciphertext_does_not_contain_plaintext() -> None:
    token = encrypt_field("tarjeta-4242-4242-4242", settings.encryption_key)
    assert "4242" not in token


def test_tampered_ciphertext_fails() -> None:
    token = encrypt_field("dato-sensible", settings.encryption_key)
    parts = token.split(":")
    # Mutar el ciphertext (cd): invertir el último carácter del payload base64
    parts[-2] = ("A" if parts[-2][-1] != "A" else "B") + parts[-2][1:]
    tampered = ":".join(parts)
    with pytest.raises(InvalidCipherValue):
        decrypt_field(tampered, settings.encryption_key)


def test_tampered_nonce_fails() -> None:
    token = encrypt_field("otro-dato", settings.encryption_key)
    parts = token.split(":")
    parts[3] = parts[3][:-1] + ("A" if parts[3][-1] != "A" else "B")
    tampered = ":".join(parts)
    with pytest.raises(InvalidCipherValue):
        decrypt_field(tampered, settings.encryption_key)


def test_wrong_key_fails() -> None:
    token = encrypt_field("secreto", b"clave-correcta-para-este-token")
    other_key = b"otra-clave-distinta-para-fallar"
    with pytest.raises(InvalidCipherValue):
        decrypt_field(token, other_key)


def test_unsupported_version_fails() -> None:
    from app.core.crypto import encrypt_field as enc

    token = enc("x", settings.encryption_key)
    parts = token.split(":")
    parts[1] = "99"
    with pytest.raises(InvalidCipherValue, match="Versión"):
        decrypt_field(":".join(parts), settings.encryption_key)


def test_invalid_format_fails() -> None:
    with pytest.raises(InvalidCipherValue):
        decrypt_field("no-es-un-token", settings.encryption_key)


def test_derive_key_is_deterministic_with_salt() -> None:
    salt = b"0123456789abcdef"
    k1 = derive_key(b"master-key", salt)
    k2 = derive_key(b"master-key", salt)
    k3 = derive_key(b"master-key", b"0123456789abcdeg")
    assert k1 == k2
    assert k1 != k3
    assert len(k1) == 32


def test_gcm_validity() -> None:
    # valida que el ciphertext descifra con AESGCM directo (interop)
    token = encrypt_field("data", settings.encryption_key)
    parts = token.split(":")
    _, version, salt_b64, nonce_b64, ct_b64, tag_b64 = parts
    assert version == "1"

    import base64

    salt = base64.b64decode(salt_b64)
    nonce = base64.b64decode(nonce_b64)
    ct = base64.b64decode(ct_b64)
    tag = base64.b64decode(tag_b64)

    derived = derive_key(settings.encryption_key, salt)
    aesgcm = AESGCM(derived)
    plaintext = aesgcm.decrypt(nonce, ct + tag, None)
    assert plaintext == b"data"