"""
Ulak Haberleşme LinkedIn Takip Modülü

Ulak Haberleşme A.Ş.'nin resmi LinkedIn şirket sayfasından son gönderileri çeker.
Teknik not: LinkedIn JavaScript render ettiği için doğrudan sayfa çekimi sınırlıdır.
DuckDuckGo arama + trafilatura ile public içerik elde edilir; gerçek etkileşim
sayıları (beğeni/yorum/paylaşım) için LinkedIn API Partnership gerekmektedir.
Claude analizi ile gönderi önem sıralaması yapılır.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import requests
from loguru import logger

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

try:
    import trafilatura
    _TRAFILATURA_VAR = True
except ImportError:
    _TRAFILATURA_VAR = False

from config.settings import BASE_DIR
from src.ai_client import sorgula

_TAG_AYAR_DOSYASI = BASE_DIR / "config" / "linkedin_tags.json"


def _secili_tagleri_oku() -> list[str]:
    """Kullanıcının UI'dan seçtiği LinkedIn hashtaglerini döndürür."""
    if _TAG_AYAR_DOSYASI.exists():
        try:
            import json as _json
            return _json.loads(_TAG_AYAR_DOSYASI.read_text(encoding="utf-8")).get("secili", [])
        except Exception:
            pass
    return []

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

LINKEDIN_SIRKET_URL = "https://www.linkedin.com/company/ulakhaberlesme"
LINKEDIN_SIRKET_ADI = "Ulak Haberleşme"


# ── Veri modeli ──────────────────────────────────────────────────────────────

@dataclass
class LinkedInGonderi:
    baslik: str                    # Gönderi başlığı / ilk satır
    icerik: str                    # Gönderi metni
    url: str                       # LinkedIn linki
    yazar: str = ""                # Paylaşan kişi / şirket
    tarih: Optional[datetime] = None
    etkilesim_tahmini: int = 0     # Claude tarafından önem skoru (1-10)
    etkilesim_aciklama: str = ""   # Claude gerekçesi
    kaynak: str = "LinkedIn"


@dataclass
class LinkedInRaporu:
    gonderiler: list[LinkedInGonderi] = field(default_factory=list)
    ozet: str = ""
    toplama_tarihi: datetime = field(default_factory=datetime.now)


# ── Veri toplama ─────────────────────────────────────────────────────────────

def _ddg_linkedin_ara(gun: int = 7) -> list[dict]:
    """DuckDuckGo ile son N günde yayınlanmış LinkedIn gönderilerini arar."""
    sonuclar: list[dict] = []
    esik = datetime.now() - timedelta(days=gun)

    # Kullanıcının seçtiği taglerle ek sorgular oluştur
    secili_tagler = _secili_tagleri_oku()
    tag_sorgulari = [
        f'site:linkedin.com/posts {tag}' for tag in secili_tagler[:10]
    ]

    sorgular = [
        f'site:linkedin.com/posts "Ulak Haberleşme"',
        f'site:linkedin.com/posts "Ulak Haberlesme"',
        f'site:linkedin.com/company/ulakhaberlesme',
        *tag_sorgulari,
    ]

    logger.info(f"LinkedIn araması: {len(secili_tagler)} seçili tag ile {len(sorgular)} sorgu yapılacak")

    _ULAK_ANAHTAR = {"ulak haberleşme", "ulak haberlesme", "ulakhaberlesme"}

    def _ilgili_mi(baslik: str, ozet: str, url: str) -> bool:
        birlesik = (baslik + " " + ozet + " " + url).lower()
        return any(k in birlesik for k in _ULAK_ANAHTAR)

    goruldu: set[str] = set()
    try:
        with DDGS() as ddgs:
            for sorgu in sorgular:
                time.sleep(2)
                try:
                    for r in ddgs.text(sorgu, max_results=10, timelimit="w"):
                        url = r.get("href", "") or r.get("url", "")
                        if url in goruldu:
                            continue
                        if "linkedin.com" not in url:
                            continue
                        baslik = r.get("title", "")
                        ozet_m = r.get("body", "") or r.get("snippet", "")
                        if not _ilgili_mi(baslik, ozet_m, url):
                            logger.debug(f"LinkedIn sonucu Ulak Haberleşme ile ilgisiz, atlandı: {url[:60]}")
                            continue
                        goruldu.add(url)
                        sonuclar.append({
                            "baslik": baslik,
                            "ozet":   ozet_m,
                            "url":    url,
                        })
                except Exception as e:
                    logger.debug(f"DDG sorgu hatası ({sorgu[:40]}): {e}")
    except Exception as e:
        logger.error(f"DuckDuckGo bağlantı hatası: {e}")

    logger.info(f"LinkedIn DDG araması: {len(sonuclar)} sonuç bulundu")
    return sonuclar


