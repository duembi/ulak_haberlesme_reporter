from cryptography.fernet import Fernet
from config.settings import BASE_DIR, ENCRYPTION_KEY

_KEY_FILE = BASE_DIR / ".encryption_key"
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet
    if ENCRYPTION_KEY:
        _fernet = Fernet(ENCRYPTION_KEY.encode())
    elif _KEY_FILE.exists():
        _fernet = Fernet(_KEY_FILE.read_bytes())
    else:
        key = Fernet.generate_key()
        _KEY_FILE.write_bytes(key)
        _fernet = Fernet(key)
    return _fernet


def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
