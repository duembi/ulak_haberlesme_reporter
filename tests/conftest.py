"""Paylaşılan test fixture'ları."""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

import src.database as db_mod


# ── Geçici Test DB ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def test_db(tmp_path_factory):
    """Tüm testler için tek bir geçici SQLite DB — session boyunca paylaşılır."""
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    original = db_mod.DB_PATH
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    yield db_path
    db_mod.DB_PATH = original


# ── HTTP İstemci ──────────────────────────────────────────────────────────────

@pytest.fixture
async def http(test_db):
    """Kimlik doğrulamasız AsyncClient."""
    from api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Kullanıcı Yardımcıları ────────────────────────────────────────────────────

def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@testcorp-{uuid.uuid4().hex[:6]}.com"


async def _kayit_ol(http: AsyncClient, email: str, sifre: str = "testpass123",
                    ad_soyad: str = "Test Kullanici", kurum_adi: str = "") -> dict:
    """Kayıt olur; başarılıysa response json döner."""
    r = await http.post("/api/auth/register", json={
        "email": email,
        "sifre": sifre,
        "ad_soyad": ad_soyad,
        "kurum_adi": kurum_adi,
    })
    assert r.status_code == 201, f"Kayıt başarısız: {r.text}"
    return r.json()


@pytest.fixture
async def user_a(http) -> dict:
    """Tenant-A için admin kullanıcı — token + tenant_id içerir."""
    data = await _kayit_ol(http, f"admin@tenant-a-{uuid.uuid4().hex[:6]}.com",
                            ad_soyad="Admin A", kurum_adi="Tenant A Corp")
    return {
        "token": data["access_token"],
        "tenant_id": data["kullanici"]["tenant_id"],
        "email": data["kullanici"]["email"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


@pytest.fixture
async def user_b(http) -> dict:
    """Tenant-B için admin kullanıcı — token + tenant_id içerir."""
    data = await _kayit_ol(http, f"admin@tenant-b-{uuid.uuid4().hex[:6]}.com",
                            ad_soyad="Admin B", kurum_adi="Tenant B Corp")
    return {
        "token": data["access_token"],
        "tenant_id": data["kullanici"]["tenant_id"],
        "email": data["kullanici"]["email"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }
