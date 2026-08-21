"""
Rakip firma haber ve borsa takip modülü.
Google News RSS ile haber, yfinance ile haftalık hisse verisi çeker.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import math
import feedparser
import yfinance as yf
from loguru import logger

from src.ai_client import sorgula
from src.database import rakip_listesi_al

# ── Rakip firma tanımları ────────────────────────────────────────────────────

@dataclass
class RakipFirma:
    ad: str
    rss_sorgu: str          # Google News RSS arama terimi
    rss_dil: str            # "tr" veya "en"
    ticker: Optional[str]   # Yahoo Finance ticker (yoksa None)
    bolge: str              # Görüntüleme için bölge/ülke
    aciklama: str

@dataclass
class RakipHaber:
    firma_adi: str
    baslik: str
    url: str
    kaynak: str
    tarih: Optional[datetime]
    ozet: str = ""

@dataclass
class HisseSenedi:
    firma_adi: str
    ticker: str
    guncel_fiyat: float
    haftalik_degisim: float        # Yüzde
    aylik_degisim: float           # Yüzde
    para_birimi: str
    piyasa_degeri: Optional[str]   # Milyar/milyon formatında
    haftalik_fiyatlar: list[tuple] = field(default_factory=list)  # (tarih, fiyat)
    hareket_aciklamasi: str = ""   # AI tarafından doldurulur


def _db_satiri_donustur(row: dict) -> RakipFirma:
    return RakipFirma(
        ad=row["ad"],
        rss_sorgu=row["rss_sorgu"],
        rss_dil=row["rss_dil"],
        ticker=row["ticker"],
        bolge=row["bolge"],
        aciklama=row["aciklama"],
    )


def rakipleri_yukle(filtre: list[str] | None = None) -> list[RakipFirma]:
    """Aktif rakipleri DB'den yükler. filtre: ad listesi verilirse sadece onları döner."""
    rows = rakip_listesi_al(sadece_aktif=True)
    firmalar = [_db_satiri_donustur(r) for r in rows]
    if filtre:
        firmalar = [f for f in firmalar if f.ad in filtre]
    return firmalar


# ── Haber çekme ─────────────────────────────────────────────────────────────

def _rss_url(sorgu: str, dil: str = "tr") -> str:
    import urllib.parse
    q = urllib.parse.quote(sorgu)
    if dil == "en":
        return f"https://news.google.com/rss/search?q={q}&hl=en&gl=US&ceid=US:en"
    return f"https://news.google.com/rss/search?q={q}&hl=tr&gl=TR&ceid=TR:tr"


def rakip_haberleri_cek(gun: int = 30, haber_basi: int = 3,
                        filtre: list[str] | None = None) -> dict[str, list[RakipHaber]]:
    """Her rakip için RSS'ten haber çeker. {firma_adi: [RakipHaber]} döner."""
    esik = datetime.now() - timedelta(days=gun)
    sonuc: dict[str, list[RakipHaber]] = {}
    liste = rakipleri_yukle(filtre)

    for firma in liste:
        haberler: list[RakipHaber] = []
        try:
            feed = feedparser.parse(_rss_url(firma.rss_sorgu, firma.rss_dil))
            for entry in feed.entries:
                try:
                    tarih = datetime(*entry.published_parsed[:6])
                except Exception:
                    tarih = None

                if tarih and tarih < esik:
                    continue

                haberler.append(RakipHaber(
                    firma_adi=firma.ad,
                    baslik=entry.get("title", "").strip(),
                    url=entry.get("link", ""),
                    kaynak=entry.get("source", {}).get("title", "Google News") if hasattr(entry, "source") else "Google News",
                    tarih=tarih,
                    ozet=entry.get("summary", "")[:400],
                ))

                if len(haberler) >= haber_basi:
                    break

            logger.info(f"Rakip haber — {firma.ad}: {len(haberler)} haber")
        except Exception as e:
            logger.error(f"Rakip haber hatası ({firma.ad}): {e}")

        sonuc[firma.ad] = haberler

    return sonuc


# ── Dashboard kartları: sabit firma seti için dönem bazlı haber sayıları ────────

# Bu 4 firma Ulak Haberleşme'nin ortakları/paydaşları — dashboard kartlarında
# sabit gösteriliyor (Ayarlar > Rakip Firmalar'daki tenant-özel listeden
# bağımsız). "SSB" tek başına aranırsa yanlış eşleşme riski taşıdığından
# (yaygın bir kısaltma) tam adıyla aranıyor.
DASHBOARD_FIRMALARI = {
    "ASELSAN": "ASELSAN",
    "SSB": "Savunma Sanayii Başkanlığı",
    "SSTEK": "SSTEK",
    "Havelsan": "HAVELSAN",
}

_DASHBOARD_DONEMLER = (1, 7, 30)
_DASHBOARD_CACHE_SN = 600  # 10 dakika — her dashboard yüklemesinde 4 RSS isteği atmamak için
_dashboard_cache: dict = {"zaman": None, "veri": None}


