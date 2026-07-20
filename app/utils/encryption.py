"""Encryption utilities for Aegis AI."""

from cryptography.fernet import Fernet
from app.core.config import get_fernet


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key using Fernet symmetric encryption.
    
    Args:
        api_key: The plaintext API key to encrypt.
        
    Returns:
        str: The encrypted API key (base64 encoded).
    """
    fernet = get_fernet()
    encrypted = fernet.encrypt(api_key.encode())
    return encrypted.decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an API key using Fernet symmetric encryption.
    
    Args:
        encrypted_key: The encrypted API key (base64 encoded).
        
    Returns:
        str: The decrypted plaintext API key.
    """
    fernet = get_fernet()
    decrypted = fernet.decrypt(encrypted_key.encode())
    return decrypted.decode()


# Generic encryption/decryption functions (aliases for any sensitive value)
def encrypt_value(value: str) -> str:
    """
    Encrypt any sensitive value using Fernet symmetric encryption.
    
    Args:
        value: The plaintext value to encrypt.
        
    Returns:
        str: The encrypted value (base64 encoded).
    """
    return encrypt_api_key(value)


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt any sensitive value using Fernet symmetric encryption.
    
    Args:
        encrypted_value: The encrypted value (base64 encoded).
        
    Returns:
        str: The decrypted plaintext value.
    """
    return decrypt_api_key(encrypted_value)
