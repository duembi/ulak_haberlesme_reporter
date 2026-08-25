import argparse
import sys
import time
from datetime import datetime, timedelta
from loguru import logger

from config.settings import LOG_DIR
from src.database import init_db, haber_kaydet
from src.news_fetcher import haberleri_cek
from src.crawler_agent import web_haberleri_cek
from src.analyzer import haberleri_analiz_et
from src.crisis_detector import kriz_degerlendir
from src.clusterer import haberleri_kumele
from src.press_scraper import press_haberleri_cek

logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
logger.add(
    LOG_DIR / "rapor_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="1 week",
    retention="4 weeks",
    encoding="utf-8",
)


def haberleri_guncelle(gun: int = 7, tenant_id: int = 1):
    logger.info("=== Ulak Haberleşme Medya Takibi Başlıyor ===")
    baslangic_zaman = time.monotonic()
    adim = "başlatma"

    try:
        init_db()

        # 1. Haber çekme — RSS + Web crawl + Resmi site
        adim = "haber çekme"
        logger.info("1/4 — Haberler çekiliyor (RSS + Web + Resmi Site)...")
        haberler       = haberleri_cek(gun=gun)
        web_haberler   = web_haberleri_cek(gun=gun)
        press_haberler = press_haberleri_cek(gun=gun)

        goruldu = {h.url for h in haberler}
        for h in web_haberler + press_haberler:
            if h.url and h.url not in goruldu:
                haberler.append(h)
                goruldu.add(h.url)

        logger.info(f"Toplam haber (tüm kaynaklar): {len(haberler)}")

        # Tarih bilinmeyen veya seçilen süreden eski haberleri filtrele
        _esik = datetime.now() - timedelta(days=gun)
        haberler_oncesi = len(haberler)
        haberler = [h for h in haberler if h.tarih is not None and h.tarih >= _esik]
        if haberler_oncesi != len(haberler):
            logger.info(
                f"{haberler_oncesi - len(haberler)} haber elendi "
                f"(tarihi bilinmeyen veya {gun}+ gün eski)"
            )

        haberler = haberleri_kumele(haberler)

        if not haberler:
            logger.warning("Haber bulunamadı, kaydedilecek bir şey yok.")
            return 0

        # 2. AI analizi
        adim = "AI analizi"
        logger.info(f"2/4 — {len(haberler)} haber analiz ediliyor...")
        haberler = haberleri_analiz_et(haberler)

        # 3. Kriz değerlendirmesi — loglar ve gerekirse alerts/ dosyası bırakır
        adim = "kriz değerlendirmesi"
        logger.info("3/4 — Kriz değerlendirmesi yapılıyor...")
        kriz_degerlendir(haberler)

        # 4. Veritabanına kaydet
        adim = "veritabanına kaydetme"
        logger.info("4/4 — Haberler veritabanına kaydediliyor...")
        kaydedilen = 0
        for haber in haberler:
            if haber_kaydet(haber, tenant_id=tenant_id):
                kaydedilen += 1

        sure = time.monotonic() - baslangic_zaman
        logger.info(f"=== Tamamlandı! {kaydedilen}/{len(haberler)} haber kaydedildi | Süre: {sure:.0f}sn ===")
        return kaydedilen

    except Exception as hata:
        sure = time.monotonic() - baslangic_zaman
        logger.error(f"Pipeline hatası ({adim}): {hata}")
        raise


def _parse_args():
    parser = argparse.ArgumentParser(description="Ulak Haberleşme medya takip pipeline")
    parser.add_argument("--gun", type=int, default=7,
                        help="Kaç günlük haberleri tara (varsayılan: 7)")
    parser.add_argument("--tenant", type=int, default=None,
                        help="Tenant ID (çok kiracılı mod)")
    return parser.parse_args()


if __name__ == "__main__":
    _args = _parse_args()
    _sonuc = haberleri_guncelle(gun=_args.gun, tenant_id=_args.tenant or 1)
    if not _sonuc:
        # Haber bulunamadı — pipeline.py bunu ayrı bir hata olarak ele alabilsin
        # diye net bir exit code döndürülür.
        sys.exit(2)
