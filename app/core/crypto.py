import base64
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

CIPHER_VERSION = "1"
_NONCE_SIZE = 12
_TAG_SIZE = 16
_SALT_SIZE = 16


class InvalidCipherValue(ValueError):
    """El token cifrado no tiene el formato esperado o fue manipulado."""


def derive_key(master: bytes, salt: bytes) -> bytes:
    """Deriva una clave de 32 bytes a partir de la master key con HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"field-encryption-v1",
    )
    return hkdf.derive(master)


def encrypt_field(plaintext: str, key: bytes) -> str:
    """Cifra un campo con AES-GCM y devuelve un token versionado.

    Formato: cipher:<version>:<salt_b64>:<nonce_b64>:<ct_b64>:<tag_b64>
    El resultado es autenticado: cualquier modificación se detecta al descifrar.
    """
    salt = os.urandom(_SALT_SIZE)
    nonce = os.urandom(_NONCE_SIZE)
    derived = derive_key(key, salt)
    cipher = Cipher(algorithms.AES(derived), modes.GCM(nonce))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()
    return ":".join(
        [
            "cipher",
            CIPHER_VERSION,
            _b64(salt),
            _b64(nonce),
            _b64(ciphertext),
            _b64(encryptor.tag),
        ]
    )


def decrypt_field(token: str, key: bytes) -> str:
    """Descifra un token generado por `encrypt_field`.

    Verifica la versión y la integridad/autenticación GCM; ante cualquier
    manipulación o formato inválido lanza `InvalidCipherValue`.
    """
    parts = token.split(":")
    if len(parts) != 6 or parts[0] != "cipher":
        raise InvalidCipherValue("Formato de cifrado inválido")

    if parts[1] != CIPHER_VERSION:
        raise InvalidCipherValue(f"Versión de cifrado no soportada: {parts[1]}")

    try:
        salt, nonce, ciphertext, tag = (_unb64(p) for p in parts[2:])
    except ValueError as exc:
        raise InvalidCipherValue("Datos de cifrado corruptos") from exc

    if not all((salt, nonce, tag)):
        raise InvalidCipherValue("Datos de cifrado vacíos")

    derived = derive_key(key, salt)
    cipher = Cipher(algorithms.AES(derived), modes.GCM(nonce, tag))
    decryptor = cipher.decryptor()
    try:
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    except Exception as exc:
        raise InvalidCipherValue("Fallo de autenticación del dato cifrado") from exc
    return plaintext.decode("utf-8")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(data: str) -> bytes:
    try:
        return base64.b64decode(data, validate=True)
    except Exception as exc:
        raise ValueError("base64 inválido") from exc