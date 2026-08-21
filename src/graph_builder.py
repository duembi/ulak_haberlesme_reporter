"""
Varlık İlişki Ağı (Entity Knowledge Graph) modülü.
Haber triple'larından pyvis etkileşimli ağ grafiği üretir.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import NamedTuple

from loguru import logger

try:
    from pyvis.network import Network
    _PYVIS_VAR = True
except ImportError:
    _PYVIS_VAR = False

from src.news_fetcher import Haber


class TripleIstatistik(NamedTuple):
    toplam_triple: int
    benzersiz_varlik: int
    benzersiz_iliski: int
    en_sik_varliklar: list[tuple[str, int]]
    en_sik_iliskiler: list[tuple[str, int]]


def triple_istatistik(haberler: list[Haber]) -> TripleIstatistik:
    varlik_sayac: Counter = Counter()
    iliski_sayac: Counter = Counter()
    toplam = 0

    for h in haberler:
        for triple in h.triples:
            if len(triple) != 3:
                continue
            kaynak, iliski, hedef = triple
            varlik_sayac[kaynak] += 1
            varlik_sayac[hedef] += 1
            iliski_sayac[iliski] += 1
            toplam += 1

    return TripleIstatistik(
        toplam_triple=toplam,
        benzersiz_varlik=len(varlik_sayac),
        benzersiz_iliski=len(iliski_sayac),
        en_sik_varliklar=varlik_sayac.most_common(15),
        en_sik_iliskiler=iliski_sayac.most_common(10),
    )


# Düğüm renkleri — varlık türüne göre tahmini renk
_RENK_PALETTE = [
    "#1A5276", "#1F618D", "#2874A6", "#2E86C1",
    "#3498DB", "#5DADE2", "#85C1E9", "#AED6F1",
    "#154360", "#1A5276",
]

_ULAK_VARLIKLARI = {
    "ulak haberleşme", "ulak haberlesme", "ulak haberleşme a.ş", "ulak haberleşme a.ş.", "ulak",
}


def _varlik_rengi(varlik: str, varlik_indeks: dict[str, int]) -> str:
    if varlik.lower() in _ULAK_VARLIKLARI:
        return "#C0392B"  # Ulak Haberleşme düğümleri kırmızı — merkez varlık
    idx = varlik_indeks.get(varlik, 0)
    return _RENK_PALETTE[idx % len(_RENK_PALETTE)]


def ag_html_uret(
    haberler: list[Haber],
    min_kenar_agirlik: int = 1,
    yukseklik: str = "600px",
) -> str:
    """
    Haber triple'larından pyvis HTML string üretir.
    Streamlit'te st.components.v1.html() ile gömülür.
    """
    if not _PYVIS_VAR:
        return "<p>pyvis kütüphanesi yüklü değil. <code>pip install pyvis</code></p>"

    # Triple'ları topla, kenar ağırlıklarını hesapla
    kenar_sayac: Counter = Counter()
    kenar_iliski: dict[tuple[str, str], list[str]] = {}

    for h in haberler:
        for triple in h.triples:
            if len(triple) != 3:
                continue
            kaynak, iliski, hedef = [str(x).strip() for x in triple]
            if not kaynak or not hedef:
                continue
            anahtar = (kaynak, hedef)
            kenar_sayac[anahtar] += 1
            kenar_iliski.setdefault(anahtar, [])
            if iliski not in kenar_iliski[anahtar]:
                kenar_iliski[anahtar].append(iliski)

    if not kenar_sayac:
        return "<p style='color:#666;text-align:center;padding:40px'>Henüz yeterli triple verisi yok. Analiz tamamlandıktan sonra tekrar deneyin.</p>"

    # Filtrelenmiş kenarlar
    filtreli = {
        (k, h): agirlik
        for (k, h), agirlik in kenar_sayac.items()
        if agirlik >= min_kenar_agirlik
    }

    if not filtreli:
        return "<p style='color:#666;text-align:center;padding:40px'>Filtre kriterini karşılayan kenar bulunamadı. Min. kenar ağırlığını düşürün.</p>"

    # Düğüm listesi ve indeks
    tum_varliklar = sorted({v for kenar in filtreli for v in kenar})
    varlik_indeks = {v: i for i, v in enumerate(tum_varliklar)}

    # Düğüm önemi — kaç kenara bağlı
    dugum_derece: Counter = Counter()
    for (k, h) in filtreli:
        dugum_derece[k] += 1
        dugum_derece[h] += 1

    net = Network(
        height=yukseklik,
        width="100%",
        bgcolor="#F8F9FA",
        font_color="#1A1A2E",
        directed=True,
    )
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=120,
        spring_strength=0.04,
        damping=0.09,
    )

    # Düğümler
    for varlik in tum_varliklar:
        derece = dugum_derece[varlik]
        boyut = max(12, min(45, 10 + derece * 3))
        renk = _varlik_rengi(varlik, varlik_indeks)
        net.add_node(
            varlik,
            label=varlik,
            size=boyut,
            color=renk,
            font={"size": max(10, min(18, 8 + derece)), "color": "#1A1A2E"},
            title=f"<b>{varlik}</b><br>Bağlantı sayısı: {derece}",
        )

    # Kenarlar
    max_agirlik = max(filtreli.values()) if filtreli else 1
    for (kaynak, hedef), agirlik in filtreli.items():
        iliski_listesi = kenar_iliski.get((kaynak, hedef), [])
        iliski_etiketi = " / ".join(iliski_listesi[:2])
        kalinlik = max(1.0, (agirlik / max_agirlik) * 6)
        net.add_edge(
            kaynak, hedef,
            label=iliski_etiketi,
            width=kalinlik,
            title=f"{kaynak} → {hedef}<br><i>{iliski_etiketi}</i><br>Tekrar: {agirlik}",
            color={"color": "#2E86C1", "opacity": 0.7},
            font={"size": 9, "color": "#555"},
            arrows={"to": {"enabled": True, "scaleFactor": 0.6}},
        )

    html = net.generate_html()
    logger.info(
        f"Ağ grafiği oluşturuldu — {len(tum_varliklar)} düğüm, {len(filtreli)} kenar"
    )
    return html
