import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

from config.settings import LOG_DIR
from src.database import init_db, haber_kaydet, rapor_kaydet
from src.news_fetcher import haberleri_cek
from src.crawler_agent import web_haberleri_cek
from src.analyzer import haberleri_analiz_et, yonetici_ozeti_uret
from src.report_generator import rapor_olustur
from src.email_sender import rapor_gonder, hata_bildir, kriz_bildir
from src.competitor_tracker import rakip_haberleri_cek, hisse_verileri_cek, hisse_hareket_acikla
from src.crisis_detector import kriz_degerlendir, KrizSeviyesi
from src.clusterer import haberleri_kumele
from src.agent import ajan_calistir, ajan_raporu_formatla
from src.press_scraper import press_haberleri_cek
from src.linkedin_tracker import linkedin_gonderileri_cek

logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
logger.add(
    LOG_DIR / "rapor_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="1 week",
    retention="4 weeks",
    encoding="utf-8",
)


def rapor_uret(gun: int = 7, rakip_filtre: str | None = None, tenant_id: int = 1):
    logger.info("=== Ulak Haberleşme Haftalık Rapor Üretimi Başlıyor ===")
    baslangic_zaman = time.monotonic()
    adim = "başlatma"

    try:
        init_db()

        # 1. Haber çekme — RSS + Web crawl
        adim = "haber çekme"
        logger.info("1/6 — Haberler çekiliyor (RSS + Web + Resmi Site)...")
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

        # 2. Rakip firma haberleri + borsa verileri
        adim = "rakip/borsa verisi"
        secili_rakipler = [r.strip() for r in rakip_filtre.split(",")] if rakip_filtre else None
        logger.info("2/6 — Rakip firma haberleri ve borsa verileri çekiliyor...")
        rakip_haberler = rakip_haberleri_cek(gun=gun, filtre=secili_rakipler)
        hisse_listesi  = hisse_verileri_cek(filtre=secili_rakipler)
        hisse_listesi  = hisse_hareket_acikla(hisse_listesi, rakip_haberler)

        # Kendi şirket haberi yoksa bile rakip haberi varsa rapor değerlidir —
        # sadece ikisi de tamamen boşsa üretimden vazgeç. (Önceden sadece
        # kendi haberi yoksa TÜM rapor iptal ediliyordu; rakip haberi bol
        # olsa bile hiçbir şey üretilmiyordu.)
        toplam_rakip_haber = sum(len(v) for v in rakip_haberler.values())
        if not haberler and not toplam_rakip_haber:
            logger.warning("Ne kendi ne de rakip haberi bulunamadı, rapor üretilmedi.")
            return

        # 3. AI analizi
        adim = "AI analizi"
        logger.info(f"3/6 — {len(haberler)} haber analiz ediliyor...")
        haberler = haberleri_analiz_et(haberler)

        # 4. Kriz değerlendirmesi
        adim = "kriz değerlendirmesi"
        kriz_seviyesi = kriz_degerlendir(haberler)
        if kriz_seviyesi in (KrizSeviyesi.KRIZ, KrizSeviyesi.DIKKAT):
            from src.crisis_detector import kriz_tespit_et
            _, aciklama = kriz_tespit_et(haberler)
            kriz_bildir(kriz_seviyesi.value, aciklama, haberler)

        # 5. Özerk ajan değerlendirmesi
        adim = "ajan analizi"
        logger.info("4/6 — Özerk ajan haberleri değerlendiriyor...")
        ajan_raporu = ajan_calistir(haberler)
        ajan_ozeti  = ajan_raporu_formatla(ajan_raporu)

        # 6. LinkedIn
        adim = "LinkedIn"
        logger.info("5/6 — LinkedIn gönderileri toplanıyor...")
        linkedin_raporu = linkedin_gonderileri_cek(gun=7)

        # 7. Yönetici özeti — PDF'de artık gösterilmiyor ama haftalık
        # e-posta bildiriminin gövdesi için hâlâ üretiliyor (rapor_gonder).
        adim = "yönetici özeti"
        logger.info("6/6 — Yönetici özeti üretiliyor (e-posta için)...")
        yonetici_ozeti = ajan_ozeti + "\n\n" + yonetici_ozeti_uret(haberler)

        # Rapor üret ve kaydet
        adim = "rapor üretimi"
        logger.info("Rapor oluşturuluyor ve kaydediliyor...")
        cikti = rapor_olustur(haberler,
                              rakip_haberler=rakip_haberler,
                              hisse_listesi=hisse_listesi,
                              linkedin_raporu=linkedin_raporu)

        bitis = datetime.now()
        rapor_id = rapor_kaydet(bitis - timedelta(days=7), bitis, len(haberler), cikti, tenant_id=tenant_id)
        for haber in haberler:
            haber_kaydet(haber, rapor_id=rapor_id, tenant_id=tenant_id)

        rapor_gonder(cikti, haberler, yonetici_ozeti)

        sure = time.monotonic() - baslangic_zaman
        logger.info(f"=== Tamamlandı! Rapor: {cikti} | DB rapor_id: {rapor_id} | Süre: {sure:.0f}sn ===")
        return cikti

    except Exception as hata:
        sure = time.monotonic() - baslangic_zaman
        logger.error(f"Pipeline hatası ({adim}): {hata}")
        hata_bildir(hata, adim, sure_sn=sure)
        raise


def _parse_args():
    parser = argparse.ArgumentParser(description="Ulak Haberleşme haftalık rapor pipeline")
    parser.add_argument("--gun", type=int, default=7,
                        help="Kaç günlük haberleri tara (varsayılan: 7)")
    parser.add_argument("--rakipler", type=str, default=None,
                        help="Virgülle ayrılmış rakip firma adları (varsayılan: hepsi)")
    parser.add_argument("--tenant", type=int, default=None,
                        help="Tenant ID (çok kiracılı mod)")
    parser.add_argument("--sadece-ben", action="store_true",
                        help="Rakip analizi atla, yalnızca kendi haberler")
    return parser.parse_args()


if __name__ == "__main__":
    _args = _parse_args()
    rakip_filtre = None if _args.sadece_ben else _args.rakipler
    _sonuc = rapor_uret(gun=_args.gun, rakip_filtre=rakip_filtre, tenant_id=_args.tenant or 1)
    if _sonuc is None:
        # Haber bulunamadığı için rapor üretilmedi (bkz. rapor_uret içindeki
        # "Hiç haber bulunamadı" uyarısı). Exit code 0 dönersek report_jobs.py
        # bunu "tamamlandı" sanıp DB'deki EN SON (eski/alakasız) raporu bu işe
        # bağlıyordu — kullanıcıya "PDF yok" hatası veren, kafa karıştırıcı bir
        # sahte başarı görünümü. Ayrı bir exit code ile net bir "hata" bildir.
        sys.exit(2)
