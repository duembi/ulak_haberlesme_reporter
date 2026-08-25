import json
import time
from loguru import logger

from src.ai_client import sorgula
from src.news_fetcher import Haber


_BATCH_PROMPT_TEMPLATE = """\
Ulak Haberleşme A.Ş. ile ilgili {sayi} haberi analiz et. SADECE geçerli JSON döndür.

{haberler}

Her haber için şu yapıyı kullan:
{{
  "sonuclar": [
    {{
      "indeks": 0,
      "ozet": "Türkçe 2-3 cümlelik yönetici özeti",
      "kategori": "teknoloji | finans | şirket haberi | politika | uluslararası | diğer",
      "triples": [
        ["Kaynak Varlık", "ilişki türü", "Hedef Varlık"]
      ]
    }}
  ]
}}

Triple kuralları:
- Varlıklar: şirket, kurum, teknoloji, kişi, ülke, ürün adı (kısa, öz)
- İlişki türleri: "anlaşma imzaladı", "satın aldı", "ortaklık kurdu", "rekabet ediyor",
  "hizmet sunuyor", "yatırım yaptı", "ihale kazandı", "fiyat düşürdü", "büyüdü",
  "geliştirdi", "kullanıyor", "destekledi", "eleştirdi", "denetledi"
- Haberde net ilişki yoksa triples boş liste []
- Her haberden en fazla 3 triple

SADECE JSON döndür, başka hiçbir şey yazma."""

_YONETICI_OZET_TEMPLATE = """\
Ulak Haberleşme A.Ş. üst yönetimi için haftalık medya bülteni hazırlıyorsun.
Elindeki araçları kullanarak (get_sentiment_trend, search_company_news) geçmiş haftalardaki \
trend bilgisini ve eksik bağlamı tamamlayabilirsin.

Aşağıdaki haber özetlerini ve sentiment bilgilerini kullanarak Türkçe, akıcı, 3-5 paragraf \
uzunluğunda yönetici özeti yaz. Önemli gelişmeleri, genel medya tonunu, önceki haftalarla \
kıyaslamalı trendi ve dikkat çeken konuları vurgula.

DİKKAT — yanlış eşleşme riski: "Ulak" Türkçe'de sıradan bir kelimedir (haberci/kurye anlamında) \
ve şirketle hiç ilgisi olmayan haberlerde de geçebilir (ör. başka bir kurumun/olayın "ulak sistemi" \
diye andığı bir şey). Bir haberde şirketin adı ("Ulak Haberleşme") açıkça geçmiyorsa, sadece "ulak" \
kelimesi geçiyor diye bunu şirketle ilgili, acil veya kriz niteliğinde bir konu gibi sunma — bunun \
yerine haberin şirketle gerçekten ilgisiz olduğunu açıkça belirt ve "acil konu" listesine ekleme.

ÖNEMLİ — kaynak atfı: Aşağıdaki haber listesindeki her haberin başında bir numara var \
(ör. "3. [OLUMLU] ..."). Özette belirli bir habere/gelişmeye değindiğinde, cümlenin sonuna \
o haberin numarasını köşeli parantez içinde ekle (ör: "...yeni anlaşma imzalandı [3]."). \
Okuyucu bu numaraya tıklayarak kaynağa ulaşabilecek, bu yüzden numaraları doğru ve \
tutarlı kullan — uydurma numara ekleme, sadece verilen listedeki numaraları kullan.
SADECE özet metnini yaz, başka hiçbir şey ekleme.

Haber listesi:
{haber_listesi}"""


_BATCH_BOYUTU = 5
_BATCH_ARASI_BEKLEME = 15  # saniye — Gemini rate limit koruması


def _json_temizle(metin: str) -> str:
    if "```" in metin:
        for parca in metin.split("```"):
            parca = parca.strip()
            if parca.startswith("json"):
                parca = parca[4:].strip()
            if parca.startswith("{"):
                return parca
    return metin


def _batch_analiz_et(batch: list[Haber]) -> list[dict]:
    """Haberleri tek Claude çağrısıyla analiz eder. Batch-relative (0-tabanlı) indeks kullanır."""
    haber_metni = "\n\n".join([
        f"[{i}] Başlık: {h.baslik}\n"
        f"Açıklama: {h.ozet[:300]}\n"
        f"Dil: {'Türkçe' if h.dil == 'tr' else 'İngilizce'}"
        for i, h in enumerate(batch)
    ])
    prompt = _BATCH_PROMPT_TEMPLATE.format(
        sayi=len(batch),
        haberler=haber_metni,
    )
    try:
        metin = sorgula(prompt)
        metin = _json_temizle(metin)
        veri = json.loads(metin)
        return veri.get("sonuclar", [])
    except Exception as e:
        logger.warning(f"Batch analiz hatası: {e}")
        return []


