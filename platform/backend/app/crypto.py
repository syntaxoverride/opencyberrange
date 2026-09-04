"""
Encryption utilities for sensitive data
Provides symmetric encryption for WireGuard private keys and other secrets
"""

from cryptography.fernet import Fernet, InvalidToken
from app.config import settings
import logging

logger = logging.getLogger(__name__)

_fernet_instance = None


def get_fernet():
    """
    Get Fernet instance for encryption/decryption.
    Caches the instance for performance.
    
    Raises:
        ValueError: If WG_ENCRYPTION_KEY is not set
    """
    global _fernet_instance
    
    if _fernet_instance is not None:
        return _fernet_instance
    
    if not settings.WG_ENCRYPTION_KEY:
        raise ValueError(
            "WG_ENCRYPTION_KEY must be set for WireGuard key encryption. "
            "Generate with: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    
    try:
        key = settings.WG_ENCRYPTION_KEY.encode()
        _fernet_instance = Fernet(key)
        return _fernet_instance
    except Exception as e:
        raise ValueError(f"Invalid WG_ENCRYPTION_KEY format: {e}")


def encrypt_private_key(private_key: str) -> str:
    """
    Encrypt a WireGuard private key for secure storage.
    
    Args:
        private_key: The plaintext WireGuard private key
        
    Returns:
        The encrypted key as a base64 string (Fernet token)
    """
    f = get_fernet()
    encrypted = f.encrypt(private_key.encode())
    return encrypted.decode()


def decrypt_private_key(encrypted_key: str) -> str:
    """
    Decrypt a WireGuard private key from storage.
    
    Args:
        encrypted_key: The encrypted key (Fernet token)
        
    Returns:
        The plaintext WireGuard private key
        
    Raises:
        ValueError: If decryption fails (invalid key or corrupted data)
    """
    f = get_fernet()
    try:
        decrypted = f.decrypt(encrypted_key.encode())
        return decrypted.decode()
    except InvalidToken:
        raise ValueError("Failed to decrypt private key - invalid encryption key or corrupted data")


def encrypt_secret(value: str) -> str:
    """Encrypt an arbitrary secret (e.g. an instructor's BYO API key).

    Generic Fernet encryption; same key/scheme as the WireGuard helpers above.
    """
    return get_fernet().encrypt(value.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Decrypt a secret produced by encrypt_secret."""
    f = get_fernet()
    try:
        return f.decrypt(token.encode()).decode()
    except InvalidToken:
        raise ValueError("Failed to decrypt secret - invalid encryption key or corrupted data")


def is_encrypted(value: str) -> bool:
    """
    Check if a value appears to be Fernet-encrypted.
    Fernet tokens start with 'gAAAAA'.
    
    Args:
        value: The string to check
        
    Returns:
        True if the value appears to be encrypted
    """
    return value.startswith('gAAAAA')


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    Use this to generate WG_ENCRYPTION_KEY for .env file.
    
    Returns:
        A new Fernet key as a string
    """
    return Fernet.generate_key().decode()

