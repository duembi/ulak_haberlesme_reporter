"""
Firma bazlı haber/gönderi relevans doğrulama.

RSS/arama sonuçları yalnızca sorgu terimiyle eşleştiği için gerçekten ilgili
olmayabilir (aynı kısaltmayı/kelimeyi kullanan başka bir firma, kişi ya da genel
bir kavramdan bahsediyor olabilir). İki aşamalı filtre uygular:
  1. Ucuz anahtar kelime ön filtresi — firma adı başlık/özette hiç geçmiyorsa
     LLM'e gönderilmeden direkt elenir.
  2. LLM doğrulama — anahtar kelimeden geçenler toplu halde LLM'e gönderilip
     gerçekten o firmayla ilgili mi diye teyit edilir.
"""
import json
from loguru import logger

from src.ai_client import sorgula

_DOGRULAMA_PROMPT = """\
Aşağıdaki {sayi} içeriğin gerçekten "{firma}" adlı firma/kurumla ilgili olup olmadığını değerlendir.
Başlık veya özette firmanın adına benzer bir kelime geçmesi yeterli değil — içerik gerçekten bu
firma hakkında olmalı. Aynı kısaltmayı/kelimeyi kullanan farklı bir firma, kişi ya da genel bir
kavramdan bahsediyorsa alakasız say.

{icerikler}

Her içerik için "ilgili" alanına 1 (gerçekten ilgili) veya 0 (alakasız) yaz. SADECE şu JSON
formatında yanıt ver, başka hiçbir şey ekleme:
{{"sonuclar": [{{"indeks": 0, "ilgili": 1}}]}}
"""

_MIN_KELIME_UZUNLUK = 4


def _anahtar_kelime_gecer(ad_gorunen: str, baslik: str, ozet: str) -> bool:
    kelimeler = [k for k in ad_gorunen.lower().split() if len(k) >= _MIN_KELIME_UZUNLUK]
    if not kelimeler:
        kelimeler = [ad_gorunen.lower()]
    metin = f"{baslik} {ozet or ''}".lower()
    return any(k in metin for k in kelimeler)


def _llm_ile_dogrula(ad_gorunen: str, ogeler: list[tuple[str, str]]) -> list[bool]:
    if not ogeler:
        return []
    icerik_metni = "\n\n".join(
        f"[{i}] Başlık: {b}\nÖzet: {(o or '')[:200]}"
        for i, (b, o) in enumerate(ogeler)
    )
    prompt = _DOGRULAMA_PROMPT.format(sayi=len(ogeler), firma=ad_gorunen, icerikler=icerik_metni)
    try:
        yanit = sorgula(prompt)
        baslangic = yanit.find("{")
        bitis = yanit.rfind("}") + 1
        if baslangic == -1 or bitis == 0:
            raise ValueError("JSON bulunamadı")
        veri = json.loads(yanit[baslangic:bitis])
        sonuc_map = {item.get("indeks"): bool(item.get("ilgili")) for item in veri.get("sonuclar", [])}
        return [sonuc_map.get(i, True) for i in range(len(ogeler))]
    except Exception as e:
        logger.warning(f"LLM relevans doğrulama hatası ({ad_gorunen}): {e} — bu aşama atlanıyor")
        return [True] * len(ogeler)


def relevans_maskesi(ad_gorunen: str, ogeler: list[tuple[str, str]]) -> list[bool]:
    """
    Her (başlık, özet) çifti için ad_gorunen firmasıyla gerçekten ilgili mi diye
    iki aşamalı (anahtar kelime + LLM) True/False maskesi döner.
    """
    if not ogeler:
        return []

    anahtar_maske = [_anahtar_kelime_gecer(ad_gorunen, b, o) for b, o in ogeler]
    if not any(anahtar_maske):
        logger.info(f"Relevans filtresi — {ad_gorunen}: hiçbir öğe anahtar kelime içermiyor, hepsi elendi")
        return [False] * len(ogeler)

    llm_girdi = [(b, o) for (b, o), gecti in zip(ogeler, anahtar_maske) if gecti]
    llm_sonuc = iter(_llm_ile_dogrula(ad_gorunen, llm_girdi))

    sonuc: list[bool] = []
    for gecti in anahtar_maske:
        sonuc.append(next(llm_sonuc) if gecti else False)
    return sonuc
