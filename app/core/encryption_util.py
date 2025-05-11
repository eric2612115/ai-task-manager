import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.core.config import settings

# Use a secret key from environment variables or settings
# In production, consider using a more robust key management solution
SECRET_KEY = settings.ENCRYPTION_SECRET_KEY.encode()
SALT = settings.ENCRYPTION_SALT.encode()

# Derive a fixed-length key using PBKDF2
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=SALT,
    iterations=100000,
)
KEY = base64.urlsafe_b64encode(kdf.derive(SECRET_KEY))
CIPHER = Fernet(KEY)

def encrypt(value: str) -> str:
    """Encrypt a string value, returns the encrypted text"""
    if not value:
        return value
    return CIPHER.encrypt(value.encode()).decode()

def decrypt(encrypted_value: str) -> str:
    """Decrypt an encrypted text, returns the original string"""
    if not encrypted_value:
        return encrypted_value
    return CIPHER.decrypt(encrypted_value.encode()).decode() 