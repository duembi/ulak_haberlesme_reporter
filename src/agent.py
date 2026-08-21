"""
Özerk AI Ajanı — Ulak Haberleşme Medya Takip Sistemi

Claude, MCP araçlarını kullanarak haberleri kendi muhakemesiyle değerlendirir:
  - Her haber için 1-10 önem skoru atar
  - Gerekli gördüğünde ek web araştırması yapar
  - Aksiyon önerir: NORMAL / TAKİP / YÖNETİME_BİLDİR / ACİL
  - Gerekçesini Türkçe açıklar
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from loguru import logger

from config.settings import BASE_DIR
from src.ai_client import sorgula
from src.news_fetcher import Haber

_ALERTS_DIR = BASE_DIR / "alerts"
_ALERTS_DIR.mkdir(exist_ok=True)


class Aksiyon(str, Enum):
    NORMAL           = "NORMAL"
    TAKIP            = "TAKİP"
    YONETIME_BILDIR  = "YÖNETİME_BİLDİR"
    ACIL             = "ACİL"


@dataclass
class AjanKarari:
    haber_baslik: str
    onem_skoru: int            # 1-10
    aksiyon: Aksiyon
    gerekcé: str
    ek_bulgular: str = ""      # Ajan web araştırması yaptıysa buraya yazar
    url: str = ""


@dataclass
class AjanRaporu:
    tarih: datetime = field(default_factory=datetime.now)
    kararlar: list[AjanKarari] = field(default_factory=list)
    ozet: str = ""

    @property
    def acil_haberler(self) -> list[AjanKarari]:
        return [k for k in self.kararlar if k.aksiyon == Aksiyon.ACIL]

    @property
    def bildirim_haberler(self) -> list[AjanKarari]:
        return [k for k in self.kararlar if k.aksiyon == Aksiyon.YONETIME_BILDIR]


# ── Prompt şablonları ────────────────────────────────────────────────────────

_SISTEM_PROMPTU = """\
Sen Ulak Haberleşme A.Ş.'nin medya takip yapay zeka ajanısın.
Görevin: verilen haberleri Ulak Haberleşme'nin kurumsal çıkarları açısından değerlendirmek.

Ulak Haberleşme'nin öncelikleri:
- 5G baz istasyonu ve çekirdek şebeke yazılımı geliştirme
- Yazılım tabanlı taktik telsiz (V/UHF) projeleri
- Kamu güvenliği ve acil durum haberleşme şebekeleri
- Kurumsal itibar ve medyada algı
- Rekabet ortamı (ASELSAN, HAVELSAN, yabancı 5G/telekom tedarikçileri)
- Finansal performans ve ihale/sözleşmeler (SSB projeleri dahil)
- Düzenleyici/yasal gelişmeler
- Uluslararası işbirlikleri

Elindeki araçlar:
- search_company_news: Bir konu hakkında güncel haber arayabilirsin
- crawl_page: Bir haberin tam içeriğini okuyabilirsin
- get_sentiment_trend: Geçmiş haftalardaki medya tonunu görebilirsin

ÖNEMLİ: Şüpheli veya kritik bir haber gördüğünde araçları kullanarak daha fazla araştır.
Analiz sonucunu SADECE geçerli JSON olarak döndür."""

_HABER_DEGERLENDIRME_PROMPTU = """\
Aşağıdaki {haber_sayisi} haberi değerlendir.

{haber_listesi}

Her haber için şu JSON yapısını kullan:
{{
  "kararlar": [
    {{
      "baslik": "haberin tam başlığı",
      "onem_skoru": 1-10 arası integer,
      "aksiyon": "NORMAL | TAKİP | YÖNETİME_BİLDİR | ACİL",
      "gerekce": "Türkçe 1-2 cümle gerekçe",
      "ek_bulgular": "araç kullandıysan bulguları yaz, kullanmadıysan boş bırak"
    }}
  ],
  "haftalik_ozet": "Tüm haberlere bakarak Ulak Haberleşme için bu haftanın Türkçe 2-3 cümlelik genel değerlendirmesi"
}}

Önem skoru rehberi:
1-3: Rutin haber, sektörel ilgi
4-6: Ulak Haberleşme'yi dolaylı etkileyen gelişme
7-8: Doğrudan etki, yönetim bilgilendirilmeli
9-10: Kurumsal kriz riski veya stratejik fırsat

