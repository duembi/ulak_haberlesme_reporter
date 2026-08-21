"""
Haber kümeleme modülü.
sentence-transformers ile embedding üretir, cosine similarity ile
benzer haberleri gruplar. Her kümeden en iyi temsilci haberi seçer.
"""
from __future__ import annotations
from loguru import logger
from src.news_fetcher import Haber

# Model ilk çalıştırmada indirilir (~90MB), sonraki çalışmalarda cache'den gelir
_MODEL_ADI  = "paraphrase-multilingual-MiniLM-L12-v2"
_ESIK       = 0.82   # Bu değerin üzerindeki benzerlik → aynı küme
_model      = None


def _model_yukle():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Embedding modeli yükleniyor: {_MODEL_ADI}")
        _model = SentenceTransformer(_MODEL_ADI)
    return _model


def _embeddingleri_hesapla(haberler: list[Haber]) -> list:
    model  = _model_yukle()
    metinler = [f"{h.baslik} {h.ozet[:200]}" for h in haberler]
    return model.encode(metinler, show_progress_bar=False, batch_size=32)


def _kumelere_ata(embeddingler, esik: float) -> list[int]:
    """
    Greedy kümeleme: her haber sırayla işlenir.
    Mevcut bir kümenin merkeziyle benzerliği eşiği aşarsa o kümeye atanır,
    aksi halde yeni küme açılır.
    """
    import numpy as np

    n        = len(embeddingler)
    kumeler  = [-1] * n
    merkezler: list[list] = []

    for i in range(n):
        en_iyi_kume  = -1
        en_iyi_skor  = esik

        for ki, merkez in enumerate(merkezler):
            # Cosine similarity
            a = np.array(embeddingler[i])
            b = np.array(merkez)
            skor = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
            if skor > en_iyi_skor:
                en_iyi_skor = skor
                en_iyi_kume = ki

        if en_iyi_kume == -1:
            kumeler[i] = len(merkezler)
            merkezler.append(list(embeddingler[i]))
        else:
            kumeler[i] = en_iyi_kume
            # Merkezi güncelle (hareketli ortalama)
            alfa = 0.3
            merkezler[en_iyi_kume] = [
                alfa * embeddingler[i][j] + (1 - alfa) * merkezler[en_iyi_kume][j]
                for j in range(len(embeddingler[i]))
            ]

    return kumeler


def _temsilci_sec(grup: list[Haber]) -> Haber:
    """
    Kümeden en iyi temsilciyi seçer:
    önce AA kaynağı, sonra ilk haber.
    """
    for kaynak_oncelik in ["Anadolu Ajansı"]:
        for h in grup:
            if h.kaynak == kaynak_oncelik:
                return h
    # En yeni haberi seç
    with_date = [h for h in grup if h.tarih]
    if with_date:
        return max(with_date, key=lambda h: h.tarih)
    return grup[0]


def haberleri_kumele(haberler: list[Haber], esik: float = _ESIK) -> list[Haber]:
    """
    Haberleri kümeler ve her kümeden bir temsilci döner.
    Küme büyüklüğü bilgisi temsilci haberin `ozet` alanına ek not olarak eklenir.
    """
    if len(haberler) < 2:
        return haberler

    try:
        embeddingler = _embeddingleri_hesapla(haberler)
        kume_id      = _kumelere_ata(embeddingler, esik)
    except Exception as e:
        logger.error(f"Kümeleme hatası: {e} — orijinal haberler kullanılıyor")
        return haberler

    # Kümeleri grupla
    gruplar: dict[int, list[Haber]] = {}
    for haber, kid in zip(haberler, kume_id):
        gruplar.setdefault(kid, []).append(haber)

    temsilciler: list[Haber] = []
    for kid, grup in sorted(gruplar.items()):
        temsilci = _temsilci_sec(grup)
        if len(grup) > 1:
            temsilci.ozet = (
                f"[{len(grup)} benzer haber birleştirildi] {temsilci.ozet}"
            )
        temsilciler.append(temsilci)

    onceki = len(haberler)
    sonraki = len(temsilciler)
    logger.info(f"Kümeleme: {onceki} haber → {sonraki} küme ({onceki - sonraki} tekrar elendi)")
    return temsilciler
