"""Admin authentication for OpenClaw Moltbook Monitor.

Password hashing uses PBKDF2-SHA256 (stdlib only, no extra deps).
Credentials are read from ADMIN_PASSWORD_HASH env var (takes priority)
or from ADMIN_CREDS_PATH file (default: ~/.openclaw/admin.creds).

Username is always "admin".  Only the password is managed here.
"""

import hashlib
import os
import secrets
from pathlib import Path

_ADMIN_USERNAME = "admin"
_ITERATIONS = 260_000  # OWASP minimum for PBKDF2-SHA256


def hash_password(password: str) -> str:
    """Return a PBKDF2-SHA256 hash string for *password*."""
    salt = secrets.token_hex(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS)
    return f"pbkdf2:sha256:{_ITERATIONS}:{salt}:{dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Return True if *password* matches *stored_hash*, using constant-time comparison."""
    parts = stored_hash.split(":")
    if len(parts) != 5 or parts[0] != "pbkdf2":
        return False
    _, algorithm, iterations_str, salt, expected_hex = parts
    try:
        iterations = int(iterations_str)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac(algorithm, password.encode(), salt.encode(), iterations)
    return secrets.compare_digest(dk.hex(), expected_hex)


def get_credentials_path() -> Path:
    """Return the path where the admin password hash is stored."""
    custom = os.getenv("ADMIN_CREDS_PATH")
    if custom:
        return Path(custom)
    data_dir = Path(os.getenv("MONITOR_DATA_DIR", str(Path.home() / ".openclaw")))
    return data_dir / "admin.creds"


def load_password_hash() -> str | None:
    """Return the stored hash, or None if no password has been set.

    Checks ADMIN_PASSWORD_HASH env var first, then the credentials file.
    """
    env_hash = os.getenv("ADMIN_PASSWORD_HASH")
    if env_hash:
        return env_hash.strip() or None
    creds_path = get_credentials_path()
    if creds_path.exists():
        return creds_path.read_text().strip() or None
    return None


def save_password_hash(password_hash: str) -> None:
    """Write *password_hash* to the credentials file with mode 0o600."""
    creds_path = get_credentials_path()
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    creds_path.write_text(password_hash + "\n")
    creds_path.chmod(0o600)


def is_password_set() -> bool:
    """Return True if an admin password has been configured."""
    return load_password_hash() is not None


def authenticate(username: str, password: str) -> bool:
    """Return True if *username*/*password* are valid admin credentials."""
    if username != _ADMIN_USERNAME:
        return False
    stored = load_password_hash()
    if stored is None:
        return False
    return verify_password(password, stored)
