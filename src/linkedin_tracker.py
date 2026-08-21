"""
Ulak Haberleşme LinkedIn Takip Modülü

Ulak Haberleşme A.Ş.'nin resmi LinkedIn şirket sayfasından son gönderileri çeker.
Teknik not: LinkedIn JavaScript render ettiği için doğrudan sayfa çekimi sınırlıdır.
DuckDuckGo arama + trafilatura ile public içerik elde edilir; gerçek etkileşim
sayıları (beğeni/yorum/paylaşım) için LinkedIn API Partnership gerekmektedir.
Claude analizi ile gönderi önem sıralaması yapılır.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import requests
from loguru import logger

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

try:
    import trafilatura
    _TRAFILATURA_VAR = True
except ImportError:
    _TRAFILATURA_VAR = False

from config.settings import BASE_DIR
from src.ai_client import sorgula

_TAG_AYAR_DOSYASI = BASE_DIR / "config" / "linkedin_tags.json"


def _secili_tagleri_oku() -> list[str]:
    """Kullanıcının UI'dan seçtiği LinkedIn hashtaglerini döndürür."""
    if _TAG_AYAR_DOSYASI.exists():
        try:
            import json as _json
            return _json.loads(_TAG_AYAR_DOSYASI.read_text(encoding="utf-8")).get("secili", [])
        except Exception:
            pass
    return []

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

LINKEDIN_SIRKET_URL = "https://www.linkedin.com/company/ulakhaberlesme"
LINKEDIN_SIRKET_ADI = "Ulak Haberleşme"


# ── Veri modeli ──────────────────────────────────────────────────────────────

@dataclass
class LinkedInGonderi:
    baslik: str                    # Gönderi başlığı / ilk satır
    icerik: str                    # Gönderi metni
    url: str                       # LinkedIn linki
    yazar: str = ""                # Paylaşan kişi / şirket
    tarih: Optional[datetime] = None
    etkilesim_tahmini: int = 0     # Claude tarafından önem skoru (1-10)
    etkilesim_aciklama: str = ""   # Claude gerekçesi
    kaynak: str = "LinkedIn"


@dataclass
class LinkedInRaporu:
    gonderiler: list[LinkedInGonderi] = field(default_factory=list)
    ozet: str = ""
    toplama_tarihi: datetime = field(default_factory=datetime.now)


# ── Veri toplama ─────────────────────────────────────────────────────────────

def _ddg_linkedin_ara(gun: int = 7) -> list[dict]:
    """DuckDuckGo ile son N günde yayınlanmış LinkedIn gönderilerini arar."""
    sonuclar: list[dict] = []
    esik = datetime.now() - timedelta(days=gun)

    # Kullanıcının seçtiği taglerle ek sorgular oluştur
    secili_tagler = _secili_tagleri_oku()
    tag_sorgulari = [
        f'site:linkedin.com/posts {tag}' for tag in secili_tagler[:10]
    ]

    sorgular = [
        f'site:linkedin.com/posts "Ulak Haberleşme"',
        f'site:linkedin.com/posts "Ulak Haberlesme"',
        f'site:linkedin.com/company/ulakhaberlesme',
        *tag_sorgulari,
    ]

    logger.info(f"LinkedIn araması: {len(secili_tagler)} seçili tag ile {len(sorgular)} sorgu yapılacak")

    _ULAK_ANAHTAR = {"ulak haberleşme", "ulak haberlesme", "ulakhaberlesme"}

    def _ilgili_mi(baslik: str, ozet: str, url: str) -> bool:
        birlesik = (baslik + " " + ozet + " " + url).lower()
        return any(k in birlesik for k in _ULAK_ANAHTAR)

    goruldu: set[str] = set()
    try:
        with DDGS() as ddgs:
            for sorgu in sorgular:
                time.sleep(2)
                try:
                    for r in ddgs.text(sorgu, max_results=10, timelimit="w"):
                        url = r.get("href", "") or r.get("url", "")
                        if url in goruldu:
                            continue
                        if "linkedin.com" not in url:
                            continue
                        baslik = r.get("title", "")
                        ozet_m = r.get("body", "") or r.get("snippet", "")
                        if not _ilgili_mi(baslik, ozet_m, url):
                            logger.debug(f"LinkedIn sonucu Ulak Haberleşme ile ilgisiz, atlandı: {url[:60]}")
                            continue
                        goruldu.add(url)
                        sonuclar.append({
                            "baslik": baslik,
                            "ozet":   ozet_m,
                            "url":    url,
                        })
                except Exception as e:
                    logger.debug(f"DDG sorgu hatası ({sorgu[:40]}): {e}")
    except Exception as e:
        logger.error(f"DuckDuckGo bağlantı hatası: {e}")

    logger.info(f"LinkedIn DDG araması: {len(sonuclar)} sonuç bulundu")
    return sonuclar