ACİL aksiyonu için: yasal tehdit, itibar krizi, büyük operasyonel sorun, acil stratejik fırsat.
YÖNETİME_BİLDİR: önem skoru 7+ veya rakip kritik hamle yaptı.
TAKİP: önem skoru 4-6, gelişim izlenmeli.
NORMAL: rutin haber."""


# ── Yardımcı fonksiyonlar ────────────────────────────────────────────────────



def _json_temizle(metin: str) -> str:
    """Claude bazen ```json ... ``` bloğu döner, temizler."""
    if "```" in metin:
        parcalar = metin.split("```")
        for p in parcalar:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                return p
    return metin


def _haberleri_formatla(haberler: list[Haber], max_haber: int = 30) -> str:
    satirlar = []
    for i, h in enumerate(haberler[:max_haber], 1):
        tarih = h.tarih.strftime("%d.%m.%Y") if h.tarih else "?"
        satirlar.append(
            f"{i}. [{tarih}] [{h.sentiment or '?'}] {h.baslik}\n"
            f"   Kaynak: {h.kaynak} | Özet: {(h.ai_ozet or h.ozet)[:200]}"
        )
    return "\n\n".join(satirlar)


# ── Ana ajan fonksiyonu ──────────────────────────────────────────────────────

def ajan_calistir(haberler: list[Haber]) -> AjanRaporu:
    """
    Özerk ajanı çalıştırır.
    Haberleri Claude'a gönderir, MCP araçlarıyla araştırmasına izin verir,
    yapılandırılmış karar raporu döner.
    """
    if not haberler:
        logger.warning("Ajan: haber listesi boş")
        return AjanRaporu(ozet="Değerlendirilecek haber bulunamadı.")

    logger.info(f"Özerk ajan başlatıldı — {len(haberler)} haber değerlendirilecek")

    haber_metni = _haberleri_formatla(haberler)
    prompt = _HABER_DEGERLENDIRME_PROMPTU.format(
        haber_sayisi=len(haberler[:30]),
        haber_listesi=haber_metni,
    )

    try:
        yanit = sorgula(prompt, sistem=_SISTEM_PROMPTU, mcp=True)
        yanit = _json_temizle(yanit)
        veri  = json.loads(yanit)
    except json.JSONDecodeError as e:
        logger.error(f"Ajan JSON parse hatası: {e}\nYanıt: {yanit[:300]}")
        return AjanRaporu(ozet="Ajan yanıtı işlenemedi.")
    except Exception as e:
        logger.error(f"Ajan çağrısı başarısız: {e}")
        return AjanRaporu(ozet="Ajan çalıştırılamadı.")

    # Kararları parse et
    kararlar: list[AjanKarari] = []
    haber_url_map = {h.baslik[:60]: h.url for h in haberler}

    for k in veri.get("kararlar", []):
        try:
            aksiyon = Aksiyon(k.get("aksiyon", "NORMAL"))
        except ValueError:
            aksiyon = Aksiyon.NORMAL

        baslik = k.get("baslik", "")
        url    = next((v for key, v in haber_url_map.items()
                       if key[:40] in baslik[:40]), "")

        kararlar.append(AjanKarari(
            haber_baslik=baslik,
            onem_skoru=int(k.get("onem_skoru", 5)),
            aksiyon=aksiyon,
            gerekcé=k.get("gerekce", ""),
            ek_bulgular=k.get("ek_bulgular", ""),
            url=url,
        ))

    kararlar.sort(key=lambda x: x.onem_skoru, reverse=True)
    ozet = veri.get("haftalik_ozet", "")

    rapor = AjanRaporu(kararlar=kararlar, ozet=ozet)

    # Loglama ve alert dosyası
    acil_sayisi    = len(rapor.acil_haberler)
    bildirim_sayisi = len(rapor.bildirim_haberler)
    logger.info(
        f"Ajan değerlendirmesi tamamlandı — "
        f"ACİL: {acil_sayisi} | YÖNETİME_BİLDİR: {bildirim_sayisi} | "
        f"Toplam: {len(kararlar)}"
    )

    if acil_sayisi > 0:
        logger.error(f"🚨 ACİL: {acil_sayisi} kritik haber tespit edildi!")
        _alert_yaz(rapor)
    elif bildirim_sayisi > 0:
        logger.warning(f"⚠️  {bildirim_sayisi} haber yönetime bildirilmeli")

    return rapor


def _alert_yaz(rapor: AjanRaporu):
    """Kritik kararları alerts/ klasörüne yazar."""
    dosya = _ALERTS_DIR / f"AJAN_ALERT_{rapor.tarih.strftime('%Y%m%d_%H%M%S')}.txt"
    satirlar = [
        "ULAK HABERLEŞME MEDYA AJAN UYARISI",
        f"Tarih: {rapor.tarih.strftime('%d.%m.%Y %H:%M')}",
        "",
        "ACİL HABERLER:",
    ]
    for k in rapor.acil_haberler:
        satirlar += [
            f"  ⚠️  [{k.onem_skoru}/10] {k.haber_baslik}",
            f"      Gerekçe: {k.gerekcé}",
            f"      {k.ek_bulgular}" if k.ek_bulgular else "",
            "",
        ]
    satirlar += ["", "YÖNETİME BİLDİRİLECEKLER:"]
    for k in rapor.bildirim_haberler:
        satirlar.append(f"  • [{k.onem_skoru}/10] {k.haber_baslik}: {k.gerekcé}")

    satirlar += ["", "GENEL DEĞERLENDİRME:", rapor.ozet]
    dosya.write_text("\n".join(satirlar), encoding="utf-8")
    logger.info(f"Ajan alert dosyası: {dosya}")


def ajan_raporu_formatla(rapor: AjanRaporu) -> str:
    """
    Ajan raporunu rapor_generator.py'nin kullanabileceği
    yönetici özeti formatına dönüştürür.
    """
    satirlar = []

    if rapor.acil_haberler:
        satirlar.append("🚨 ACİL KONULAR")
        for k in rapor.acil_haberler:
            satirlar.append(f"• {k.haber_baslik} (Önem: {k.onem_skoru}/10)")
            satirlar.append(f"  {k.gerekcé}")
        satirlar.append("")

    if rapor.bildirim_haberler:
        satirlar.append("📌 YÖNETİME BİLDİRİLECEKLER")
        for k in rapor.bildirim_haberler:
            satirlar.append(f"• {k.haber_baslik} (Önem: {k.onem_skoru}/10)")
            satirlar.append(f"  {k.gerekcé}")
        satirlar.append("")

    if rapor.ozet:
        satirlar.append("GENEL DEĞERLENDİRME")
        satirlar.append(rapor.ozet)

    return "\n".join(satirlar)
