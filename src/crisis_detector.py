"""
Kriz algılama modülü.
Haberleri kritik kelimeler açısından tarar.
Kriz tespit edilirse log'a uyarı yazar ve alerts/ klasörüne dosya bırakır.
"""
from datetime import datetime
from enum import Enum
from pathlib import Path

from loguru import logger

from config.settings import BASE_DIR
from src.news_fetcher import Haber

ALERTS_DIR = BASE_DIR / "alerts"
ALERTS_DIR.mkdir(exist_ok=True)

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

    kritik_haberler = _kritik_kelime_tara(haberler)

    if kritik_haberler:
        seviye = KrizSeviyesi.KRIZ
        aciklama = (
            f"KRİTİK KELİME TESPİT EDİLDİ — {len(kritik_haberler)} haber.\n"
            + "\n".join(f"  • [{k}] {b}" for b, k in kritik_haberler[:5])
        )
    else:
        seviye = KrizSeviyesi.NORMAL
        aciklama = "Normal — kritik kelime yok."

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
    else:
        logger.info(f"✅ Kriz yok. {aciklama}")

    return seviye


def _alert_dosyasi_yaz(seviye: KrizSeviyesi, aciklama: str,
                        haberler: list[Haber], simdi: datetime):
    """alerts/ klasörüne tarihli uyarı dosyası yazar."""
    dosya_adi = f"ALERT_{seviye.value.upper()}_{simdi.strftime('%Y%m%d_%H%M%S')}.txt"
    yol = ALERTS_DIR / dosya_adi

    kritik_baslikliler = {b for b, _ in _kritik_kelime_tara(haberler)}
    kritik_haberler = [h for h in haberler if h.baslik[:80] in kritik_baslikliler]
    satirlar = [
        f"ULAK HABERLEŞME MEDYA KRİZ UYARISI",
        f"Seviye : {seviye.value.upper()}",
        f"Tarih  : {simdi.strftime('%d.%m.%Y %H:%M')}",
        f"",
        f"GEREKÇE:",
        aciklama,
        f"",
        f"İLGİLİ HABERLER ({len(kritik_haberler)} adet):",
    ]
    for h in kritik_haberler[:10]:
        tarih = h.tarih.strftime("%d.%m.%Y") if h.tarih else "?"
        satirlar.append(f"  [{tarih}] {h.baslik}")
        if h.ai_ozet:
            satirlar.append(f"           {h.ai_ozet[:150]}")

    yol.write_text("\n".join(satirlar), encoding="utf-8")
    logger.info(f"Alert dosyası oluşturuldu: {yol}")
