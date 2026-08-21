from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
import feedparser
import requests
from loguru import logger

from src.retry import retry
from config.settings import (
    NEWS_API_KEY,
    GOOGLE_NEWS_RSS_TR,
    GOOGLE_NEWS_RSS_EN,
    AA_RSS_TR,
    AA_RSS_EN,
    SEARCH_KEYWORDS_TR,
    SEARCH_KEYWORDS_EN,
    NEWS_API_LOOKBACK_DAYS,
    ARAMA_KATEGORILERI,
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


@retry(max_deneme=3, bekleme=3.0, istisnalar=(Exception,))
def _newsapi_cek(kelimeler: list[str], dil: str) -> list[Haber]:
    if not NEWS_API_KEY:
        logger.warning("NEWS_API_KEY tanımlı değil, NewsAPI atlanıyor")
        return []

    haberler = []
    baslangic = (datetime.now() - timedelta(days=NEWS_API_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    sorgu = " OR ".join(kelimeler)

    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": sorgu,
                "from": baslangic,
                "language": dil,
                "sortBy": "publishedAt",
                "pageSize": 50,
            },
            headers={"X-Api-Key": NEWS_API_KEY},
            timeout=15,
        )
        resp.raise_for_status()
        veri = resp.json()

        for makale in veri.get("articles", []):
            tarih = None
            if makale.get("publishedAt"):
                try:
                    tarih = datetime.fromisoformat(makale["publishedAt"].replace("Z", "+00:00"))
                except Exception:
                    pass

            haberler.append(Haber(
                baslik=makale.get("title") or "",
                ozet=makale.get("description") or "",
                url=makale.get("url") or "",
                kaynak=makale.get("source", {}).get("name") or "NewsAPI",
                tarih=tarih.replace(tzinfo=None) if tarih else None,
                dil=dil,
            ))

        logger.info(f"NewsAPI ({dil}): {len(haberler)} haber alındı")
    except Exception as e:
        logger.error(f"NewsAPI ({dil}) hatası: {e}")

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


def _newsapi_kategori_cek() -> list[Haber]:
    """Her kategori için ayrı NewsAPI sorgusu çalıştırır."""
    haberler: list[Haber] = []
    for kategori, diller in ARAMA_KATEGORILERI.items():
        for dil, kelimeler in diller.items():
            yeni = _newsapi_cek(kelimeler, dil)
            for h in yeni:
                h.kategori = kategori  # ön etiket — analyzer üzerine yazar
            haberler += yeni
    return haberler


_ALAKA_KELIMELER = {
    "ulak haberleşme", "ulak haberlesme", "ulak 5g", "ulak mobil haberleşme",
    "ulak yazılım tabanlı telsiz", "ulak çekirdek şebeke", "ulak baz istasyonu",
}


def _ulak_alakali_mi(haber: Haber) -> bool:
    """Başlık veya özette Ulak Haberleşme ile ilgili kelime geçiyor mu?"""
    metin = (haber.baslik + " " + haber.ozet).lower()
    return any(k in metin for k in _ALAKA_KELIMELER)


def haberleri_cek() -> list[Haber]:
    """Tüm kaynaklardan haberleri toplar, tekilleştirir ve döner."""
    tum_haberler: list[Haber] = []

    tum_haberler += _google_news_rss_cek(GOOGLE_NEWS_RSS_TR, "tr")
    tum_haberler += _google_news_rss_cek(GOOGLE_NEWS_RSS_EN, "en")
    tum_haberler += _aa_rss_cek()
    tum_haberler += _newsapi_cek(SEARCH_KEYWORDS_TR, "tr")
    tum_haberler += _newsapi_cek(SEARCH_KEYWORDS_EN, "en")
    tum_haberler += _newsapi_kategori_cek()

    tum_haberler = _tekilestir(tum_haberler)

    # Boş başlıkları at
    tum_haberler = [h for h in tum_haberler if h.baslik.strip()]

    # Ulak Haberleşme ile alakasız haberleri filtrele
    onceki = len(tum_haberler)
    tum_haberler = [h for h in tum_haberler if _ulak_alakali_mi(h)]
    logger.info(f"{onceki - len(tum_haberler)} alakasız haber filtrelendi")

    # Sadece son 7 günün haberlerini al; tarihi bilinmeyenleri at
    esik = datetime.now() - timedelta(days=NEWS_API_LOOKBACK_DAYS)
    onceki = len(tum_haberler)
    tum_haberler = [h for h in tum_haberler if h.tarih and h.tarih >= esik]
    logger.info(f"{onceki - len(tum_haberler)} eski haber filtrelendi (>{NEWS_API_LOOKBACK_DAYS} gün)")

    # Tarihe göre yeniden eskiye sırala
    tum_haberler.sort(key=lambda h: h.tarih, reverse=True)

    logger.info(f"Toplam tekil haber (son {NEWS_API_LOOKBACK_DAYS} gün): {len(tum_haberler)}")
    return tum_haberler
