"""P2 — Auth endpoint testleri: register, login, /me, branding."""
import uuid
import pytest


def _email(suffix: str = "") -> str:
    return f"user_{uuid.uuid4().hex[:8]}@authtest{suffix}.com"


# ── Kayıt ─────────────────────────────────────────────────────────────────────

async def test_register_201(http):
    r = await http.post("/api/auth/register", json={
        "email": _email(),
        "sifre": "testpass123",
        "ad_soyad": "Test Kullanici",
    })
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "id" in data["kullanici"]
    assert "tenant_id" in data["kullanici"]
    assert "password_hash" not in data["kullanici"]


async def test_register_ilk_kullanici_admin(http):
    domain = f"admintest-{uuid.uuid4().hex[:6]}.com"
    r = await http.post("/api/auth/register", json={
        "email": f"admin@{domain}",
        "sifre": "testpass123",
        "ad_soyad": "İlk Kullanici",
    })
    assert r.status_code == 201
    assert r.json()["kullanici"]["rol"] == "admin"


async def test_register_ikinci_kullanici_kullanici_rolu(http):
    domain = f"roltest-{uuid.uuid4().hex[:6]}.com"
    await http.post("/api/auth/register", json={
        "email": f"admin@{domain}", "sifre": "testpass123", "ad_soyad": "Admin",
    })
    r2 = await http.post("/api/auth/register", json={
        "email": f"user@{domain}", "sifre": "testpass123", "ad_soyad": "User",
    })
    assert r2.status_code == 201
    assert r2.json()["kullanici"]["rol"] == "kullanici"


async def test_register_duplicate_email_409(http):
    email = _email("-dup")
    await http.post("/api/auth/register", json={
        "email": email, "sifre": "testpass123", "ad_soyad": "Birinci",
    })
    r2 = await http.post("/api/auth/register", json={
        "email": email, "sifre": "testpass123", "ad_soyad": "İkinci",
    })
    assert r2.status_code == 409


async def test_register_kisa_sifre_422(http):
    r = await http.post("/api/auth/register", json={
        "email": _email(), "sifre": "kisa", "ad_soyad": "Test",
    })
    assert r.status_code == 422


async def test_register_gecersiz_email_422(http):
    r = await http.post("/api/auth/register", json={
        "email": "gecersiz-email", "sifre": "testpass123", "ad_soyad": "Test",
    })
    assert r.status_code == 422


async def test_register_domain_tenant_olusturur(http):
    domain = f"tenantcreate-{uuid.uuid4().hex[:6]}.com"
    r = await http.post("/api/auth/register", json={
        "email": f"ilk@{domain}", "sifre": "testpass123", "ad_soyad": "Test",
    })
    tid = r.json()["kullanici"]["tenant_id"]

    # Aynı domain'den ikinci kullanıcı → aynı tenant
    r2 = await http.post("/api/auth/register", json={
        "email": f"ikinci@{domain}", "sifre": "testpass123", "ad_soyad": "Test 2",
    })
    assert r2.json()["kullanici"]["tenant_id"] == tid


# ── Giriş ─────────────────────────────────────────────────────────────────────

async def test_login_dogru_credentials_200(http):
    email = _email("-login")
    await http.post("/api/auth/register", json={
        "email": email, "sifre": "testpass123", "ad_soyad": "Login Test",
    })
    r = await http.post("/api/auth/login", json={"email": email, "sifre": "testpass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_login_yanlis_sifre_401(http):
    email = _email("-wrong")
    await http.post("/api/auth/register", json={
        "email": email, "sifre": "dogrusifre1", "ad_soyad": "Test",
    })
    r = await http.post("/api/auth/login", json={"email": email, "sifre": "yanlissifre"})
    assert r.status_code == 401


async def test_login_olmayan_kullanici_401(http):
    r = await http.post("/api/auth/login", json={
        "email": "yok@olmayan.com", "sifre": "testpass123",
    })
    assert r.status_code == 401


# ── /me ───────────────────────────────────────────────────────────────────────

async def test_me_gecerli_token(http, user_a):
    r = await http.get("/api/auth/me", headers=user_a["headers"])
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == user_a["email"]
    assert data["tenant_id"] == user_a["tenant_id"]
    assert "tenant_adi" in data
    assert "password_hash" not in data


async def test_me_token_olmadan_401(http):
    r = await http.get("/api/auth/me")
    assert r.status_code == 401


async def test_me_gecersiz_token_401(http):
    r = await http.get("/api/auth/me", headers={"Authorization": "Bearer gecersiz.token.xxx"})
    assert r.status_code == 401


# ── Branding ──────────────────────────────────────────────────────────────────

async def test_branding_varsayilan_doner(http, user_a):
    """LLM yapılandırılmamışsa varsayılan renk paleti dönmeli."""
    r = await http.get("/api/auth/branding", headers=user_a["headers"])
    assert r.status_code == 200
    data = r.json()
    assert "light" in data and "dark" in data
    assert "brand_600" in data["light"]
    assert "brand_600" in data["dark"]
    assert data["light"]["brand_600"].startswith("#")


async def test_branding_token_olmadan_401(http):
    r = await http.get("/api/auth/branding")
    assert r.status_code == 401
