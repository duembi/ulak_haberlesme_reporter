from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
import feedparser
from loguru import logger

from config.settings import (
    GOOGLE_NEWS_RSS_TR,
    GOOGLE_NEWS_RSS_EN,
    AA_RSS_TR,
    AA_RSS_EN,
    NEWS_API_LOOKBACK_DAYS,
)


@dataclass
class Haber:
    baslik: str
    ozet: str
    url: str
    kaynak: str
    tarih: Optional[datetime]
    dil: str  # "tr" veya "en"
    # Analyzer tarafından doldurulur
    ai_ozet: str = ""
    sentiment: str = ""  # olumlu / olumsuz / nötr
    kategori: str = ""
    triples: list = field(default_factory=list)  # [["Kaynak", "ilişki", "Hedef"], ...]


def _parse_tarih(entry) -> Optional[datetime]:
    try:
        return datetime(*entry.published_parsed[:6])
    except Exception:
        return None


def _google_news_rss_cek(url: str, dil: str) -> list[Haber]:
    haberler = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            haberler.append(Haber(
                baslik=entry.get("title", ""),
                ozet=entry.get("summary", ""),
                url=entry.get("link", ""),
                kaynak="Google News RSS",
                tarih=_parse_tarih(entry),
                dil=dil,
            ))
        logger.info(f"Google News RSS ({dil}): {len(haberler)} haber alındı")
    except Exception as e:
        logger.error(f"Google News RSS ({dil}) hatası: {e}")
    return haberler


def _tekilestir(haberler: list[Haber]) -> list[Haber]:
    """URL'ye göre tekrar eden haberleri kaldırır."""
    goruldu = set()
    sonuc = []
    for h in haberler:
        if h.url and h.url not in goruldu:
            goruldu.add(h.url)
            sonuc.append(h)
    return sonuc


def _aa_rss_cek() -> list[Haber]:
    """Anadolu Ajansı haberlerini Google News üzerinden çeker."""
    haberler = []
    haberler += _google_news_rss_cek(AA_RSS_TR, "tr")
    haberler += _google_news_rss_cek(AA_RSS_EN, "en")
    # Kaynak adını AA olarak işaretle
    for h in haberler:
        h.kaynak = "Anadolu Ajansı"
    logger.info(f"Anadolu Ajansı: {len(haberler)} haber alındı")
    return haberler


_ALAKA_KELIMELER = {
    "ulak haberleşme", "ulak haberlesme", "ulak 5g", "ulak mobil haberleşme",
    "ulak yazılım tabanlı telsiz", "ulak çekirdek şebeke", "ulak baz istasyonu",
}


def _ulak_alakali_mi(haber: Haber) -> bool:
    """Başlık veya özette Ulak Haberleşme ile ilgili kelime geçiyor mu?"""
    metin = (haber.baslik + " " + haber.ozet).lower()
    return any(k in metin for k in _ALAKA_KELIMELER)


def haberleri_cek(gun: int = NEWS_API_LOOKBACK_DAYS) -> list[Haber]:
    """Tüm kaynaklardan haberleri toplar, tekilleştirir ve döner."""
    tum_haberler: list[Haber] = []

    tum_haberler += _google_news_rss_cek(GOOGLE_NEWS_RSS_TR, "tr")
    tum_haberler += _google_news_rss_cek(GOOGLE_NEWS_RSS_EN, "en")
    tum_haberler += _aa_rss_cek()

    tum_haberler = _tekilestir(tum_haberler)

    # Boş başlıkları at
    tum_haberler = [h for h in tum_haberler if h.baslik.strip()]

    # Ulak Haberleşme ile alakasız haberleri filtrele
    onceki = len(tum_haberler)
    tum_haberler = [h for h in tum_haberler if _ulak_alakali_mi(h)]
    logger.info(f"{onceki - len(tum_haberler)} alakasız haber filtrelendi")

    # Sadece seçilen dönemin haberlerini al; tarihi bilinmeyenleri at
    esik = datetime.now() - timedelta(days=gun)
    onceki = len(tum_haberler)
    tum_haberler = [h for h in tum_haberler if h.tarih and h.tarih >= esik]
    logger.info(f"{onceki - len(tum_haberler)} eski haber filtrelendi (>{gun} gün)")

    # Tarihe göre yeniden eskiye sırala
    tum_haberler.sort(key=lambda h: h.tarih, reverse=True)

    logger.info(f"Toplam tekil haber (son {gun} gün): {len(tum_haberler)}")
    return tum_haberler