def _linkedin_sayfa_cek(url: str) -> str:
    """
    Tek bir LinkedIn URL'sinin içeriğini çekmeye çalışır.
    LinkedIn JS render ettiğinden içerik kısmi olabilir.
    """
    if not _TRAFILATURA_VAR:
        return ""
    try:
        time.sleep(1.5)
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            metin = trafilatura.extract(downloaded, include_comments=False,
                                        include_tables=False) or ""
            return metin[:1000]
    except Exception as e:
        logger.debug(f"LinkedIn sayfa çekme hatası ({url[:60]}): {e}")
    return ""


def _sirket_sayfasi_cek() -> list[dict]:
    """
    Ulak Haberleşme'nin resmi LinkedIn sayfasını doğrudan çekmeyi dener.
    JavaScript nedeniyle gönderi listesi gelmeyebilir; meta verileri alınır.
    """
    sonuclar = []
    try:
        resp = requests.get(
            LINKEDIN_SIRKET_URL,
            headers=_HEADERS,
            timeout=15,
            allow_redirects=True,
        )
        if resp.status_code == 200 and "linkedin" in resp.url:
            metin = resp.text

            # Open Graph meta başlıklarından bilgi topla
            og_desc = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', metin)
            og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', metin)

            if og_title or og_desc:
                sonuclar.append({
                    "baslik": og_title.group(1) if og_title else LINKEDIN_SIRKET_ADI,
                    "ozet":   og_desc.group(1) if og_desc else "",
                    "url":    LINKEDIN_SIRKET_URL,
                })
    except Exception as e:
        logger.debug(f"LinkedIn şirket sayfası hatası: {e}")
    return sonuclar


# ── Claude ile analiz ve sıralama ────────────────────────────────────────────

_ANALIZ_PROMPTU = """\
Ulak Haberleşme A.Ş.'nin LinkedIn'den bulunan aşağıdaki {sayi} gönderiyi/içeriği analiz et.

{gonderiler}

Her gönderi için şu JSON yapısını kullan:
{{
  "gonderiler": [
    {{
      "indeks": 0,
      "onem_skoru": 1-10,
      "gerekce": "Neden bu kadar önemli — 1 cümle Türkçe",
      "yazar_tahmini": "Şirket mi, yönetici mi, çalışan mı?",
      "kategori": "duyuru | proje | etkinlik | basın | teknik | insan_kaynakları | genel"
    }}
  ],
  "en_onemli_3": [0, 1, 2],
  "ozet": "LinkedIn varlığının Türkçe 2 cümlelik genel değerlendirmesi"
}}

Önem skoru kriterleri (Ulak Haberleşme kurumsal perspektifi):
9-10: Stratejik duyuru, büyük sözleşme, üst yönetim paylaşımı
7-8: Proje lansmanı, teknik başarı, kurumsal etkinlik
4-6: Rutin içerik, işe alım, motivasyon paylaşımı
1-3: Genel sektör içeriği, alıntı

SADECE JSON döndür."""