def _linkedin_sayfa_cek(url: str) -> str:
    """
    Tek bir LinkedIn URL'sinin içeriğini çekmeye çalışır.
    LinkedIn JS render ettiğinden içerik kısmi olabilir.
    """
    if not _TRAFILATURA_VAR:
        return ""
    try:
        time.sleep(1.5)
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            metin = trafilatura.extract(downloaded, include_comments=False,
                                        include_tables=False) or ""
            return metin[:1000]
    except Exception as e:
        logger.debug(f"LinkedIn sayfa çekme hatası ({url[:60]}): {e}")
    return ""


def _sirket_sayfasi_cek() -> list[dict]:
    """
    Ulak Haberleşme'nin resmi LinkedIn sayfasını doğrudan çekmeyi dener.
    JavaScript nedeniyle gönderi listesi gelmeyebilir; meta verileri alınır.
    """
    sonuclar = []
    try:
        resp = requests.get(
            LINKEDIN_SIRKET_URL,
            headers=_HEADERS,
            timeout=15,
            allow_redirects=True,
        )
        if resp.status_code == 200 and "linkedin" in resp.url:
            metin = resp.text

            # Open Graph meta başlıklarından bilgi topla
            og_desc = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', metin)
            og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', metin)

            if og_title or og_desc:
                sonuclar.append({
                    "baslik": og_title.group(1) if og_title else LINKEDIN_SIRKET_ADI,
                    "ozet":   og_desc.group(1) if og_desc else "",
                    "url":    LINKEDIN_SIRKET_URL,
                })
    except Exception as e:
        logger.debug(f"LinkedIn şirket sayfası hatası: {e}")
    return sonuclar


# ── Claude ile analiz ve sıralama ────────────────────────────────────────────

_ANALIZ_PROMPTU = """\
Ulak Haberleşme A.Ş.'nin LinkedIn'den bulunan aşağıdaki {sayi} gönderiyi/içeriği analiz et.

{gonderiler}

Her gönderi için şu JSON yapısını kullan:
{{
  "gonderiler": [
    {{
      "indeks": 0,
      "onem_skoru": 1-10,
      "gerekce": "Neden bu kadar önemli — 1 cümle Türkçe",
      "yazar_tahmini": "Şirket mi, yönetici mi, çalışan mı?",
      "kategori": "duyuru | proje | etkinlik | basın | teknik | insan_kaynakları | genel"
    }}
  ],
  "en_onemli_3": [0, 1, 2],
  "ozet": "LinkedIn varlığının Türkçe 2 cümlelik genel değerlendirmesi"
}}

Önem skoru kriterleri (Ulak Haberleşme kurumsal perspektifi):
9-10: Stratejik duyuru, büyük sözleşme, üst yönetim paylaşımı
7-8: Proje lansmanı, teknik başarı, kurumsal etkinlik
4-6: Rutin içerik, işe alım, motivasyon paylaşımı
1-3: Genel sektör içeriği, alıntı

SADECE JSON döndür."""


