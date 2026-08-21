"""
Kriz algılama modülü.
Haberleri kritik kelimeler ve sentiment oranı açısından tarar.
Kriz tespit edilirse log'a uyarı yazar ve alerts/ klasörüne dosya bırakır.
"""
from collections import Counter
from datetime import datetime
from enum import Enum
from pathlib import Path

from loguru import logger

from config.settings import BASE_DIR
from src.news_fetcher import Haber

ALERTS_DIR = BASE_DIR / "alerts"
ALERTS_DIR.mkdir(exist_ok=True)

# Kriz seviyesi eşikleri
DIKKAT_OLUMSUZ_ORAN  = 0.40   # %40 ve üzeri olumsuz → DİKKAT
KRIZ_OLUMSUZ_ORAN    = 0.60   # %60 ve üzeri olumsuz → KRİZ
KRIZ_MINIMUM_HABER   = 3      # En az bu kadar haber varsa oran hesapla

# Ulak Haberleşme bağlamı anahtar kelimeleri — haberde bunlardan biri varsa şirketle ilgili sayılır
ULAK_BAGLAM = [
    "ulak haberleşme", "ulak haberlesme", "ulak a.ş", "ulak haberleşme a.ş",
    "ulak 5g", "ulak mobil haberleşme",
]

# Kritik kelimeler — Ulak Haberleşme bağlamı aranmaksızın her haberde tetikler
# (teknik/operasyonel krizler: veri ihlali, sistem çöküşü vb.)
KRITIK_KELIMELER_GENEL = [
    "davası açıldı", "dava açıldı", "mahkemeye verildi",
    "soruşturma başlatıldı", "soruşturma açıldı",
    "para cezası", "cezai işlem",
    "personel ihracı", "ihraç edildi",
    "güvenlik ihlali", "veri ihlali",
    "haciz", "iflas",
    "faaliyetleri durduruldu", "kapatıldı",
    "manipülasyon",
    "fraud", "corruption", "bribery",
    "sanctions", "yaptırım uygulandı",
    "data breach", "security breach",
    "penalty imposed", "fine imposed",
    "lawsuit filed", "indicted",
]

# Bağlam gerektiren kelimeler — yalnızca Ulak Haberleşme adı da geçiyorsa tetikler
# (genel suç/tutuklama haberleri false positive üretmesin)
KRITIK_KELIMELER_BAGLAM = [
    "gözaltına alındı", "tutuklandı",
    "skandal", "yolsuzluk", "rüşvet",
    "zimmet", "ihaleye fesat",
]


class KrizSeviyesi(Enum):
    NORMAL = "normal"
    DIKKAT = "dikkat"
    KRIZ   = "kriz"


def _ulak_baglami_var_mi(metin: str) -> bool:
    """Haberin metninde Ulak Haberleşme'ye atıf var mı?"""
    return any(b in metin for b in ULAK_BAGLAM)


def _kritik_kelime_tara(haberler: list[Haber]) -> list[tuple[str, str]]:
    """
    Kritik kelime içeren (haber başlığı, kelime) çiftlerini döner.
    Bağlam gerektiren kelimeler yalnızca Ulak Haberleşme adı da geçiyorsa sayılır.
    """
    bulunanlar = []
    for h in haberler:
        metin = (h.baslik + " " + h.ai_ozet).lower()

        # Genel kritik kelimeler — bağlam şartı yok
        for kelime in KRITIK_KELIMELER_GENEL:
            if kelime in metin:
                bulunanlar.append((h.baslik[:80], kelime))
                break
        else:
            # Bağlam gerektiren kelimeler — Ulak Haberleşme adı da geçmeli
            if _ulak_baglami_var_mi(metin):
                for kelime in KRITIK_KELIMELER_BAGLAM:
                    if kelime in metin:
                        bulunanlar.append((h.baslik[:80], f"{kelime} [Ulak Haberleşme bağlamı]"))
                        break

    return bulunanlar