def haberleri_analiz_et(haberler: list[Haber]) -> list[Haber]:
    """Haberleri batch'ler halinde Claude CLI ile analiz eder."""
    logger.info(f"{len(haberler)} haber analiz ediliyor...")

    # global_indeks → sonuç sözlüğü
    sonuc_map: dict[int, dict] = {}

    for batch_no, baslangic in enumerate(range(0, len(haberler), _BATCH_BOYUTU)):
        if batch_no > 0:
            logger.info(f"  Rate limit koruması: {_BATCH_ARASI_BEKLEME}s bekleniyor...")
            time.sleep(_BATCH_ARASI_BEKLEME)
        batch = haberler[baslangic: baslangic + _BATCH_BOYUTU]
        sonuclar = _batch_analiz_et(batch)
        for item in sonuclar:
            # Claude batch-relative (0-tabanlı) indeks döndürür; global indekse çevir
            rel_idx = item.get("indeks", -1)
            if isinstance(rel_idx, int) and 0 <= rel_idx < len(batch):
                global_idx = baslangic + rel_idx
                sonuc_map[global_idx] = item
        logger.info(
            f"  Batch {batch_no + 1}: {baslangic}–{baslangic + len(batch) - 1} "
            f"({len(sonuclar)}/{len(batch)} analiz edildi)"
        )

    # Sonuçları haber nesnelerine yaz
    for i, haber in enumerate(haberler):
        sonuc = sonuc_map.get(i, {})
        # ai_ozet: Claude'dan gelen özeti kullan; yoksa ham özeti kırp (başlık tekrar etme)
        ai_ozet_ham = sonuc.get("ozet", "")
        if ai_ozet_ham:
            haber.ai_ozet = ai_ozet_ham
        elif haber.ozet and haber.ozet.strip() != haber.baslik.strip():
            haber.ai_ozet = haber.ozet[:300]
        else:
            haber.ai_ozet = ""
        haber.kategori  = sonuc.get("kategori",   "diğer")
        raw_triples = sonuc.get("triples", [])
        haber.triples   = [t for t in raw_triples if isinstance(t, list) and len(t) == 3]

    logger.info("Analiz tamamlandı")
    return haberler


_TEKNIK_NOT_KALIPLARI = [
    "araç izinleri verilmediğinden",
    "elinizdeki haber listesine dayanarak",
    "doğrudan yazıyorum",
    "mcp araçlarına erişimim",
    "araçlara erişimim yok",
    "tool",
    "bu bir sistem notu",
]


def _teknik_notlari_temizle(metin: str) -> str:
    """Claude'un iç notlarını ve meta açıklamalarını çıktıdan kaldırır."""
    satirlar = metin.splitlines()
    temiz = []
    for satir in satirlar:
        alt = satir.lower()
        if any(kalip in alt for kalip in _TEKNIK_NOT_KALIPLARI):
            continue
        temiz.append(satir)
    return "\n".join(temiz).strip()


def yonetici_ozeti_uret(haberler: list[Haber]) -> str:
    """Tüm haberlerden konsolide yönetici özeti üretir."""
    if not haberler:
        return "Bu hafta Ulak Haberleşme ile ilgili haber bulunamadı."

    # Numaralar rapor PDF'indeki Referanslar bölümüyle eşleşsin diye orijinal
    # haberler listesindeki sırayla (1'den başlayarak) numaralandırılır.
    haber_listesi = "\n".join([
        f"{i}. [{h.sentiment.upper()}] {h.baslik} | {h.ai_ozet}"
        for i, h in enumerate(haberler[:40], 1)
    ])
    prompt = _YONETICI_OZET_TEMPLATE.format(haber_listesi=haber_listesi)

    try:
        ham = sorgula(prompt, mcp=True)
        return _teknik_notlari_temizle(ham)
    except Exception as e:
        logger.error(f"Yönetici özeti üretilemedi: {e}")
        # Hata mesajı yerine mevcut verileri kullanarak temel özet üret
        olumlu = sum(1 for h in haberler if h.sentiment == "olumlu")
        olumsuz = sum(1 for h in haberler if h.sentiment == "olumsuz")
        notr = len(haberler) - olumlu - olumsuz
        return (
            f"Bu hafta Ulak Haberleşme A.Ş. ile ilgili toplam {len(haberler)} haber analiz edildi. "
            f"Haberlerin {olumlu} adedi olumlu, {olumsuz} adedi olumsuz, {notr} adedi nötr tonda değerlendirildi. "
            f"Detaylı bilgi için aşağıdaki kategori bazlı haber listesini inceleyiniz."
        )