def _gonderileri_analiz_et(
        ham_sonuclar: list[dict],
) -> LinkedInRaporu:
    """Claude ile gönderileri analiz eder, önem sırası çıkarır."""
    if not ham_sonuclar:
        return LinkedInRaporu(ozet="LinkedIn'den içerik bulunamadı.")

    # Ham veriyi LinkedInGonderi listesine çevir
    gonderiler: list[LinkedInGonderi] = []
    for r in ham_sonuclar:
        ek_icerik = ""
        if r["url"] and "linkedin.com" in r["url"] and _TRAFILATURA_VAR:
            ek_icerik = _linkedin_sayfa_cek(r["url"])

        icerik = ek_icerik or r.get("ozet", "") or r.get("baslik", "")
        gonderiler.append(LinkedInGonderi(
            baslik=r.get("baslik", "")[:200],
            icerik=icerik[:500],
            url=r.get("url", ""),
        ))

    gonderi_metni = "\n\n".join([
        f"[{i}] Başlık: {g.baslik}\n"
        f"İçerik: {g.icerik[:300]}\n"
        f"URL: {g.url}"
        for i, g in enumerate(gonderiler)
    ])

    prompt = _ANALIZ_PROMPTU.format(
        sayi=len(gonderiler),
        gonderiler=gonderi_metni,
    )

    try:
        yanit = sorgula(prompt)
        if "```" in yanit:
            parcalar = yanit.split("```")
            for p in parcalar:
                p = p.strip()
                if p.startswith("json"):
                    p = p[4:].strip()
                if p.startswith("{"):
                    yanit = p
                    break

        veri = json.loads(yanit)

        # Analiz sonuçlarını gönderilere işle
        for item in veri.get("gonderiler", []):
            idx = item.get("indeks", -1)
            if 0 <= idx < len(gonderiler):
                gonderiler[idx].etkilesim_tahmini = int(item.get("onem_skoru", 5))
                gonderiler[idx].etkilesim_aciklama = item.get("gerekce", "")
                gonderiler[idx].yazar = item.get("yazar_tahmini", "")

        # En önemli 3 gönderiyi seç
        en_onemli_idx = veri.get("en_onemli_3", [])
        if en_onemli_idx:
            secili = [gonderiler[i] for i in en_onemli_idx if i < len(gonderiler)]
        else:
            secili = sorted(gonderiler, key=lambda g: g.etkilesim_tahmini, reverse=True)[:3]

        ozet = veri.get("ozet", "")
        rapor = LinkedInRaporu(gonderiler=secili, ozet=ozet)
        logger.info(
            f"LinkedIn analizi tamamlandı — "
            f"{len(secili)} gönderi seçildi, "
            f"önem skorları: {[g.etkilesim_tahmini for g in secili]}"
        )
        return rapor

    except json.JSONDecodeError as e:
        logger.error(f"LinkedIn analiz JSON hatası: {e}")
    except Exception as e:
        logger.error(f"LinkedIn analiz hatası: {e}")

    # Fallback: en fazla 3 gönderi ham haliyle döndür
    return LinkedInRaporu(
        gonderiler=gonderiler[:3],
        ozet="Analiz tamamlanamadı.",
    )


# ── Firma bazlı ham arama (Dashboard "LinkedIn" popup'ı için) ─────────────────