def kriz_tespit_et(haberler: list[Haber]) -> tuple[KrizSeviyesi, str]:
    """
    Haberleri analiz eder, kriz seviyesi ve gerekçe döner.
    Returns: (KrizSeviyesi, açıklama metni)
    """
    if not haberler:
        return KrizSeviyesi.NORMAL, "Haber bulunamadı."

    sayim  = Counter(h.sentiment for h in haberler)
    toplam = len(haberler)
    olumsuz_oran = sayim.get("olumsuz", 0) / toplam if toplam else 0

    kritik_haberler = _kritik_kelime_tara(haberler)

    # Kriz seviyesi belirleme
    if kritik_haberler:
        seviye = KrizSeviyesi.KRIZ
        aciklama = (
            f"KRİTİK KELİME TESPİT EDİLDİ — {len(kritik_haberler)} haber.\n"
            + "\n".join(f"  • [{k}] {b}" for b, k in kritik_haberler[:5])
        )
    elif toplam >= KRIZ_MINIMUM_HABER and olumsuz_oran >= KRIZ_OLUMSUZ_ORAN:
        seviye = KrizSeviyesi.KRIZ
        aciklama = (
            f"YÜKSEK OLUMSUZ ORAN — %{olumsuz_oran*100:.0f} olumsuz "
            f"({sayim.get('olumsuz',0)}/{toplam} haber)"
        )
    elif toplam >= KRIZ_MINIMUM_HABER and olumsuz_oran >= DIKKAT_OLUMSUZ_ORAN:
        seviye = KrizSeviyesi.DIKKAT
        aciklama = (
            f"Olumsuz haber oranı yüksek — %{olumsuz_oran*100:.0f} "
            f"({sayim.get('olumsuz',0)}/{toplam} haber)"
        )
    else:
        seviye = KrizSeviyesi.NORMAL
        aciklama = (
            f"Normal — %{olumsuz_oran*100:.0f} olumsuz, "
            f"kritik kelime yok."
        )

    return seviye, aciklama


def kriz_degerlendir(haberler: list[Haber]) -> KrizSeviyesi:
    """
    Kriz tespiti yapar, loglar ve gerekirse alerts/ klasörüne dosya bırakır.
    Ana pipeline'dan çağrılır.
    """
    seviye, aciklama = kriz_tespit_et(haberler)
    simdi = datetime.now()

    if seviye == KrizSeviyesi.KRIZ:
        logger.error(f"🚨 KRİZ UYARISI: {aciklama}")
        _alert_dosyasi_yaz(seviye, aciklama, haberler, simdi)

    elif seviye == KrizSeviyesi.DIKKAT:
        logger.warning(f"⚠️  DİKKAT: {aciklama}")
        _alert_dosyasi_yaz(seviye, aciklama, haberler, simdi)

    else:
        logger.info(f"✅ Kriz yok. {aciklama}")

    return seviye


def _alert_dosyasi_yaz(seviye: KrizSeviyesi, aciklama: str,
                        haberler: list[Haber], simdi: datetime):
    """alerts/ klasörüne tarihli uyarı dosyası yazar."""
    dosya_adi = f"ALERT_{seviye.value.upper()}_{simdi.strftime('%Y%m%d_%H%M%S')}.txt"
    yol = ALERTS_DIR / dosya_adi

    olumsuz = [h for h in haberler if h.sentiment == "olumsuz"]
    satirlar = [
        f"ULAK HABERLEŞME MEDYA KRİZ UYARISI",
        f"Seviye : {seviye.value.upper()}",
        f"Tarih  : {simdi.strftime('%d.%m.%Y %H:%M')}",
        f"",
        f"GEREKÇE:",
        aciklama,
        f"",
        f"OLUMSUZ HABERLER ({len(olumsuz)} adet):",
    ]
    for h in olumsuz[:10]:
        tarih = h.tarih.strftime("%d.%m.%Y") if h.tarih else "?"
        satirlar.append(f"  [{tarih}] {h.baslik}")
        if h.ai_ozet:
            satirlar.append(f"           {h.ai_ozet[:150]}")

    yol.write_text("\n".join(satirlar), encoding="utf-8")
    logger.info(f"Alert dosyası oluşturuldu: {yol}")
