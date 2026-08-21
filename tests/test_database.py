"""P1 — Veritabanı katmanı birim testleri."""
import pytest
from src.database import (
    tenant_bul_veya_olustur, tenant_al,
    tenant_brand_colors_al, tenant_brand_colors_kaydet,
    kullanici_ekle, kullanici_bul, kullanici_sayisi,
    tenant_llm_config_ekle, tenant_llm_config_al,
    tenant_llm_config_listele, tenant_llm_config_aktifle, tenant_llm_config_sil,
    tenant_rakip_ekle, tenant_rakip_listele, tenant_rakip_guncelle, tenant_rakip_sil,
    report_job_olustur, report_job_al, report_job_guncelle, report_job_listele,
    mail_ekle, mail_listesi_al, mail_sil,
    rakip_listesi_al, rakip_ekle,
)


# ── Tenant ────────────────────────────────────────────────────────────────────

def test_tenant_bul_veya_olustur_yeni():
    tid = tenant_bul_veya_olustur("db-test-firm.com", "DB Test Firm")
    assert isinstance(tid, int) and tid > 0


def test_tenant_bul_veya_olustur_idempotent():
    tid1 = tenant_bul_veya_olustur("idempotent-firm.com", "Idempotent Corp")
    tid2 = tenant_bul_veya_olustur("idempotent-firm.com", "Idempotent Corp")
    assert tid1 == tid2


def test_tenant_al():
    tid = tenant_bul_veya_olustur("tenant-al-test.com", "Tenant Al Test")
    t = tenant_al(tid)
    assert t is not None
    assert t["domain"] == "tenant-al-test.com"
    assert t["ad"] == "Tenant Al Test"


def test_tenant_al_olmayan():
    assert tenant_al(999999) is None


# ── Brand Colors ──────────────────────────────────────────────────────────────

def test_brand_colors_kaydet_al():
    tid = tenant_bul_veya_olustur("brand-test.com", "Brand Test")
    colors = {
        "light": {"brand_600": "#1a56db", "sidebar": "#1e293b"},
        "dark":  {"brand_600": "#3b82f6", "sidebar": "#020617"},
    }
    tenant_brand_colors_kaydet(tid, colors)
    result = tenant_brand_colors_al(tid)
    assert result is not None
    assert result["light"]["brand_600"] == "#1a56db"
    assert result["dark"]["brand_600"] == "#3b82f6"


def test_brand_colors_al_bos_tenant():
    tid = tenant_bul_veya_olustur("no-colors.com", "No Colors Corp")
    assert tenant_brand_colors_al(tid) is None


# ── Kullanıcı ─────────────────────────────────────────────────────────────────

def test_kullanici_ekle_ve_bul():
    tid = tenant_bul_veya_olustur("user-test.com", "User Test Corp")
    uid = kullanici_ekle(tid, "unit@user-test.com", "hash123", "Unit Tester", "admin")
    assert uid is not None
    u = kullanici_bul("unit@user-test.com")
    assert u["email"] == "unit@user-test.com"
    assert u["rol"] == "admin"
    assert u["tenant_id"] == tid


def test_kullanici_ekle_duplicate_email():
    tid = tenant_bul_veya_olustur("dup-user.com", "Dup Corp")
    kullanici_ekle(tid, "dup@dup-user.com", "hash", "Dup User")
    uid2 = kullanici_ekle(tid, "dup@dup-user.com", "hash", "Dup User 2")
    assert uid2 is None


def test_kullanici_sayisi():
    tid = tenant_bul_veya_olustur("count-test.com", "Count Corp")
    assert kullanici_sayisi(tid) == 0
    kullanici_ekle(tid, "u1@count-test.com", "h", "U1")
    assert kullanici_sayisi(tid) == 1
    kullanici_ekle(tid, "u2@count-test.com", "h", "U2")
    assert kullanici_sayisi(tid) == 2


# ── LLM Config ────────────────────────────────────────────────────────────────

def test_llm_config_ekle_listele():
    tid = tenant_bul_veya_olustur("llm-cfg.com", "LLM Corp")
    cid = tenant_llm_config_ekle(tid, "openai", "gpt-4o", "enc_key_xxx")
    configs = tenant_llm_config_listele(tid)
    assert any(c["id"] == cid for c in configs)


def test_llm_config_aktifle():
    tid = tenant_bul_veya_olustur("llm-aktif.com", "LLM Aktif Corp")
    cid1 = tenant_llm_config_ekle(tid, "openai", "gpt-4o", "enc1")
    cid2 = tenant_llm_config_ekle(tid, "gemini", "gemini-flash", "enc2")

    ok = tenant_llm_config_aktifle(cid2, tid)
    assert ok is True

    aktif = tenant_llm_config_al(tid)
    assert aktif["id"] == cid2
    assert aktif["aktif"] == 1

    ok2 = tenant_llm_config_aktifle(cid1, tid)
    assert ok2 is True
    aktif2 = tenant_llm_config_al(tid)
    assert aktif2["id"] == cid1


def test_llm_config_sil():
    tid = tenant_bul_veya_olustur("llm-sil.com", "LLM Sil Corp")
    cid = tenant_llm_config_ekle(tid, "anthropic", "claude-sonnet-4-6", "enc")
    ok = tenant_llm_config_sil(cid, tid)
    assert ok is True
    configs = tenant_llm_config_listele(tid)
    assert not any(c["id"] == cid for c in configs)


def test_llm_config_baska_tenant_silemez():
    tid1 = tenant_bul_veya_olustur("sec-llm-a.com", "Sec A")
    tid2 = tenant_bul_veya_olustur("sec-llm-b.com", "Sec B")
    cid = tenant_llm_config_ekle(tid1, "openai", "gpt-4o", "enc")
    ok = tenant_llm_config_sil(cid, tid2)
    assert ok is False


