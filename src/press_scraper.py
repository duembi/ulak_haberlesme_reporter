"""
Resmi basın bülteni scraper.
ulakhaberlesme.com.tr/category/haberler/ sayfasından haber listesini çeker;
her makale sayfasından tarih bilgisini doğrular. Site WordPress tabanlı;
makale linkleri kök dizinde tek segmentli slug olarak yayınlanıyor
(ör. /ulak-haberlesme-asde-gorev-degisimi/), "haberler/" alt yolunda değil.
"""
import re
import time
from datetime import datetime, timedelta
from loguru import logger
import requests
from bs4 import BeautifulSoup

from src.news_fetcher import Haber

_BASE_URL     = "https://www.ulakhaberlesme.com.tr"
_HABERLER_URL = f"{_BASE_URL}/category/haberler/"
# Kök dizindeki statik sayfalar — haber makalesi değil, listeleme sırasında atlanır
_STATIK_YOLLAR = {
    "category", "tag", "page", "author", "wp-content", "wp-json", "feed",
    "en", "iletisim", "hakkimizda", "cozumlerimiz", "projeler", "kariyer",
    "kalite-yonetimi", "kvkk", "gizlilik-politikasi",
}
_HEADERS      = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

_AYLAR = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
    # İngilizce kısaltmalar (bazı sayfalar)
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# "15 Nisan 2026", "5 Mayıs, 2026" (virgüllü) veya "15.04.2026" veya "2026-04-15"
_RE_TURKCE    = re.compile(r"\b(\d{1,2})\s+([A-Za-zÇçĞğİıÖöŞşÜü]+),?\s+(\d{4})\b")
_RE_NOKTA     = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
_RE_ISO       = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def _tarih_parse_metin(metin: str) -> datetime | None:
    """Türkçe/ISO/nokta formatlı tarih metininden datetime üretir."""
    # ISO: 2026-04-15
    m = _RE_ISO.search(metin)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # Nokta: 15.04.2026
    m = _RE_NOKTA.search(metin)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass

    # Türkçe: 15 Nisan 2026
    m = _RE_TURKCE.search(metin)
    if m:
        ay = _AYLAR.get(m.group(2).lower())
        if ay:
            try:
                return datetime(int(m.group(3)), ay, int(m.group(1)))
            except ValueError:
                pass

    return None


def _makale_tarihi_cek(url: str) -> datetime | None:
    """
    Makale sayfasından tarih çeker:
    1. <meta property="article:published_time"> / og:updated_time
    2. <time datetime="...">
    3. Sayfadaki görünür tarih metinleri
    """
    try:
        time.sleep(0.5)
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")

        # 1. Meta etiketleri
        for prop in ("article:published_time", "og:article:published_time",
                     "datePublished", "pubdate", "date", "DC.date"):
            tag = soup.find("meta", {"property": prop}) or soup.find("meta", {"name": prop})
            if tag and tag.get("content"):
                t = _tarih_parse_metin(tag["content"])
                if t:
                    return t

        # 2. <time> etiketi
        time_tag = soup.find("time")
        if time_tag:
            dt_str = time_tag.get("datetime", "") or time_tag.get_text(strip=True)
            t = _tarih_parse_metin(dt_str)
            if t:
                return t

        # 3. JSON-LD yapısal veri
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                import json
                veri = json.loads(script.string or "")
                for alan in ("datePublished", "dateModified", "dateCreated"):
                    if alan in veri:
                        t = _tarih_parse_metin(str(veri[alan]))
                        if t:
                            return t
            except Exception:
                pass

        # 4. Sayfa metninde tarih arayışı — yaygın CSS sınıflarına bak
        for secici in (
            "[class*='date']", "[class*='tarih']", "[class*='time']",
            "[class*='publish']", "[class*='yayın']", "span.date", "p.date",
        ):
            el = soup.select_one(secici)
            if el:
                t = _tarih_parse_metin(el.get_text(strip=True))
                if t:
                    return t

        # 5. Tüm sayfa metninde tarih ara (son çare)
        sayfa_metni = soup.get_text(" ")
        t = _tarih_parse_metin(sayfa_metni)
        if t:
            return t

    except Exception as e:
        logger.debug(f"Makale tarihi çekilemedi ({url[:60]}): {e}")

    return None


def _haber_linki_mi(href: str) -> bool:
    """Kök dizinde tek segmentli slug ise (ör. /örnek-baslik/) True döner;
    /category/, /tag/, /en/ gibi statik/gezinme yollarını eler."""
    yol = href
    if yol.startswith(_BASE_URL):
        yol = yol[len(_BASE_URL):]
    if not yol.startswith("/"):
        return False
    segmentler = [s for s in yol.split("/") if s]
    if len(segmentler) != 1:
        return False
    return segmentler[0] not in _STATIK_YOLLAR


def press_haberleri_cek(gun: int = 7, max_haber: int = 30) -> list[Haber]:
    """
    Resmi haberler sayfasından (ulakhaberlesme.com.tr/category/haberler/)
    son {gun} günün bültenlerini çeker.

    Site Avada/Fusion Builder (WordPress) tabanlı; her haber kartı bir
    `div.fusion-column-wrapper` içinde: tarih `div.fusion-title-heading`,
    başlık `h5.fusion-title-heading`, bağlantı `a.fusion-button` olarak
    yer alıyor. Tarih zaten listeleme sayfasında olduğundan makale başına
    ayrı istek atılmıyor (daha hızlı, siteye daha az yük).
    """
    esik = datetime.now() - timedelta(days=gun)
    haberler: list[Haber] = []
    goruldu_href: set[str] = set()

    try:
        resp = requests.get(_HABERLER_URL, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Ulak Haberleşme haber sayfası çekilemedi: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    for kart in soup.select("div.fusion-column-wrapper"):
        baslik_el = kart.select_one("h5.fusion-title-heading")
        tarih_el  = kart.select_one("div.fusion-title-heading")
        link_el   = kart.select_one("a.fusion-button[href]")
        if not (baslik_el and link_el):
            continue

        href = link_el["href"]
        if href in goruldu_href:
            continue
        goruldu_href.add(href)

        if not _haber_linki_mi(href):
            continue

        baslik = baslik_el.get_text(strip=True)
        if len(baslik) < 10:
            continue

        tarih = _tarih_parse_metin(tarih_el.get_text(strip=True)) if tarih_el else None
        if tarih is None:
            # Listeleme sayfasında tarih yoksa makale sayfasından dene
            tarih = _makale_tarihi_cek(href)
        if tarih is None:
            logger.debug(f"Tarih bulunamadı, atlandı: {baslik[:60]}")
            continue

        if tarih < esik:
            logger.debug(f"Eski haber ({tarih.date()}), atlandı: {baslik[:60]}")
            continue

        haberler.append(Haber(
            baslik=baslik[:500],
            ozet="",
            url=href,
            kaynak="Ulak Haberleşme Resmi",
            tarih=tarih,
            dil="tr",
        ))

        if len(haberler) >= max_haber:
            break

    logger.info(f"Ulak Haberleşme resmi site: {len(haberler)} güncel haber (son {gun} gün)")
    return haberler
