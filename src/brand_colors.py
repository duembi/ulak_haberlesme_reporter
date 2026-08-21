"""
Marka rengi veritabanı ve HSL tabanlı palet üretici.

Veri kaynakları:
  - reimertz/brand-colors (693 marka, ~2093 renk girişi)
  - Elle eklenen Türk şirketleri
  - Brandfetch API (domain bazlı, BRANDFETCH_API_KEY gerektirir)
"""
import colorsys
import json
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Optional

import httpx

_DATA_FILE = Path(__file__).parent / "brand_colors_data.json"


@lru_cache(maxsize=1)
def _veri_yukle() -> dict[str, str]:
    """Brand colors veritabanını yükler (uygulama başlangıcında bir kez)."""
    if not _DATA_FILE.exists():
        return {}
    with open(_DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def _normalize(metin: str) -> str:
    """Firma adını arama için normalize eder."""
    # Unicode dönüşümü (ş→s, ç→c, ğ→g, ü→u, ö→o, ı→i, İ→i)
    nfd = unicodedata.normalize("NFD", metin.lower())
    ascii_str = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Tire, nokta, parantez → boşluk
    ascii_str = re.sub(r"[-_.,()&/\\]", " ", ascii_str)
    return " ".join(ascii_str.split())


def _hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = (int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h, s, l


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    l = max(0.0, min(1.0, l))
    s = max(0.0, min(1.0, s))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


def _shade(h: float, s: float, base_l: float, delta_l: float, sat_mult: float = 1.0) -> str:
    return _hsl_to_hex(h, min(1.0, s * sat_mult), base_l + delta_l)


def palet_uret(hex_primary: str, koyu_sidebar: str = "#0F172A") -> dict:
    """
    Tek bir ana renkten light + dark UI paleti üretir.
    brand_600 = verilen ana renk; diğerleri HSL interpolasyonla türetilir.
    """
    h, s, l = _hex_to_hsl(hex_primary)

    # Light palet
    light = {
        "brand_600": _hsl_to_hex(h, s, l),
        "brand_700": _shade(h, s, l, -0.08),
        "brand_500": _shade(h, s, l, +0.10),
        "brand_50":  _shade(h, s, 0.97, 0, sat_mult=0.25),
        "brand_100": _shade(h, s, 0.93, 0, sat_mult=0.35),
        "brand_200": _shade(h, s, 0.86, 0, sat_mult=0.50),
        "brand_800": _shade(h, s, l, -0.16),
        "sidebar":   koyu_sidebar,
        "bg_base":   "#F1F5F9",
        "bg_card":   "#FFFFFF",
        "bg_input":  "#FFFFFF",
        "bg_hover":  "#F8FAFC",
        "text_main": "#0F172A",
        "text_sub":  "#475569",
        "text_muted": "#94A3B8",
        "border":    "#E2E8F0",
    }

    # Dark palet — brand renklerini biraz açıklaştır
    dark_l = min(l + 0.12, 0.72)  # koyu zeminde görünür olsun
    dark_s = min(s * 1.05, 1.0)
    dark = {
        "brand_600": _hsl_to_hex(h, dark_s, dark_l),
        "brand_700": _shade(h, dark_s, dark_l, -0.08),
        "brand_500": _shade(h, dark_s, dark_l, +0.10),
        "brand_50":  _shade(h, dark_s, 0.06, 0, sat_mult=0.40),
        "brand_100": _shade(h, dark_s, 0.10, 0, sat_mult=0.50),
        "brand_200": _shade(h, dark_s, 0.16, 0, sat_mult=0.60),
        "brand_800": _shade(h, dark_s, dark_l, +0.15),
        "sidebar":   "#020617",
        "bg_base":   "#0F172A",
        "bg_card":   "#1E293B",
        "bg_input":  "#0F172A",
        "bg_hover":  "#1E293B",
        "text_main": "#F8FAFC",
        "text_sub":  "#CBD5E1",
        "text_muted": "#64748B",
        "border":    "#334155",
    }

    return {"light": light, "dark": dark}


def marka_rengi_bul(firma_adi: str) -> str | None:
    """
    Firma adını veritabanında arar, bulursa birincil HEX rengini döndürür.
    Aranan: tam eşleşme → token seti benzerliği → kelime içerme.
    """
    db = _veri_yukle()
    if not db:
        return None

    q = _normalize(firma_adi)
    if not q:
        return None

    # 1. Tam eşleşme
    if q in db:
        return db[q]

    # 2. Parantez içindeki kısımları kaldır (örn. "Garanti BBVA" → "garanti bbva")
    q_tokens = set(q.split())

    # 3. Token seti tam örtüşmesi
    for key, color in db.items():
        if set(key.split()) == q_tokens:
            return color

    # 4. Sorgu kelimeleri db anahtarı içinde geçiyorsa (kısa query, uzun key)
    for key, color in db.items():
        key_tokens = set(key.split())
        if q_tokens and q_tokens.issubset(key_tokens):
            return color

    # 5. db anahtarı sorguda geçiyorsa (kısa key, uzun query)
    for key, color in db.items():
        key_tokens = set(key.split())
        if len(key_tokens) >= 2 and key_tokens.issubset(q_tokens):
            return color

    return None


def marka_paleti_al(firma_adi: str) -> Optional[dict]:
    """
    Firma adından tam UI paleti döndürür (yerel DB).
    Bulunamazsa None.
    """
    hex_primary = marka_rengi_bul(firma_adi)
    if hex_primary is None:
        return None
    return palet_uret(hex_primary)


async def brandfetch_paleti_al(domain: str) -> Optional[dict]:
    """
    Brandfetch API ile domain'den marka rengi çeker ve UI paleti üretir.
    BRANDFETCH_API_KEY env değişkeni yoksa None döner.
    Hata durumunda None döner (sessizce).
    """
    from config.settings import BRANDFETCH_API_KEY
    if not BRANDFETCH_API_KEY or not domain:
        return None

    url = f"https://api.brandfetch.io/v2/brands/{domain}"
    headers = {"Authorization": f"Bearer {BRANDFETCH_API_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return None

        data = resp.json()
        colors = data.get("colors", [])
        if not colors:
            return None

        # Öncelik sırası: type==brand → type==accent → en parlak renk
        def _oncelik(c: dict) -> int:
            return {"brand": 0, "accent": 1, "dark": 2, "light": 3}.get(c.get("type", ""), 4)

        renk = sorted(colors, key=_oncelik)[0]
        hex_primary = renk.get("hex", "")
        if not hex_primary or not hex_primary.startswith("#"):
            return None

        return palet_uret(hex_primary)

    except Exception:
        return None