def rakip_kart_sayilari() -> dict[str, dict[int, int]]:
    """Her sabit dashboard firması için {gün: haber_sayısı} döner (1/7/30 gün)."""
    simdi = datetime.now()

    onbellek_zaman = _dashboard_cache["zaman"]
    if onbellek_zaman and (simdi - onbellek_zaman).total_seconds() < _DASHBOARD_CACHE_SN:
        return _dashboard_cache["veri"]

    sonuc: dict[str, dict[int, int]] = {}

    for ad, sorgu in DASHBOARD_FIRMALARI.items():
        tarihler: list[datetime] = []
        try:
            feed = feedparser.parse(_rss_url(sorgu, "tr"))
            for entry in feed.entries:
                try:
                    tarihler.append(datetime(*entry.published_parsed[:6]))
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Dashboard rakip sayı hatası ({ad}): {e}")

        sonuc[ad] = {
            gun: sum(1 for t in tarihler if t >= simdi - timedelta(days=gun))
            for gun in _DASHBOARD_DONEMLER
        }

    _dashboard_cache["zaman"] = simdi
    _dashboard_cache["veri"] = sonuc
    return sonuc


# ── Borsa verisi ─────────────────────────────────────────────────────────────

def _piyasa_degeri_formatla(deger) -> str:
    if deger is None:
        return "—"
    try:
        d = float(deger)
        if d >= 1e9:
            return f"{d/1e9:.1f}B"
        if d >= 1e6:
            return f"{d/1e6:.1f}M"
        return str(int(d))
    except Exception:
        return "—"


def _degisim_hesapla(fiyatlar: list[float], gun: int) -> float:
    if len(fiyatlar) < 2:
        return 0.0
    bitis  = fiyatlar[-1]
    baslangic = fiyatlar[max(0, len(fiyatlar) - gun)]
    if baslangic == 0:
        return 0.0
    return (bitis - baslangic) / baslangic * 100


def hisse_hareket_acikla(hisse_listesi: list[HisseSenedi],
                          rakip_haberler: dict[str, list[RakipHaber]]) -> list[HisseSenedi]:
    """
    Her hisse için haftalık fiyat hareketini ve ilgili haberleri Claude'a
    göndererek Türkçe açıklama üretir.
    """
    for hisse in hisse_listesi:
        if abs(hisse.haftalik_degisim) < 1.0:
            hisse.hareket_aciklamasi = "Bu hafta kayda değer bir fiyat hareketi gözlemlenmedi."
            continue

        haberler = rakip_haberler.get(hisse.firma_adi, [])
        haber_metni = "\n".join(
            f"- {h.baslik} ({h.tarih.strftime('%d.%m.%Y') if h.tarih else ''})"
            for h in haberler
        ) or "Bu hafta kayda değer haber bulunamadı."

        yon = "artış" if hisse.haftalik_degisim > 0 else "düşüş"
        prompt = (
            f"Ulak Haberleşme A.Ş. haftalık medya takip raporunun rakip firmalar bölümü için "
            f"aşağıdaki haber ve borsa verilerini Türkçe, 2-3 cümleyle özetle.\n\n"
            f"Firma: {hisse.firma_adi} ({hisse.ticker})\n"
            f"Haftalık borsa değişimi: %{hisse.haftalik_degisim:+.1f} ({yon})\n\n"
            f"Bu haftaki haberler:\n{haber_metni}\n\n"
            f"Haberleri borsa değişimiyle ilişkilendirerek kısa bir medya özeti yaz. "
            f"Yatırım tavsiyesi verme, yalnızca haber-veri korelasyonunu özetle. "
            f"Sadece özet metnini yaz, başka hiçbir şey ekleme."
        )

        try:
            hisse.hareket_aciklamasi = sorgula(prompt)
        except Exception:
            hisse.hareket_aciklamasi = f"Fiyat hareketi: %{hisse.haftalik_degisim:+.1f}"

        logger.info(f"Hareket açıklandı: {hisse.firma_adi}")

    return hisse_listesi


def hisse_verileri_cek(filtre: list[str] | None = None) -> list[HisseSenedi]:
    """Borsadaki rakiplerin haftalık hisse verilerini çeker."""
    sonuc: list[HisseSenedi] = []
    tum_rakipler = rakipleri_yukle(filtre)
    liste = [r for r in tum_rakipler if r.ticker]

    for firma in liste:
        try:
            hisse = yf.Ticker(firma.ticker)
            # Son 30 günlük günlük veri
            gecmis = hisse.history(period="1mo", interval="1d")

            if gecmis.empty:
                logger.warning(f"Hisse verisi boş: {firma.ticker}")
                continue

            # NaN değerleri filtrele
            ham = list(zip(gecmis.index, gecmis["Close"].tolist()))
            temiz = [(d, f) for d, f in ham if not math.isnan(f)]

            if not temiz:
                logger.warning(f"Hisse verisi boş (NaN): {firma.ticker}")
                continue

            tarihler  = [d.strftime("%d.%m") for d, _ in temiz]
            fiyatlar  = [f for _, f in temiz]
            bilgi = hisse.info
            para_birimi  = bilgi.get("currency", "—")
            guncel_fiyat = fiyatlar[-1]

            sonuc.append(HisseSenedi(
                firma_adi=firma.ad,
                ticker=firma.ticker,
                guncel_fiyat=round(guncel_fiyat, 2),
                haftalik_degisim=round(_degisim_hesapla(fiyatlar, 5), 2),
                aylik_degisim=round(_degisim_hesapla(fiyatlar, 30), 2),
                para_birimi=para_birimi,
                piyasa_degeri=_piyasa_degeri_formatla(bilgi.get("marketCap")),
                haftalik_fiyatlar=list(zip(tarihler[-10:], [round(f, 2) for f in fiyatlar[-10:]])),
            ))
            logger.info(f"Hisse verisi — {firma.ticker}: {guncel_fiyat:.2f} {para_birimi}")

        except Exception as e:
            logger.error(f"Hisse verisi hatası ({firma.ticker}): {e}")

    return sonuc
