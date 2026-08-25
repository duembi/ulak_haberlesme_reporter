"""
ULAK Haberleşme resmi web sitesinden Yönetim Kurulu ve Yönetim (Genel Müdür)
sayfalarını çeker. Site Avada/Fusion Builder (WordPress) tabanlı; her kişi
kartı bir `li.post-card` içinde: fotoğraf `img[data-orig-src]`, isim
`p.title-heading-tag`, unvan `h5.fusion-title-heading` (title-heading-tag
sınıfı olmayan) olarak yer alıyor.
"""
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from loguru import logger

_BASE_URL = "https://www.ulakhaberlesme.com.tr"
_KURUL_URL = f"{_BASE_URL}/yonetim-kurulu/"
_YONETIM_URL = f"{_BASE_URL}/yonetim/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


@dataclass
class YonetimKisi:
    ad_soyad: str
    unvan: str
    foto_url: str
    grup: str  # "kurul" | "yonetim"


def _sayfadan_kisileri_cek(url: str, grup: str) -> list[YonetimKisi]:
    kisiler: list[YonetimKisi] = []
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Yönetim sayfası çekilemedi ({url}): {e}")
        return kisiler

    soup = BeautifulSoup(resp.text, "lxml")
    for kart in soup.select("li.post-card"):
        isim_tag = kart.select_one("p.title-heading-tag")
        unvan_tag = kart.select_one("h5.fusion-title-heading")
        img_tag = kart.select_one("img[data-orig-src]")

        ad_soyad = isim_tag.get_text(strip=True) if isim_tag else ""
        unvan = unvan_tag.get_text(strip=True) if unvan_tag else ""
        foto_url = img_tag.get("data-orig-src", "") if img_tag else ""

        if not ad_soyad:
            continue

        kisiler.append(YonetimKisi(ad_soyad=ad_soyad, unvan=unvan, foto_url=foto_url, grup=grup))

    logger.info(f"Yönetim scraper — {grup}: {len(kisiler)} kişi bulundu")
    return kisiler


def yonetim_kisilerini_cek() -> list[YonetimKisi]:
    """Yönetim Kurulu + Yönetim (Genel Müdür) sayfalarındaki tüm kişileri döner."""
    kisiler = _sayfadan_kisileri_cek(_KURUL_URL, "kurul")
    kisiler += _sayfadan_kisileri_cek(_YONETIM_URL, "yonetim")
    return kisiler
