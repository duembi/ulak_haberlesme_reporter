"""
Müşteri sesi toplama modülü.
Şikayetvar, Şikayet.com, Ekşi Sözlük, Reddit ve Google Play'den
Ulak Haberleşme hakkında müşteri yorumlarını çeker ve Claude ile analiz eder.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger

try:
    import trafilatura
    _TRAFILATURA_VAR = True
except ImportError:
    _TRAFILATURA_VAR = False

from config.settings import BASE_DIR
from src.ai_client import sorgula

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}


# ── Veri modeli ──────────────────────────────────────────────────────────────

@dataclass
class MusteriYorumu:
    platform: str
    baslik: str
    icerik: str
    tarih: Optional[datetime]
    url: str
    tip: str = ""          # "sikayet" | "tesekkur" | "notr" — Claude doldurur
    tema: str = ""         # Ana konu — Claude doldurur
    onem: int = 5          # 1-10 — Claude doldurur


@dataclass
class MusteriSesiRaporu:
    yorumlar: list[MusteriYorumu] = field(default_factory=list)
    tema_ozeti: str = ""
    en_sik_sikayet: list[str] = field(default_factory=list)
    en_sik_tesekkur: list[str] = field(default_factory=list)


# ── Platform scraperları ─────────────────────────────────────────────────────

def _sikayetvar_cek(gun: int = 7) -> list[MusteriYorumu]:
    """
    Ulak Haberleşme B2B/savunma sanayi tedarikçisi (bireysel tüketiciye değil,
    operatörlere/kamu kurumlarına satış yapıyor); sikayetvar.com'da şirkete ait
    bir profil/şikayet sayfası doğrulanamadı (denenen URL 410 Gone döndü).
    Bu yüzden şimdilik devre dışı — sayfa varlığı doğrulanırsa _SIKAYETVAR_URL
    güncellenip aşağıdaki erken `return []` kaldırılabilir.
    """
    logger.info("Ulak Haberleşme için Şikayetvar sayfası doğrulanamadı, atlanıyor.")
    return []

    yorumlar: list[MusteriYorumu] = []
    url = "https://www.sikayetvar.com/ulak-haberlesme"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        esik = datetime.now() - timedelta(days=gun)

        kartlar = (
            soup.select("div.complaint-item") or
            soup.select("article.complaint") or
            soup.select("div.card-complaint") or
            soup.select("li.complaint-list__item") or
            soup.select("[class*='complaint']")
        )

        for kart in kartlar[:30]:
            baslik_el = kart.select_one("h2, h3, .title, [class*='title']")
            icerik_el = kart.select_one("p, .content, [class*='content'], [class*='text']")
            link_el   = kart.select_one("a[href]")
            tarih_el  = kart.select_one("time, [class*='date'], [class*='time']")

            baslik  = baslik_el.get_text(strip=True) if baslik_el else ""
            icerik  = icerik_el.get_text(strip=True)[:600] if icerik_el else ""
            link    = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://www.sikayetvar.com" + link

            tarih = None
            if tarih_el:
                tarih_str = tarih_el.get("datetime") or tarih_el.get_text(strip=True)
                try:
                    tarih = datetime.fromisoformat(tarih_str[:19])
                except Exception:
                    pass

            if not baslik and not icerik:
                continue

            yorumlar.append(MusteriYorumu(
                platform="Şikayetvar",
                baslik=baslik[:200],
                icerik=icerik,
                tarih=tarih,
                url=link,
            ))

        logger.info(f"Şikayetvar: {len(yorumlar)} yorum çekildi")
    except Exception as e:
        logger.error(f"Şikayetvar hatası: {e}")
    return yorumlar


def _sikayet_com_cek(gun: int = 7) -> list[MusteriYorumu]:
    """
    Şikayet.com JavaScript render ettiğinden DuckDuckGo ile arama yapılır,
    bulunan URL'lerden trafilatura ile içerik çekilir.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    yorumlar: list[MusteriYorumu] = []
    goruldu: set[str] = set()

    sorgular = [
        'site:sikayet.com "ulak haberleşme" OR "ulak haberlesme"',
        'site:sikayet.com ulak haberleşme şikayet',
    ]

    try:
        with DDGS() as ddgs:
            for sorgu in sorgular:
                time.sleep(2)
                try:
                    for r in ddgs.text(sorgu, max_results=15, timelimit="w"):
                        url = r.get("href", "") or r.get("url", "")
                        if not url or "sikayet.com" not in url:
                            continue
                        if url in goruldu:
                            continue
                        goruldu.add(url)

                        baslik = r.get("title", "")
                        icerik = r.get("body", "") or r.get("snippet", "")

                        # Trafilatura ile tam içerik çekmeyi dene
                        if _TRAFILATURA_VAR:
                            try:
                                downloaded = trafilatura.fetch_url(url)
                                if downloaded:
                                    tam = trafilatura.extract(
                                        downloaded,
                                        include_comments=False,
                                        include_tables=False,
                                    )
                                    if tam and len(tam) > len(icerik):
                                        icerik = tam[:600]
                            except Exception:
                                pass

                        if not baslik or len(baslik) < 8:
                            continue

                        yorumlar.append(MusteriYorumu(
                            platform="Şikayet.com",
                            baslik=baslik[:200],
                            icerik=icerik[:600],
                            tarih=None,
                            url=url,
                        ))
                except Exception as e:
                    logger.debug(f"Şikayet.com DDG sorgu hatası: {e}")

    except Exception as e:
        logger.error(f"Şikayet.com DDG hatası: {e}")

    logger.info(f"Şikayet.com: {len(yorumlar)} yorum çekildi")
    return yorumlar


