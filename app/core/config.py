"""Configuration management for Aegis AI."""

import os
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# In-memory key for cases where .env is not writable
_in_memory_key: str | None = None


def _ensure_encryption_key() -> str:
    """
    Ensure an ENCRYPTION_KEY exists. Auto-generate if missing.
    Persists to .env file when possible.
    """
    global _in_memory_key

    key = os.getenv("ENCRYPTION_KEY")
    if key:
        try:
            Fernet(key.encode())
            return key
        except Exception:
            pass

    # Auto-generate
    key = Fernet.generate_key().decode()
    print("[CONFIG] ENCRYPTION_KEY not found or invalid — auto-generated new key")

    # Try to persist to .env
    try:
        if ENV_FILE.exists():
            content = ENV_FILE.read_text(encoding="utf-8")
        else:
            content = ""

        if "ENCRYPTION_KEY" in content:
            import re
            content = re.sub(r"^ENCRYPTION_KEY=.*$", f"ENCRYPTION_KEY={key}", content, flags=re.MULTILINE)
        else:
            if content and not content.endswith("\n"):
                content += "\n"
            content += f"ENCRYPTION_KEY={key}\n"

        ENV_FILE.write_text(content, encoding="utf-8")
        print(f"[CONFIG] ENCRYPTION_KEY persisted to {ENV_FILE}")
    except Exception as e:
        print(f"[CONFIG] Warning: Could not persist ENCRYPTION_KEY to .env: {e}")
        _in_memory_key = key

    os.environ["ENCRYPTION_KEY"] = key
    return key


def load_config() -> dict:
    """
    Load and validate configuration from .env file.
    ADMIN_PASSWORD is no longer required (set via wizard).
    ENCRYPTION_KEY is auto-generated if missing.
    """
    load_dotenv(ENV_FILE, override=True)

    encryption_key = _ensure_encryption_key()

    config = {
        "AIDR_TOKEN": os.getenv("AIDR_TOKEN"),
        "AIDR_URL": os.getenv("AIDR_URL", "https://api.crowdstrike.com/aidr/aiguard"),
        "ENCRYPTION_KEY": encryption_key,
    }

    return config


def get_fernet() -> Fernet:
    """Get a Fernet instance for encryption/decryption."""
    config = load_config()
    return Fernet(config["ENCRYPTION_KEY"].encode())


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value using Fernet."""
    fernet = get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    fernet = get_fernet()
    return fernet.decrypt(ciphertext.encode()).decode()
