"""P4 — Tenant rakip (AI destekli) CRUD ve tenant izolasyonu testleri."""
import pytest
from unittest.mock import AsyncMock, patch


_RAKIP = {
    "ad": "TestRakipFirma",
    "aciklama": "Test açıklama",
    "bolge": "Türkiye",
    "sektor": "Telekom",
}


# ── Liste / Boş Durum ─────────────────────────────────────────────────────────

async def test_listele_bos(http, user_a):
    r = await http.get("/api/tenant-competitors/", headers=user_a["headers"])
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_listele_token_olmadan_401(http):
    r = await http.get("/api/tenant-competitors/")
    assert r.status_code == 401


# ── Ekleme ────────────────────────────────────────────────────────────────────

async def test_ekle_201(http, user_a):
    r = await http.post("/api/tenant-competitors/", json=_RAKIP, headers=user_a["headers"])
    assert r.status_code == 201
    data = r.json()
    assert data["ad"] == "TestRakipFirma"
    assert data["bolge"] == "Türkiye"
    assert data["tenant_id"] == user_a["tenant_id"]
    assert data["ai_onerisi"] is False  # Manuel ekleme


async def test_ekle_duplicate_409(http, user_a):
    rakip = {**_RAKIP, "ad": "DupRakipFirma"}
    await http.post("/api/tenant-competitors/", json=rakip, headers=user_a["headers"])
    r2 = await http.post("/api/tenant-competitors/", json=rakip, headers=user_a["headers"])
    assert r2.status_code == 409


# ── Güncelleme ────────────────────────────────────────────────────────────────

async def test_guncelle_200(http, user_a):
    rakip = {**_RAKIP, "ad": "GuncellenecekFirma"}
    r = await http.post("/api/tenant-competitors/", json=rakip, headers=user_a["headers"])
    rid = r.json()["id"]

    r2 = await http.patch(
        f"/api/tenant-competitors/{rid}",
        json={"aciklama": "Yeni açıklama", "sektor": "Uzay"},
        headers=user_a["headers"],
    )
    assert r2.status_code == 200
    assert r2.json()["aciklama"] == "Yeni açıklama"
    assert r2.json()["sektor"] == "Uzay"


async def test_guncelle_bos_body_400(http, user_a):
    rakip = {**_RAKIP, "ad": "BosBodyFirma"}
    r = await http.post("/api/tenant-competitors/", json=rakip, headers=user_a["headers"])
    rid = r.json()["id"]

    r2 = await http.patch(f"/api/tenant-competitors/{rid}", json={}, headers=user_a["headers"])
    assert r2.status_code == 400


async def test_guncelle_olmayan_404(http, user_a):
    r = await http.patch(
        "/api/tenant-competitors/999999",
        json={"aciklama": "test"},
        headers=user_a["headers"],
    )
    assert r.status_code == 404


async def test_aktif_pasif_toggle(http, user_a):
    rakip = {**_RAKIP, "ad": "AktifToggleFirma"}
    r = await http.post("/api/tenant-competitors/", json=rakip, headers=user_a["headers"])
    rid = r.json()["id"]

    # Pasife al
    r2 = await http.patch(
        f"/api/tenant-competitors/{rid}",
        json={"aktif": False},
        headers=user_a["headers"],
    )
    assert r2.status_code == 200

    # Aktif listede görünmemeli
    r3 = await http.get("/api/tenant-competitors/", headers=user_a["headers"])
    ids = [item["id"] for item in r3.json()]
    assert rid not in ids


# ── Silme ─────────────────────────────────────────────────────────────────────

async def test_sil_204(http, user_a):
    rakip = {**_RAKIP, "ad": "SilinecekRakip"}
    r = await http.post("/api/tenant-competitors/", json=rakip, headers=user_a["headers"])
    rid = r.json()["id"]

    r2 = await http.delete(f"/api/tenant-competitors/{rid}", headers=user_a["headers"])
    assert r2.status_code == 204

    r3 = await http.get("/api/tenant-competitors/?sadece_aktif=false", headers=user_a["headers"])
    ids = [item["id"] for item in r3.json()]
    assert rid not in ids


async def test_sil_olmayan_404(http, user_a):
    r = await http.delete("/api/tenant-competitors/999999", headers=user_a["headers"])
    assert r.status_code == 404


# ── Tenant İzolasyonu ─────────────────────────────────────────────────────────

async def test_tenant_izolasyonu(http, user_a, user_b):
    """Tenant A'nın rakibi Tenant B tarafından görülmemeli ve silinememeli."""
    rakip = {**_RAKIP, "ad": "SaddeceBenimRakibim"}
    r = await http.post("/api/tenant-competitors/", json=rakip, headers=user_a["headers"])
    rid = r.json()["id"]

    # Tenant B listesinde yok
    r2 = await http.get("/api/tenant-competitors/", headers=user_b["headers"])
    ids_b = [item["id"] for item in r2.json()]
    assert rid not in ids_b

    # Tenant B silemiyor
    r3 = await http.delete(f"/api/tenant-competitors/{rid}", headers=user_b["headers"])
    assert r3.status_code == 404

    # Tenant B güncelleyemiyor
    r4 = await http.patch(
        f"/api/tenant-competitors/{rid}",
        json={"aciklama": "Hack denemesi"},
        headers=user_b["headers"],
    )
    assert r4.status_code == 404


# ── AI Analiz (Mock) ──────────────────────────────────────────────────────────

async def test_analiz_baslat_202(http, user_a):
    """AI analizi arka planda başlatılır — LLM mock'lanıyor."""
    mock_llm = AsyncMock()
    mock_llm.generate_text = AsyncMock(return_value=
        '{"rakipler": [{"ad": "MockRakip", "aciklama": "mock", "bolge": "TR", "sektor": "IT"}]}')

    with patch("api.routers.tenant_competitors.LLMFactory.for_tenant",
               AsyncMock(return_value=mock_llm)):
        r = await http.post(
            "/api/tenant-competitors/analyze?sektor=Telekom",
            headers=user_a["headers"],
        )
    assert r.status_code == 202
    assert "mesaj" in r.json()
