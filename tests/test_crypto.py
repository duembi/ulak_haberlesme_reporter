"""P0 — Şifreleme / çözme katmanı testleri."""
import pytest
from src.crypto import encrypt, decrypt


def test_encrypt_decrypt_round_trip():
    plain = "sk-test-abc123"
    assert decrypt(encrypt(plain)) == plain


def test_encrypt_produces_different_ciphertext_each_time():
    plain = "same_value"
    c1 = encrypt(plain)
    c2 = encrypt(plain)
    assert c1 != c2  # Fernet her seferinde rastgele IV üretir


def test_decrypt_invalid_raises():
    with pytest.raises(Exception):
        decrypt("bu_gecersiz_bir_ciphertext")


def test_empty_string():
    assert decrypt(encrypt("")) == ""


def test_unicode():
    plain = "Türkçe şifre değeri 日本語"
    assert decrypt(encrypt(plain)) == plain