def _eksisozluk_cek(gun: int = 7) -> list[MusteriYorumu]:
    yorumlar: list[MusteriYorumu] = []
    # Doğru başlık slug'ı: "ulak haberleşme aş" (id 6171707) — düz "ulak-haberlesme" 404 veriyordu
    url = "https://eksisozluk.com/ulak-haberlesme-as--6171707"
    try:
        resp = requests.get(url, headers={**_HEADERS, "Accept": "text/html"},
                            timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        esik = datetime.now() - timedelta(days=gun)

        entryler = soup.select("li[data-id]")
        for entry in entryler[:30]:
            icerik_el = entry.select_one("div.content")
            tarih_el  = entry.select_one("a.entry-date")
            link_el   = entry.select_one("a.entry-date")

            icerik = icerik_el.get_text(strip=True)[:600] if icerik_el else ""
            if not icerik:
                continue

            tarih = None
            if tarih_el:
                tarih_str = tarih_el.get_text(strip=True)
                try:
                    tarih = datetime.strptime(tarih_str[:16], "%d.%m.%Y %H:%M")
                except Exception:
                    pass

            if tarih and tarih < esik:
                continue

            link = ""
            if link_el and link_el.get("href"):
                link = "https://eksisozluk.com" + link_el["href"]

            yorumlar.append(MusteriYorumu(
                platform="Ekşi Sözlük",
                baslik="Ulak Haberleşme entry",
                icerik=icerik,
                tarih=tarih,
                url=link,
            ))

        logger.info(f"Ekşi Sözlük: {len(yorumlar)} entry çekildi")
    except Exception as e:
        logger.error(f"Ekşi Sözlük hatası: {e}")
    return yorumlar


def _reddit_cek(gun: int = 7) -> list[MusteriYorumu]:
    """Reddit'ten Ulak Haberleşme gönderilerini DuckDuckGo üzerinden çeker."""
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    yorumlar: list[MusteriYorumu] = []
    goruldu: set[str] = set()

    sorgular = [
        'site:reddit.com "Ulak Haberleşme" OR "Ulak Haberlesme"',
        'site:reddit.com/r/Turkey "Ulak Haberlesme"',
    ]

    try:
        with DDGS() as ddgs:
            for sorgu in sorgular:
                time.sleep(2)
                try:
                    for r in ddgs.text(sorgu, max_results=15, timelimit="w"):
                        url = r.get("href", "") or r.get("url", "")
                        if not url or "reddit.com" not in url:
                            continue
                        if url in goruldu:
                            continue
                        goruldu.add(url)

                        baslik = r.get("title", "")
                        icerik = r.get("body", "") or r.get("snippet", "")
                        if not baslik:
                            continue

                        # Subreddit adını URL'den çıkar
                        subreddit = ""
                        if "/r/" in url:
                            subreddit = "r/" + url.split("/r/")[1].split("/")[0]

                        yorumlar.append(MusteriYorumu(
                            platform=f"Reddit ({subreddit})" if subreddit else "Reddit",
                            baslik=baslik[:200],
                            icerik=icerik[:600],
                            tarih=None,
                            url=url,
                        ))
                except Exception as e:
                    logger.debug(f"Reddit DDG sorgu hatası: {e}")
    except Exception as e:
        logger.error(f"Reddit DDG hatası: {e}")

    logger.info(f"Reddit: {len(yorumlar)} post çekildi")
    return yorumlar


def _google_play_cek() -> list[MusteriYorumu]:
    """Ulak Haberleşme uygulaması Google Play yorumları."""
    yorumlar: list[MusteriYorumu] = []
    # Ulak Haberleşme'nin resmi uygulaması doğrulanmadı — bilinen bir app id yok,
    # şimdilik boş liste; gerçek app id bulununca buraya eklenmeli.
    app_idler: list[str] = []
    for app_id in app_idler:
        url = f"https://play.google.com/store/apps/details?id={app_id}&hl=tr"
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")

            yorumlar_el = soup.select("div[jscontroller] span[jsname]")
            for el in yorumlar_el[:20]:
                metin = el.get_text(strip=True)
                if len(metin) < 20:
                    continue
                yorumlar.append(MusteriYorumu(
                    platform="Google Play",
                    baslik="Uygulama yorumu",
                    icerik=metin[:600],
                    tarih=None,
                    url=url,
                ))
        except Exception as e:
            logger.debug(f"Google Play ({app_id}): {e}")

    logger.info(f"Google Play: {len(yorumlar)} yorum çekildi")
    return yorumlar


# ── Claude ile analiz ────────────────────────────────────────────────────────

_ANALIZ_PROMPTU = """\
Ulak Haberleşme A.Ş. hakkında çeşitli platformlardan toplanmış {sayi} müşteri yorumunu analiz et.

{yorumlar}

Her yorum için şu JSON yapısını döndür:
{{
  "yorumlar": [
    {{
      "indeks": 0,
      "tip": "sikayet | tesekkur | oneri | notr",
      "tema": "internet hızı | fatura | müşteri hizmetleri | teknik destek | kurulum | uygulama | fiyat | kapsama alanı | genel | diğer",
      "onem": 1-10,
      "ozet": "1 cümlelik Türkçe özet"
    }}
  ],
  "en_sik_sikayet_temalar": ["tema1", "tema2", "tema3"],
  "en_sik_tesekkur_temalar": ["tema1", "tema2"],
  "genel_ozet": "Müşteri geri bildirimlerinin Türkçe 2-3 cümlelik genel değerlendirmesi"
}}

SADECE JSON döndür."""


def yorumlari_analiz_et(yorumlar: list[MusteriYorumu]) -> MusteriSesiRaporu:
    """AI ile yorumları toplu analiz eder."""
    if not yorumlar:
        return MusteriSesiRaporu(yorumlar=yorumlar)

    yorum_metni = "\n\n".join([
        f"[{i}] Platform: {y.platform}\n"
        f"Başlık: {y.baslik}\n"
        f"İçerik: {y.icerik[:300]}"
        for i, y in enumerate(yorumlar[:40])
    ])

    prompt = _ANALIZ_PROMPTU.format(
        sayi=min(len(yorumlar), 40),
        yorumlar=yorum_metni,
    )

    try:
        yanit = sorgula(prompt)
        # JSON bloğunu temizle
        if "```" in yanit:
            for parca in yanit.split("```"):
                parca = parca.strip()
                if parca.startswith("json"):
                    parca = parca[4:].strip()
                if parca.startswith("{"):
                    yanit = parca
                    break

        veri = json.loads(yanit)

        # Sonuçları yorumlara işle
        for item in veri.get("yorumlar", []):
            idx = item.get("indeks", -1)
            if 0 <= idx < len(yorumlar):
                yorumlar[idx].tip   = item.get("tip", "notr")
                yorumlar[idx].tema  = item.get("tema", "genel")
                yorumlar[idx].onem  = int(item.get("onem", 5))

        rapor = MusteriSesiRaporu(
            yorumlar=yorumlar,
            tema_ozeti=veri.get("genel_ozet", ""),
            en_sik_sikayet=veri.get("en_sik_sikayet_temalar", []),
            en_sik_tesekkur=veri.get("en_sik_tesekkur_temalar", []),
        )
        logger.info(
            f"Müşteri sesi analizi tamamlandı — "
            f"şikayet temaları: {rapor.en_sik_sikayet[:3]}"
        )
        return rapor

    except Exception as e:
        logger.error(f"Müşteri sesi analiz hatası: {e} — anahtar kelime fallback kullanılıyor")
        # AI başarısız olursa basit anahtar kelime sınıflandırması
        _SIKAYET_KEL = {"şikayet", "sorun", "hata", "çalışmıyor", "kötü", "berbat", "rezil",
                        "mağdur", "hayal kırıklığı", "iletişim yok", "çözüm yok"}
        _TESEKKUR_KEL = {"teşekkür", "memnun", "başarılı", "güzel", "iyi", "harika", "süper",
                         "tavsiye", "hızlı", "çözüldü"}
        for y in yorumlar:
            birlesik = (y.baslik + " " + y.icerik).lower()
            if any(k in birlesik for k in _SIKAYET_KEL):
                y.tip = "sikayet"
            elif any(k in birlesik for k in _TESEKKUR_KEL):
                y.tip = "tesekkur"
            else:
                y.tip = "notr"
        return MusteriSesiRaporu(yorumlar=yorumlar)


# ── Ana fonksiyon ────────────────────────────────────────────────────────────

def musteri_sesi_topla(gun: int = 7) -> MusteriSesiRaporu:
    """Tüm platformlardan yorumları çeker ve analiz eder."""
    tum_yorumlar: list[MusteriYorumu] = []

    tum_yorumlar += _sikayetvar_cek(gun)
    tum_yorumlar += _sikayet_com_cek(gun)
    tum_yorumlar += _eksisozluk_cek(gun)
    tum_yorumlar += _reddit_cek(gun)
    tum_yorumlar += _google_play_cek()

    logger.info(f"Toplam müşteri yorumu: {len(tum_yorumlar)}")

    if not tum_yorumlar:
        return MusteriSesiRaporu()

    return yorumlari_analiz_et(tum_yorumlar)
