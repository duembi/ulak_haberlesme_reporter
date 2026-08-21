"""
Web crawling agent — DuckDuckGo + trafilatura ile Ulak Haberleşme haberi arar.
"""
import time
from datetime import datetime
from loguru import logger

from src.news_fetcher import Haber, _ALAKA_KELIMELER

try:
    from ddgs import DDGS
    _DDGS_OK = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        _DDGS_OK = True
    except ImportError:
        _DDGS_OK = False
        logger.warning("ddgs kurulu değil; 'pip install ddgs'")

try:
    import trafilatura
    _TRAFILATURA_OK = True
except ImportError:
    _TRAFILATURA_OK = False
    logger.warning("trafilatura kurulu değil; 'pip install trafilatura'")

_ARAMA_SORGULARI = [
    ("Ulak Haberleşme", "tr"),
    ("Ulak Haberleşme A.Ş. haber", "tr"),
    ("Ulak Haberlesme news", "en"),
    ("Ulak Haberlesme Turkey telecom", "en"),
    # Kategori bazlı ek sorgular — her kategoriden en spesifik terim seçildi
    ("ULAK 5G baz istasyonu", "tr"),
    ("ULAK yazılım tabanlı telsiz", "tr"),
    ("Ulak Mobil Haberleşme Sistemi", "tr"),
    ("Ulak Haberleşme ASELSAN HAVELSAN", "tr"),
    ("Ulak Haberleşme arıza gecikme", "tr"),
    ("ULAK 5G base station Turkey", "en"),
    ("Ulak Haberlesme delay disruption", "en"),
]

# news_fetcher.py ile aynı, elle seçilmiş çok-kelimeli alaka listesi kullanılır
# (ÖNEMLİ: burada kelimelerin "ilk kelimesini" alıp otomatik set üretmeye ASLA
# dönme — "ulak" tek başına Türkçe'de sıradan bir kelime/isim, bu yüzden alakasız
# haberleri (ör. "ulak sistemi" geçen bambaşka bir olay) yanlışlıkla içeri alır.
# Bkz. gerçek olay: Ulak Haberleşme ile hiç ilgisi olmayan bir suç örgütü haberi
# sırf "ulak sistemi" ifadesi geçtiği için rapora girmişti.)


def sayfa_metni_cek(url: str) -> str:
    """trafilatura ile makale ana metnini çeker."""
    if not _TRAFILATURA_OK:
        return ""
    try:
        indirilen = trafilatura.fetch_url(url)
        if indirilen:
            metin = trafilatura.extract(indirilen, include_comments=False, include_tables=False)
            return metin or ""
    except Exception as e:
        logger.debug(f"Sayfa çekme hatası ({url[:60]}): {e}")
    return ""


def _gun_timelimit(gun: int) -> str:
    """Gün sayısını DDG'nin kabul ettiği timelimit formatına çevirir."""
    if gun <= 1:
        return "d"
    if gun <= 7:
        return "w"
    if gun <= 30:
        return "m"
    return "y"


def ddg_ara(sorgu: str, gun: int = 7) -> list[dict]:
    """DuckDuckGo News araması yapar."""
    if not _DDGS_OK:
        return []
    timelimit = _gun_timelimit(gun)
    try:
        with DDGS() as ddgs:
            sonuclar = list(ddgs.news(sorgu, max_results=15, timelimit=timelimit))
        return sonuclar
    except Exception as e:
        logger.warning(f"DDG news hatası ('{sorgu[:40]}'): {e} — text aramasına geçiliyor")
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(sorgu, max_results=10, timelimit=timelimit))
        except Exception as e2:
            logger.error(f"DDG arama hatası ('{sorgu[:40]}'): {e2}")
            return []


def _alakali_mi(baslik: str, icerik: str) -> bool:
    """Haber gerçekten Ulak Haberleşme ile ilgili mi?"""
    birlesik = (baslik + " " + icerik[:500]).lower()
    return any(k in birlesik for k in _ALAKA_KELIMELER)


def web_haberleri_cek(gun: int = 7) -> list[Haber]:
    """
    DuckDuckGo'da Ulak Haberleşme sorgularını çalıştırır, sayfa metinlerini çeker,
    alaka filtresinden geçirir ve Haber listesi döner.
    """
    if not _DDGS_OK:
        logger.warning("duckduckgo-search yüklü değil, web crawl atlanıyor")
        return []

    goruldu: set[str] = set()
    haberler: list[Haber] = []

    for i, (sorgu, dil) in enumerate(_ARAMA_SORGULARI):
        if i > 0:
            time.sleep(3)  # DDG rate limit'i aşmamak için
        logger.info(f"Web arama: '{sorgu}'")
        sonuclar = ddg_ara(sorgu, gun)

        for s in sonuclar:
            url = s.get("url", "").strip()
            if not url or url in goruldu:
                continue
            goruldu.add(url)

            baslik = s.get("title", "").strip()
            icerik = sayfa_metni_cek(url)

            if not _alakali_mi(baslik, icerik):
                logger.debug(f"Alaka yok, atlandı: {baslik[:60]}")
                continue

            tarih: datetime | None = None
            if s.get("date"):
                try:
                    tarih = datetime.fromisoformat(s["date"])
                    if tarih.tzinfo:
                        tarih = tarih.replace(tzinfo=None)
                except Exception:
                    pass

            haberler.append(Haber(
                baslik=baslik[:500],
                ozet=(icerik[:1500] if icerik else s.get("body", "")[:500]),
                url=url,
                kaynak=s.get("source", "Web"),
                tarih=tarih,
                dil=dil,
            ))

    logger.info(f"Web crawl tamamlandı: {len(haberler)} Ulak Haberleşme haberi bulundu")
    return haberler