def firma_linkedin_ara(firma_adi: str, tagler: list[str], gun: int = 30,
                        sonuc_basi: int = 15) -> list[dict]:
    """
    Verilen etiketlerle bir firma için LinkedIn gönderisi arar (DuckDuckGo).
    Claude analizi yapmaz — ham sonuç listesi döner (hızlı, popup için).
    """
    if not tagler:
        return []

    zaman_araligi = "w" if gun <= 7 else ("m" if gun <= 31 else None)
    sonuclar: list[dict] = []
    goruldu: set[str] = set()

    try:
        with DDGS() as ddgs:
            for tag in tagler[:12]:
                if len(sonuclar) >= sonuc_basi:
                    break
                sorgu = f"site:linkedin.com/posts {tag}"
                time.sleep(1.5)
                try:
                    for r in ddgs.text(sorgu, max_results=8, timelimit=zaman_araligi):
                        url = r.get("href", "") or r.get("url", "")
                        if not url or url in goruldu or "linkedin.com" not in url:
                            continue
                        goruldu.add(url)
                        sonuclar.append({
                            "baslik": r.get("title", ""),
                            "ozet": (r.get("body", "") or r.get("snippet", ""))[:300],
                            "url": url,
                            "tag": tag,
                        })
                        if len(sonuclar) >= sonuc_basi:
                            break
                except Exception as e:
                    logger.debug(f"Firma LinkedIn arama hatası ({firma_adi}, {sorgu[:40]}): {e}")
    except Exception as e:
        logger.error(f"DuckDuckGo bağlantı hatası ({firma_adi}): {e}")

    from src.relevans_filtre import relevans_maskesi
    maske = relevans_maskesi(firma_adi, [(s["baslik"], s["ozet"]) for s in sonuclar])
    sonuclar = [s for s, ilgili in zip(sonuclar, maske) if ilgili]

    logger.info(f"Firma LinkedIn araması — {firma_adi}: {len(sonuclar)} sonuç (relevans filtresi sonrası)")
    return sonuclar


# ── Firma tag üretimi + arama (Rakip Firmalar "Oluştur" akışı için) ───────────

_TAG_URETIM_SYSTEM = (
    "Sen bir sosyal medya ve pazar araştırması uzmanısın. "
    "LinkedIn'de takip edilecek anahtar kelimeleri ve hashtag'leri belirliyorsun. "
    "Yanıtlarını daima geçerli JSON formatında ver, başka metin ekleme."
)

_TAG_URETIM_PROMPT = """
Aşağıdaki firma için LinkedIn'de takip edilmesi gereken hashtag ve anahtar kelimeleri belirle:

Firma adı: {ad}

Görev: Bu firmanın kurumsal duyuruları, ürünleri, projeleri ve sektörel gelişmeleriyle
ilgili LinkedIn'de takip edilecek 15-20 hashtag/keyword üret.

Her tag için:
- tag: # ile başlayan hashtag veya arama terimi
- aciklama: Neden takip edilmeli (kısa, Türkçe)

Yanıtı SADECE şu JSON formatında ver:
{{
  "tagler": [
    {{"tag": "#Örnek", "aciklama": "..."}}
  ]
}}
"""


async def _firma_tagleri_llm_ile_uret(tenant_id: int, firma: str, ad_gorunen: str) -> list[str]:
    """Firma için LLM ile LinkedIn tag'leri üretir ve DB'ye kaydeder."""
    import json as _json
    from src.database import linkedin_tag_ekle
    from src.llm_providers import LLMFactory

    try:
        llm = await LLMFactory.for_tenant(tenant_id)
        prompt = _TAG_URETIM_PROMPT.format(ad=ad_gorunen)
        yanit = await llm.generate_text(prompt, system_prompt=_TAG_URETIM_SYSTEM)
        baslangic = yanit.find("{")
        bitis = yanit.rfind("}") + 1
        if baslangic == -1 or bitis == 0:
            return []
        veri = _json.loads(yanit[baslangic:bitis])
    except Exception as e:
        logger.error(f"LinkedIn tag üretim hatası ({firma}): {e}")
        return []

    uretilenler: list[str] = []
    for item in veri.get("tagler", []):
        tag = (item.get("tag") or "").strip()
        if not tag:
            continue
        linkedin_tag_ekle(
            tenant_id=tenant_id, tag=tag,
            aciklama=(item.get("aciklama") or "").strip(),
            kaynak="ai", secili=True, firma=firma,
        )
        uretilenler.append(tag)
    return uretilenler


async def firma_linkedin_tagleri_ve_gonderileri(tenant_id: int, firma: str, ad_gorunen: str,
                                                 gun: int = 30) -> list[dict]:
    """
    Firmanın seçili LinkedIn tag'lerini kullanır; hiç tag yoksa LLM ile üretir,
    ardından bu tag'lerle LinkedIn'de arama yapıp ham gönderi listesi döner.
    """
    import asyncio
    from src.database import linkedin_tag_listele

    tagler = [t["tag"] for t in linkedin_tag_listele(tenant_id, firma=firma) if t["secili"]]
    if not tagler:
        tagler = await _firma_tagleri_llm_ile_uret(tenant_id, firma, ad_gorunen)

    if not tagler:
        return []

    return await asyncio.to_thread(firma_linkedin_ara, ad_gorunen, tagler, gun)


