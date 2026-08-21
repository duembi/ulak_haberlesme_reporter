"""P5 — Rapor işleri (asenkron kuyruk) testleri."""
import pytest
from unittest.mock import patch, AsyncMock


_JOB_PAYLOAD = {
    "gun": 7,
    "kapsam": "hepsi",
    "rakipler": [],
    "mail_alicilari": [],
}


# ── Liste ─────────────────────────────────────────────────────────────────────

async def test_listele_bos(http, user_a):
    r = await http.get("/api/report-jobs/", headers=user_a["headers"])
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_listele_token_olmadan_401(http):
    r = await http.get("/api/report-jobs/")
    assert r.status_code == 401


# ── Oluşturma ─────────────────────────────────────────────────────────────────

async def test_olustur_202(http, user_a):
    """Pipeline subprocess'i mock'layarak job oluşturur."""
    with patch("api.routers.report_jobs._rapor_uret", AsyncMock(return_value=None)):
        r = await http.post("/api/report-jobs/", json=_JOB_PAYLOAD, headers=user_a["headers"])
    assert r.status_code == 202
    data = r.json()
    assert data["durum"] in ("kuyrukta", "calisiyor")
    assert data["gun"] == 7
    assert data["kapsam"] == "hepsi"
    assert data["tenant_id"] == user_a["tenant_id"]


async def test_olustur_gecersiz_gun_400(http, user_a):
    payload = {**_JOB_PAYLOAD, "gun": 5}
    with patch("api.routers.report_jobs._rapor_uret", AsyncMock(return_value=None)):
        r = await http.post("/api/report-jobs/", json=payload, headers=user_a["headers"])
    assert r.status_code == 400


async def test_olustur_gun_secenekleri(http, user_a):
    """Geçerli: 3, 7, 15, 30 gün."""
    for gun in (3, 7, 15, 30):
        with patch("api.routers.report_jobs._rapor_uret", AsyncMock(return_value=None)):
            r = await http.post("/api/report-jobs/", json={**_JOB_PAYLOAD, "gun": gun},
                                headers=user_a["headers"])
        assert r.status_code == 202, f"gun={gun} için 202 beklendi"


# ── Durum / Tekil Al ──────────────────────────────────────────────────────────

async def test_durum_al(http, user_a):
    with patch("api.routers.report_jobs._rapor_uret", AsyncMock(return_value=None)):
        r = await http.post("/api/report-jobs/", json=_JOB_PAYLOAD, headers=user_a["headers"])
    job_id = r.json()["id"]

    r2 = await http.get(f"/api/report-jobs/{job_id}", headers=user_a["headers"])
    assert r2.status_code == 200
    assert r2.json()["id"] == job_id


async def test_durum_olmayan_404(http, user_a):
    r = await http.get("/api/report-jobs/999999", headers=user_a["headers"])
    assert r.status_code == 404


# ── Tenant İzolasyonu ─────────────────────────────────────────────────────────

async def test_tenant_izolasyonu(http, user_a, user_b):
    """Tenant B, Tenant A'nın jobunu görememeli."""
    with patch("api.routers.report_jobs._rapor_uret", AsyncMock(return_value=None)):
        r = await http.post("/api/report-jobs/", json=_JOB_PAYLOAD, headers=user_a["headers"])
    job_id = r.json()["id"]

    # Tenant B bu job'u görememeli
    r2 = await http.get(f"/api/report-jobs/{job_id}", headers=user_b["headers"])
    assert r2.status_code == 404


# ── İndirme ───────────────────────────────────────────────────────────────────

async def test_indir_tamamlanmamis_404(http, user_a):
    """Kuyrukta bekleyen job için dosya indirme 404 dönmeli."""
    with patch("api.routers.report_jobs._rapor_uret", AsyncMock(return_value=None)):
        r = await http.post("/api/report-jobs/", json=_JOB_PAYLOAD, headers=user_a["headers"])
    job_id = r.json()["id"]

    r2 = await http.get(f"/api/report-jobs/{job_id}/download", headers=user_a["headers"])
    assert r2.status_code == 404
