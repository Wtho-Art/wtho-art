"""Local password for the studio. The hash stays in studio/.auth."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from pathlib import Path

N = 2**14
R = 8
P = 1


def ensure_auth(directory: Path) -> str | None:
    """Create the secret and, on first launch, a password. Returns the password once."""
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)
    secret = directory / "secret.key"
    if not secret.exists():
        secret.write_bytes(secrets.token_bytes(32))
        os.chmod(secret, 0o600)
    password_file = directory / "password.hash"
    if password_file.exists():
        return None
    password = secrets.token_urlsafe(12)
    set_password(directory, password, minimum=8)
    return password


def secret_key(directory: Path) -> bytes:
    return (directory / "secret.key").read_bytes()


def set_password(directory: Path, password: str, minimum: int = 10) -> None:
    if len(password) < minimum:
        raise ValueError(f"Mindestens {minimum} Zeichen.")
    path = directory / "password.hash"
    path.write_text(hash_password(password) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def verify_password(directory: Path, password: str) -> bool:
    path = directory / "password.hash"
    if not path.is_file():
        return False
    return check_password(path.read_text(encoding="utf-8").strip(), password)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=N, r=R, p=P, dklen=32)
    return f"scrypt${N}${R}${P}${salt.hex()}${digest.hex()}"


def check_password(stored: str, password: str) -> bool:
    try:
        kind, n, r, p, salt_hex, digest_hex = stored.split("$")
        if kind != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
        )
        return hmac.compare_digest(digest, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False
