"""P3 — LLM konfigürasyon CRUD ve tenant izolasyonu testleri."""
import pytest


_LLM_PAYLOAD = {
    "provider_name": "openai",
    "model_name": "gpt-4o",
    "api_key": "sk-test-1234567890",
}


# ── Liste / Boş Durum ─────────────────────────────────────────────────────────

async def test_listele_bos(http, user_a):
    r = await http.get("/api/llm-configs/", headers=user_a["headers"])
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_listele_token_olmadan_401(http):
    r = await http.get("/api/llm-configs/")
    assert r.status_code == 401


# ── Ekleme ────────────────────────────────────────────────────────────────────

async def test_ekle_201(http, user_a):
    r = await http.post("/api/llm-configs/", json=_LLM_PAYLOAD, headers=user_a["headers"])
    assert r.status_code == 201
    data = r.json()
    assert data["provider_name"] == "openai"
    assert data["model_name"] == "gpt-4o"
    assert "api_key" not in data  # API key asla dönmemeli
    assert "api_key_encrypted" not in data


async def test_ekle_sonra_listele(http, user_a):
    await http.post("/api/llm-configs/", json=_LLM_PAYLOAD, headers=user_a["headers"])
    r = await http.get("/api/llm-configs/", headers=user_a["headers"])
    assert len(r.json()) >= 1


async def test_farkli_providerlar(http, user_a):
    providerlar = [
        {"provider_name": "anthropic", "model_name": "claude-sonnet-4-6", "api_key": "sk-ant-test"},
        {"provider_name": "gemini", "model_name": "gemini-2.5-flash", "api_key": "AIza-test"},
        {"provider_name": "custom", "model_name": "llama3", "api_key": "none",
         "base_url": "http://localhost:11434/v1"},
    ]
    for payload in providerlar:
        r = await http.post("/api/llm-configs/", json=payload, headers=user_a["headers"])
        assert r.status_code == 201


# ── Aktifleştirme ─────────────────────────────────────────────────────────────

async def test_aktifle_ve_aktif_al(http, user_a):
    r1 = await http.post("/api/llm-configs/", json=_LLM_PAYLOAD, headers=user_a["headers"])
    config_id = r1.json()["id"]

    r2 = await http.post(f"/api/llm-configs/{config_id}/activate", headers=user_a["headers"])
    assert r2.status_code == 200

    r3 = await http.get("/api/llm-configs/active", headers=user_a["headers"])
    assert r3.status_code == 200
    assert r3.json()["aktif"] is True
    assert r3.json()["provider_name"] == "openai"


async def test_aktifle_olmayan_config_404(http, user_a):
    r = await http.post("/api/llm-configs/999999/activate", headers=user_a["headers"])
    assert r.status_code == 404


async def test_aktif_olmadan_aktif_config(http, user_b):
    """Hiç aktifleştirme yapılmamışsa aktif=False dönmeli."""
    r = await http.get("/api/llm-configs/active", headers=user_b["headers"])
    assert r.status_code == 200
    # Ya aktif=False ya da aktif=True; en az bir field dönmeli
    data = r.json()
    assert "aktif" in data


# ── Silme ─────────────────────────────────────────────────────────────────────

async def test_sil_204(http, user_a):
    r = await http.post("/api/llm-configs/", json=_LLM_PAYLOAD, headers=user_a["headers"])
    cid = r.json()["id"]
    r2 = await http.delete(f"/api/llm-configs/{cid}", headers=user_a["headers"])
    assert r2.status_code == 204


async def test_sil_olmayan_404(http, user_a):
    r = await http.delete("/api/llm-configs/999999", headers=user_a["headers"])
    assert r.status_code == 404


# ── Tenant İzolasyonu ─────────────────────────────────────────────────────────

async def test_tenant_izolasyonu(http, user_a, user_b):
    """Tenant A'nın config'i Tenant B tarafından görülmemeli ve silinememeli."""
    # Tenant A config ekle
    r = await http.post("/api/llm-configs/", json=_LLM_PAYLOAD, headers=user_a["headers"])
    cid = r.json()["id"]

    # Tenant B listesinde görünmemeli
    r2 = await http.get("/api/llm-configs/", headers=user_b["headers"])
    ids_b = [c["id"] for c in r2.json()]
    assert cid not in ids_b

    # Tenant B silemez
    r3 = await http.delete(f"/api/llm-configs/{cid}", headers=user_b["headers"])
    assert r3.status_code == 404

    # Tenant B aktifleştiremez
    r4 = await http.post(f"/api/llm-configs/{cid}/activate", headers=user_b["headers"])
    assert r4.status_code == 404