# ── Tenant Competitors ────────────────────────────────────────────────────────

def test_tenant_rakip_ekle_listele():
    tid = tenant_bul_veya_olustur("comp-test.com", "Comp Corp")
    ok = tenant_rakip_ekle(tid, "RakipFirma", "Açıklama", "Türkiye", "Telekom")
    assert ok is True
    rakipler = tenant_rakip_listele(tid)
    assert any(r["ad"] == "RakipFirma" for r in rakipler)


def test_tenant_rakip_duplicate():
    tid = tenant_bul_veya_olustur("comp-dup.com", "Comp Dup")
    tenant_rakip_ekle(tid, "Tekrar", "Açıklama", "", "")
    ok2 = tenant_rakip_ekle(tid, "Tekrar", "Farklı", "", "")
    assert ok2 is False


def test_tenant_rakip_guncelle():
    tid = tenant_bul_veya_olustur("comp-upd.com", "Comp Upd")
    tenant_rakip_ekle(tid, "GuncelleFirma", "eski", "TR", "IT")
    rakipler = tenant_rakip_listele(tid, sadece_aktif=False)
    rid = next(r["id"] for r in rakipler if r["ad"] == "GuncelleFirma")

    ok = tenant_rakip_guncelle(rid, tid, aciklama="yeni açıklama")
    assert ok is True
    guncellendi = next(r for r in tenant_rakip_listele(tid, sadece_aktif=False) if r["id"] == rid)
    assert guncellendi["aciklama"] == "yeni açıklama"


def test_tenant_rakip_sil():
    tid = tenant_bul_veya_olustur("comp-del.com", "Comp Del")
    tenant_rakip_ekle(tid, "SilinecekFirma", "", "", "")
    rakipler = tenant_rakip_listele(tid, sadece_aktif=False)
    rid = next(r["id"] for r in rakipler if r["ad"] == "SilinecekFirma")

    ok = tenant_rakip_sil(rid, tid)
    assert ok is True
    assert not any(r["id"] == rid for r in tenant_rakip_listele(tid, sadece_aktif=False))


def test_tenant_rakip_izolasyonu():
    tid1 = tenant_bul_veya_olustur("iso-comp-a.com", "Iso A")
    tid2 = tenant_bul_veya_olustur("iso-comp-b.com", "Iso B")
    tenant_rakip_ekle(tid1, "SadeceBenimRakibim", "", "", "")
    rakipler_b = tenant_rakip_listele(tid2)
    assert not any(r["ad"] == "SadeceBenimRakibim" for r in rakipler_b)


# ── Report Jobs ───────────────────────────────────────────────────────────────

def test_report_job_olustur_al():
    tid = tenant_bul_veya_olustur("job-test.com", "Job Corp")
    jid = report_job_olustur(tid, gun=7, kapsam="hepsi", rakipler=[], mail_alicilari=[])
    assert jid > 0
    job = report_job_al(jid, tid)
    assert job is not None
    assert job["durum"] == "kuyrukta"
    assert job["gun"] == 7


def test_report_job_guncelle():
    tid = tenant_bul_veya_olustur("job-upd.com", "Job Upd")
    jid = report_job_olustur(tid, 7, "hepsi", [], [])
    ok = report_job_guncelle(jid, durum="calisiyor", baslangic_at="2026-01-01T08:00:00")
    assert ok is True
    job = report_job_al(jid, tid)
    assert job["durum"] == "calisiyor"


def test_report_job_baska_tenant_alamaz():
    tid1 = tenant_bul_veya_olustur("job-sec-a.com", "Job Sec A")
    tid2 = tenant_bul_veya_olustur("job-sec-b.com", "Job Sec B")
    jid = report_job_olustur(tid1, 7, "hepsi", [], [])
    job = report_job_al(jid, tid2)
    assert job is None


def test_report_job_listele():
    tid = tenant_bul_veya_olustur("job-list.com", "Job List")
    report_job_olustur(tid, 7, "hepsi", [], [])
    report_job_olustur(tid, 30, "sadece_ben", [], [])
    jobs = report_job_listele(tid)
    assert len(jobs) >= 2


# ── Global Rakip Kataloğu ─────────────────────────────────────────────────────

def test_rakip_listesi_al_seed_data():
    """init_db() seed ile 25+ rakip yüklemiş olmalı."""
    rakipler = rakip_listesi_al()
    assert len(rakipler) >= 20


def test_rakip_ekle_duplicate():
    ok1 = rakip_ekle("UniqueTestRakip", "unique test query", "en", "ABD", "Test açıklama")
    ok2 = rakip_ekle("UniqueTestRakip", "unique test query 2", "en", "ABD", "Farklı açıklama")
    assert ok1 is True
    assert ok2 is False  # UNIQUE(ad) kısıtı


# ── Mail Listesi ──────────────────────────────────────────────────────────────

def test_mail_ekle_listele():
    tid = tenant_bul_veya_olustur("mail-test.com", "Mail Corp")
    ok = mail_ekle("Test Alici", "alici@mail-test.com", tenant_id=tid)
    assert ok is True
    liste = mail_listesi_al(tenant_id=tid)
    assert any(m["email"] == "alici@mail-test.com" for m in liste)


def test_mail_tenant_izolasyonu():
    tid1 = tenant_bul_veya_olustur("mail-iso-a.com", "Mail Iso A")
    tid2 = tenant_bul_veya_olustur("mail-iso-b.com", "Mail Iso B")
    mail_ekle("A Alici", "a@mail-iso-a.com", tenant_id=tid1)
    liste_b = mail_listesi_al(tenant_id=tid2)
    assert not any(m["email"] == "a@mail-iso-a.com" for m in liste_b)