# ── Üst kademe çalışan keşfi (LinkedIn profil araması) ────────────────────────

_UST_KADEME_SORGU_SABLONLARI = [
    'site:linkedin.com/in "{sirket}" Direktör',
    'site:linkedin.com/in "{sirket}" Müdür',
    'site:linkedin.com/in "{sirket}" Director',
    'site:linkedin.com/in "{sirket}" Manager',
]


def _ascii_normalle(metin: str) -> str:
    """
    Türkçe karakterleri ASCII karşılığına çevirir — LinkedIn profillerinde
    şirket adı genelde diyakritiksiz yazılır (ör. "ULAK HABERLESME"), quoted
    arama bu yüzden orijinal Türkçe yazımla eşleşmeyebilir.
    """
    cevirim = str.maketrans("şŞğĞıİöÖüÜçÇ", "sSgGiIoOuUcC")
    return metin.translate(cevirim)


def _ust_kademe_sorgulari(sirket_adi: str) -> list[str]:
    """Türkçe + ASCII normalize edilmiş şirket adıyla sorgu listesi üretir (tekilleştirilmiş)."""
    varyantlar = {sirket_adi, _ascii_normalle(sirket_adi)}
    sorgular = [
        sablon.format(sirket=varyant)
        for varyant in varyantlar
        for sablon in _UST_KADEME_SORGU_SABLONLARI
    ]
    return sorgular

_UST_KADEME_SYSTEM = (
    "Sen bir İK/kurumsal araştırma uzmanısın. LinkedIn arama sonuçlarından "
    "gerçekten belirtilen şirkette çalışan direktör/müdür seviyesindeki "
    "kişileri ayıklıyorsun. Emin olmadığın veya belirsiz sonuçları eleme "
    "yaparak dışarıda bırakıyorsun. Yanıtlarını daima geçerli JSON formatında ver."
)

_UST_KADEME_PROMPT = """
Aşağıda "{sirket}" için LinkedIn'de yapılan aramalardan ham sonuçlar var. Her sonucun
başlığı genelde "Ad Soyad - Unvan - Şirket | LinkedIn" formatındadır.

{sonuclar}

Görev: Bu sonuçlardan SADECE gerçekten "{sirket}" bünyesinde çalışan, Direktör veya
Müdür (Director/Manager) seviyesindeki kişileri çıkar. Kurallar:
- Başlık/özet şirket adını açıkça içermiyorsa veya şirketle ilişkisi belirsizse dahil etme.
- Unvanı Direktör/Müdür/Director/Manager seviyesinde olmayanları (stajyer, uzman,
  danışman vb.) dahil etme.
- Aynı kişi birden fazla sonuçta geçiyorsa yalnızca bir kez ekle.
- Emin değilsen dahil etme — yanlış kişi eklemek yanlış olmaktan iyidir.

Yanıtı SADECE şu JSON formatında ver:
{{
  "kisiler": [
    {{"ad_soyad": "...", "unvan": "...", "indeks": 0}}
  ]
}}

"indeks" alanına o kişiyi tespit ettiğin sonucun köşeli parantez içindeki numarasını yaz.
"""