def _gonderileri_analiz_et(
        ham_sonuclar: list[dict],
) -> LinkedInRaporu:
    """Claude ile gönderileri analiz eder, önem sırası çıkarır."""
    if not ham_sonuclar:
        return LinkedInRaporu(ozet="LinkedIn'den içerik bulunamadı.")

    # Ham veriyi LinkedInGonderi listesine çevir
    gonderiler: list[LinkedInGonderi] = []
    for r in ham_sonuclar:
        ek_icerik = ""
        if r["url"] and "linkedin.com" in r["url"] and _TRAFILATURA_VAR:
            ek_icerik = _linkedin_sayfa_cek(r["url"])

        icerik = ek_icerik or r.get("ozet", "") or r.get("baslik", "")
        gonderiler.append(LinkedInGonderi(
            baslik=r.get("baslik", "")[:200],
            icerik=icerik[:500],
            url=r.get("url", ""),
        ))

    gonderi_metni = "\n\n".join([
        f"[{i}] Başlık: {g.baslik}\n"
        f"İçerik: {g.icerik[:300]}\n"
        f"URL: {g.url}"
        for i, g in enumerate(gonderiler)
    ])

    prompt = _ANALIZ_PROMPTU.format(
        sayi=len(gonderiler),
        gonderiler=gonderi_metni,
    )

    try:
        yanit = sorgula(prompt)
        if "```" in yanit:
            parcalar = yanit.split("```")
            for p in parcalar:
                p = p.strip()
                if p.startswith("json"):
                    p = p[4:].strip()
                if p.startswith("{"):
                    yanit = p
                    break

        veri = json.loads(yanit)

        # Analiz sonuçlarını gönderilere işle
        for item in veri.get("gonderiler", []):
            idx = item.get("indeks", -1)
            if 0 <= idx < len(gonderiler):
                gonderiler[idx].etkilesim_tahmini = int(item.get("onem_skoru", 5))
                gonderiler[idx].etkilesim_aciklama = item.get("gerekce", "")
                gonderiler[idx].yazar = item.get("yazar_tahmini", "")

        # En önemli 3 gönderiyi seç
        en_onemli_idx = veri.get("en_onemli_3", [])
        if en_onemli_idx:
            secili = [gonderiler[i] for i in en_onemli_idx if i < len(gonderiler)]
        else:
            secili = sorted(gonderiler, key=lambda g: g.etkilesim_tahmini, reverse=True)[:3]

        ozet = veri.get("ozet", "")
        rapor = LinkedInRaporu(gonderiler=secili, ozet=ozet)
        logger.info(
            f"LinkedIn analizi tamamlandı — "
            f"{len(secili)} gönderi seçildi, "
            f"önem skorları: {[g.etkilesim_tahmini for g in secili]}"
        )
        return rapor

    except json.JSONDecodeError as e:
        logger.error(f"LinkedIn analiz JSON hatası: {e}")
    except Exception as e:
        logger.error(f"LinkedIn analiz hatası: {e}")

    # Fallback: en fazla 3 gönderi ham haliyle döndür
    return LinkedInRaporu(
        gonderiler=gonderiler[:3],
        ozet="Analiz tamamlanamadı.",
    )


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

def linkedin_gonderileri_cek(gun: int = 7) -> LinkedInRaporu:
    """
    Ulak Haberleşme resmi LinkedIn sayfasından son {gun} günün gönderilerini toplar,
    Claude ile analiz eder ve en önemli 3 gönderiyi döndürür.
    """
    logger.info("LinkedIn takibi başlıyor...")
    ham: list[dict] = []

    # 1. DuckDuckGo arama
    ham += _ddg_linkedin_ara(gun)

    # 2. Doğrudan sayfa çekimi (kısmi)
    ham += _sirket_sayfasi_cek()

    if not ham:
        logger.warning("LinkedIn'den hiç içerik bulunamadı.")
        return LinkedInRaporu(ozet="Bu hafta LinkedIn'den içerik toplanamadı.")

    # URL bazlı tekilleştir
    goruldu: set[str] = set()
    tekil: list[dict] = []
    for r in ham:
        url = r.get("url", "")
        if url and url not in goruldu:
            goruldu.add(url)
            tekil.append(r)
        elif not url:
            tekil.append(r)

    logger.info(f"LinkedIn toplam tekil içerik: {len(tekil)}")
    return _gonderileri_analiz_et(tekil)