def _linkedin_profil_ara(sirket_adi: str, sonuc_basi: int = 30) -> list[dict]:
    """DDG ile LinkedIn profil sonuçları arar (ham, doğrulanmamış)."""
    sonuclar: list[dict] = []
    goruldu: set[str] = set()

    try:
        with DDGS() as ddgs:
            for sorgu in _ust_kademe_sorgulari(sirket_adi):
                if len(sonuclar) >= sonuc_basi:
                    break
                time.sleep(1.5)
                try:
                    for r in ddgs.text(sorgu, max_results=8):
                        url = r.get("href", "") or r.get("url", "")
                        if not url or url in goruldu or "linkedin.com/in" not in url:
                            continue
                        goruldu.add(url)
                        sonuclar.append({
                            "baslik": r.get("title", ""),
                            "ozet": (r.get("body", "") or r.get("snippet", ""))[:300],
                            "url": url,
                        })
                        if len(sonuclar) >= sonuc_basi:
                            break
                except Exception as e:
                    logger.debug(f"Üst kademe profil arama hatası ({sorgu[:40]}): {e}")
    except Exception as e:
        logger.error(f"DuckDuckGo bağlantı hatası (üst kademe keşfi): {e}")

    logger.info(f"Üst kademe profil araması — {sirket_adi}: {len(sonuclar)} ham sonuç")
    return sonuclar


async def ust_kademe_kesif(tenant_id: int, sirket_adi: str = "Ulak Haberleşme") -> list[dict]:
    """
    LinkedIn'de "{sirket_adi}" için Direktör/Müdür unvanlı profilleri arar,
    LLM ile ham sonuçları ayıklayıp gerçek kişi listesi döner
    ({ad_soyad, unvan, linkedin_url}).
    """
    import asyncio
    import json as _json
    from src.llm_providers import LLMFactory

    ham = await asyncio.to_thread(_linkedin_profil_ara, sirket_adi)
    if not ham:
        return []

    sonuc_metni = "\n\n".join(
        f"[{i}] Başlık: {s['baslik']}\nÖzet: {s['ozet']}"
        for i, s in enumerate(ham)
    )
    prompt = _UST_KADEME_PROMPT.format(sirket=sirket_adi, sonuclar=sonuc_metni)

    try:
        llm = await LLMFactory.for_tenant(tenant_id)
        yanit = await llm.generate_text(prompt, system_prompt=_UST_KADEME_SYSTEM)
        baslangic = yanit.find("{")
        bitis = yanit.rfind("}") + 1
        if baslangic == -1 or bitis == 0:
            return []
        veri = _json.loads(yanit[baslangic:bitis])
    except Exception as e:
        logger.error(f"Üst kademe LLM doğrulama hatası: {e}")
        return []

    kisiler: list[dict] = []
    for item in veri.get("kisiler", []):
        idx = item.get("indeks")
        ad_soyad = (item.get("ad_soyad") or "").strip()
        unvan = (item.get("unvan") or "").strip()
        if not ad_soyad or not isinstance(idx, int) or not (0 <= idx < len(ham)):
            continue
        kisiler.append({
            "ad_soyad": ad_soyad,
            "unvan": unvan,
            "linkedin_url": ham[idx]["url"],
        })

    logger.info(f"Üst kademe keşfi — {sirket_adi}: {len(kisiler)} kişi doğrulandı")
    return kisiler


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

def linkedin_gonderileri_cek(gun: int = 7) -> LinkedInRaporu:
    """
    Ulak Haberleşme resmi LinkedIn sayfasından son {gun} günün gönderilerini toplar,
    Claude ile analiz eder ve en önemli 3 gönderiyi döndürür.
    """
    logger.info("LinkedIn takibi başlıyor...")
    ham: list[dict] = []

    # 1. DuckDuckGo arama
    ham += _ddg_linkedin_ara(gun)

    # 2. Doğrudan sayfa çekimi (kısmi)
    ham += _sirket_sayfasi_cek()

    if not ham:
        logger.warning("LinkedIn'den hiç içerik bulunamadı.")
        return LinkedInRaporu(ozet="Bu hafta LinkedIn'den içerik toplanamadı.")

    # URL bazlı tekilleştir
    goruldu: set[str] = set()
    tekil: list[dict] = []
    for r in ham:
        url = r.get("url", "")
        if url and url not in goruldu:
            goruldu.add(url)
            tekil.append(r)
        elif not url:
            tekil.append(r)

    logger.info(f"LinkedIn toplam tekil içerik: {len(tekil)}")
    return _gonderileri_analiz_et(tekil)
