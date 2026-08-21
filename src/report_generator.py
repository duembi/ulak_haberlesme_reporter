from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image,
)
from reportlab.graphics.shapes import Drawing, String, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics import renderPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from loguru import logger
import re
import html

from config.settings import REPORT_OUTPUT_DIR, BASE_DIR
from src.news_fetcher import Haber
from src.competitor_tracker import RakipHaber, HisseSenedi
from src.database import sentiment_trend_al
from src.customer_voice import MusteriSesiRaporu
from src.linkedin_tracker import LinkedInRaporu, LinkedInGonderi

def _guvli_metin(metin: str) -> str:
    """Claude çıktısındaki bozuk XML etiketlerini ve özel karakterleri temizler."""
    if not metin:
        return ""
    # HTML etiketlerini sil (<b>foo</b> → foo), ardından & < > karakterlerini escape et
    temiz = re.sub(r"<[^>]+>", "", metin)
    return html.escape(temiz)


_LOGO_YOLU = None  # logo kaldırıldı

_FONT_KAYDEDILDI = False


def _font_kaydet():
    global _FONT_KAYDEDILDI
    if _FONT_KAYDEDILDI:
        return
    font_yollari = [
        ("C:/Windows/Fonts/arial.ttf",   "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),
    ]
    for normal, kalin in font_yollari:
        if Path(normal).exists():
            pdfmetrics.registerFont(TTFont("Rapor", normal))
            pdfmetrics.registerFont(TTFont("Rapor-Bold", kalin))
            _FONT_KAYDEDILDI = True
            return
    _FONT_KAYDEDILDI = True


RENK_MAVI    = colors.HexColor("#1A5276")
RENK_YESIL   = colors.HexColor("#1E8449")
RENK_KIRMIZI = colors.HexColor("#C0392B")
RENK_GRI     = colors.HexColor("#5D6D7E")
RENK_TURUNCU = colors.HexColor("#D35400")
RENK_MOR     = colors.HexColor("#7D3C98")
RENK_ACIK    = colors.HexColor("#EBF5FB")
RENK_CIZGI   = colors.HexColor("#AED6F1")

SENTIMENT_RENK = {"olumlu": RENK_YESIL, "olumsuz": RENK_KIRMIZI, "nötr": RENK_GRI}
KATEGORI_SIRA  = ["teknoloji", "finans", "şirket haberi", "politika", "uluslararası", "diğer"]
KATEGORI_RENKLER = [
    colors.HexColor("#2E86C1"),
    colors.HexColor("#1E8449"),
    colors.HexColor("#D35400"),
    colors.HexColor("#7D3C98"),
    colors.HexColor("#B7950B"),
    colors.HexColor("#5D6D7E"),
]


def _f():
    return "Rapor" if _FONT_KAYDEDILDI else "Helvetica"


def _fb():
    return "Rapor-Bold" if _FONT_KAYDEDILDI else "Helvetica-Bold"


def _stiller():
    _font_kaydet()
    return {
        "baslik1":    ParagraphStyle("b1",  fontName=_fb(), fontSize=20, textColor=RENK_MAVI,
                                     spaceAfter=6, leading=24),
        "baslik2":    ParagraphStyle("b2",  fontName=_fb(), fontSize=14, textColor=RENK_MAVI,
                                     spaceAfter=4, spaceBefore=14, leading=18),
        "baslik3":    ParagraphStyle("b3",  fontName=_fb(), fontSize=11, textColor=RENK_GRI,
                                     spaceAfter=3, spaceBefore=8, leading=14),
        "govde":      ParagraphStyle("g",   fontName=_f(),  fontSize=10, leading=15, spaceAfter=4),
        "bullet":     ParagraphStyle("bul", fontName=_f(),  fontSize=10, leading=14,
                                     leftIndent=14, spaceAfter=2, bulletIndent=4),
        "kucuk":      ParagraphStyle("k",   fontName=_f(),  fontSize=8,  textColor=RENK_GRI, leading=11),
        "kapak_ana":  ParagraphStyle("ka",  fontName=_fb(), fontSize=26, textColor=RENK_MAVI,
                                     alignment=1, leading=32),
        "kapak_alt":  ParagraphStyle("kal", fontName=_f(),  fontSize=13, alignment=1,
                                     textColor=colors.black, leading=18),
        "kapak_tarih":ParagraphStyle("kt",  fontName=_f(),  fontSize=11, alignment=1,
                                     textColor=RENK_GRI, leading=15),
        "ref_baslik": ParagraphStyle("rb",  fontName=_fb(), fontSize=9,  textColor=RENK_MAVI,
                                     spaceAfter=1, leading=12),
        "ref_link":   ParagraphStyle("rl",  fontName=_f(),  fontSize=8,  textColor=RENK_GRI,
                                     leading=11, spaceAfter=5),
        "govde_ic":   ParagraphStyle("gi",  fontName=_f(),  fontSize=10, leading=15,
                                     spaceAfter=4, leftIndent=18),
        "grafik_baslik": ParagraphStyle("gb", fontName=_fb(), fontSize=10, textColor=RENK_GRI,
                                        alignment=1, spaceAfter=2),
    }


# ── Grafik yardımcıları ──────────────────────────────────────────────────────

def _pasta_grafik(etiketler: list[str], degerler: list[int],
                  renk_listesi: list, genislik=7*cm, yukseklik=6*cm) -> Drawing:
    """Genel amaçlı pasta grafik Drawing döner."""
    d = Drawing(genislik, yukseklik)

    pie = Pie()
    pie.x = genislik * 0.18
    pie.y = yukseklik * 0.18
    pie.width  = min(genislik, yukseklik) * 0.55
    pie.height = min(genislik, yukseklik) * 0.55
    pie.data   = degerler
    pie.labels = [f"%{v/sum(degerler)*100:.0f}" if sum(degerler) else "0"
                  for v in degerler]
    pie.sideLabels    = False
    pie.simpleLabels  = True
    pie.slices.strokeWidth  = 0.5
    pie.slices.strokeColor  = colors.white
    pie.slices.labelRadius  = 0.65
    pie.slices.fontName     = _f()
    pie.slices.fontSize     = 8
    pie.slices.fontColor    = colors.white

    _renk_havuzu = (renk_listesi * ((len(degerler) // max(len(renk_listesi), 1)) + 1))
    for i in range(len(degerler)):
        pie.slices[i].fillColor = _renk_havuzu[i]

    legend = Legend()
    legend.x           = genislik * 0.68
    legend.y           = yukseklik * 0.72
    legend.dx           = 8
    legend.dy           = 8
    legend.fontName     = _f()
    legend.fontSize     = 7
    # Renk listesi yetersizse döngüsel olarak tekrarla
    _renkler = (renk_listesi * ((len(etiketler) // max(len(renk_listesi), 1)) + 1))
    legend.colorNamePairs = [(_renkler[i], f"{etiketler[i]} ({degerler[i]})")
                              for i in range(len(etiketler))]
    legend.strokeColor  = None
    legend.columnMaximum = 10

    d.add(pie)
    d.add(legend)
    return d


def _cubuk_grafik(etiketler: list[str], degerler: list[int],
                  renk_listesi: list, genislik=16*cm, yukseklik=7*cm) -> Drawing:
    """Dikey çubuk grafik Drawing döner."""
    d = Drawing(genislik, yukseklik)

    bar = VerticalBarChart()
    bar.x      = 2.5 * cm
    bar.y      = 1.2 * cm
    bar.width  = genislik - 3.5 * cm
    bar.height = yukseklik - 2 * cm
    bar.data   = [degerler]
    bar.categoryAxis.categoryNames = etiketler
    bar.categoryAxis.labels.fontName  = _f()
    bar.categoryAxis.labels.fontSize  = 8
    bar.categoryAxis.labels.angle     = 15
    bar.categoryAxis.labels.boxAnchor = "ne"
    bar.valueAxis.labels.fontName     = _f()
    bar.valueAxis.labels.fontSize     = 8
    bar.valueAxis.valueMin            = 0
    bar.valueAxis.valueStep           = max(1, max(degerler) // 5) if degerler else 1
    bar.bars[0].fillColor             = RENK_MAVI
    bar.groupSpacing                  = 10

    for i, renk in enumerate(renk_listesi[:len(degerler)]):
        bar.bars[(0, i)].fillColor = renk

    # Değer etiketleri çubukların üstüne
    for i, val in enumerate(degerler):
        if val == 0:
            continue
        bar_w  = bar.width / len(degerler)
        bar_x  = bar.x + i * bar_w + bar_w / 2
        bar_h  = bar.y + (val / (max(degerler) or 1)) * bar.height
        lbl = String(bar_x, bar_h + 3, str(val),
                     fontName=_f(), fontSize=8, fillColor=RENK_GRI,
                     textAnchor="middle")
        d.add(lbl)

    d.add(bar)
    return d


def _trend_grafigi(genislik=16*cm, yukseklik=6*cm) -> Drawing | None:
    """
    Son 8 haftanın olumlu/olumsuz/nötr haber sayılarını çizgi grafik olarak döner.
    Veritabanında yeterli veri yoksa None döner.
    """
    trend = sentiment_trend_al(hafta_sayisi=8)
    if not trend:
        return None

    # Hafta bazında grupla: {hafta: {sentiment: sayi}}
    haftalar: dict[str, dict[str, int]] = {}
    for satir in trend:
        h = satir["hafta"]
        haftalar.setdefault(h, {})
        haftalar[h][satir["sentiment"]] = satir["sayi"]

    sirali_haftalar = sorted(haftalar.keys())
    if len(sirali_haftalar) < 2:
        return None

    etiketler   = sirali_haftalar
    olumlu_data = [(i, haftalar[h].get("olumlu",  0)) for i, h in enumerate(etiketler)]
    olumsuz_data= [(i, haftalar[h].get("olumsuz", 0)) for i, h in enumerate(etiketler)]
    notr_data   = [(i, haftalar[h].get("nötr",    0)) for i, h in enumerate(etiketler)]

    d    = Drawing(genislik, yukseklik)
    plot = LinePlot()
    plot.x      = 2*cm
    plot.y      = 1.2*cm
    plot.width  = genislik - 3.2*cm
    plot.height = yukseklik - 1.8*cm

    tum_deger = [v for _, v in olumlu_data + olumsuz_data + notr_data]
    plot.yValueAxis.valueMin  = 0
    plot.yValueAxis.valueMax  = max(tum_deger, default=5) + 1
    plot.yValueAxis.valueStep = max(1, (max(tum_deger, default=5) + 1) // 5)
    plot.yValueAxis.labels.fontName = _f()
    plot.yValueAxis.labels.fontSize = 7
    plot.xValueAxis.valueMin  = 0
    plot.xValueAxis.valueMax  = len(etiketler) - 1
    plot.xValueAxis.valueStep = 1
    plot.xValueAxis.labelTextFormat = lambda v: etiketler[int(round(v))] if 0 <= int(round(v)) < len(etiketler) else ""
    plot.xValueAxis.labels.fontName = _f()
    plot.xValueAxis.labels.fontSize = 6
    plot.xValueAxis.labels.angle    = 30

    plot.data = [olumlu_data, olumsuz_data, notr_data]
    plot.lines[0].strokeColor = RENK_YESIL
    plot.lines[0].strokeWidth = 2
    plot.lines[1].strokeColor = RENK_KIRMIZI
    plot.lines[1].strokeWidth = 2
    plot.lines[2].strokeColor = RENK_GRI
    plot.lines[2].strokeWidth = 1.5

    legend = Legend()
    legend.x          = genislik - 3.5*cm
    legend.y          = yukseklik - 0.8*cm
    legend.dx, legend.dy = 10, 6
    legend.fontName   = _f()
    legend.fontSize   = 8
    legend.strokeColor= None
    legend.colorNamePairs = [
        (RENK_YESIL,   "Olumlu"),
        (RENK_KIRMIZI, "Olumsuz"),
        (RENK_GRI,     "Nötr"),
    ]

    d.add(plot)
    d.add(legend)
    return d


# ── Rapor bölümleri ──────────────────────────────────────────────────────────

def _sayfa_numarasi(canvas, doc):
    canvas.saveState()
    canvas.setFont(_f(), 8)
    canvas.setFillColor(RENK_GRI)
    canvas.drawCentredString(A4[0]/2, 1.2*cm,
                             f"Medya İstihbarat Raporu  |  Sayfa {doc.page}")
    canvas.restoreState()


_AY_TR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
}

def _tarih_tr(dt) -> str:
    return f"{dt.day} {_AY_TR[dt.month]} {dt.year}"


def _kapak(ic, s, baslangic, bitis, haber_sayisi):
    ic.append(Spacer(1, 2.5*cm))
    if False:
        pass
    else:
        ic.append(Spacer(1, 1.5*cm))
    ic.append(Paragraph("ULAK HABERLEŞME A.Ş.", s["kapak_ana"]))
    ic.append(Spacer(1, 0.5*cm))
    ic.append(Paragraph("Haftalık Medya Takip Raporu", s["kapak_alt"]))
    ic.append(Spacer(1, 1*cm))
    ic.append(HRFlowable(width="60%", thickness=1.5, color=RENK_CIZGI, hAlign="CENTER"))
    ic.append(Spacer(1, 0.8*cm))
    ic.append(Paragraph(f"{_tarih_tr(baslangic)} – {_tarih_tr(bitis)}", s["kapak_tarih"]))
    ic.append(Spacer(1, 0.3*cm))
    ic.append(Paragraph(f"Toplam {haber_sayisi} haber analiz edildi", s["kapak_tarih"]))
    ic.append(Spacer(1, 0.3*cm))
    ic.append(Paragraph(f"Üretim tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", s["kapak_tarih"]))
    ic.append(PageBreak())


def _istatistik_paneli(ic, s, haberler):
    """Sentiment tablosu + pasta grafik yan yana."""
    ic.append(Paragraph("Medya Analizi", s["baslik1"]))
    ic.append(HRFlowable(width="100%", thickness=1.5, color=RENK_MAVI))
    ic.append(Spacer(1, 0.4*cm))

    sayim   = Counter(h.sentiment for h in haberler)
    toplam  = len(haberler)
    sentimentler = ["olumlu", "olumsuz", "nötr"]
    renkler_s    = [RENK_YESIL, RENK_KIRMIZI, RENK_GRI]

    # — Sentiment tablo verisi
    tablo_veri = [["Sentiment", "Haber", "Oran"]]
    for snt in sentimentler:
        sayi = sayim.get(snt, 0)
        oran = f"%{sayi/toplam*100:.1f}" if toplam else "%-"
        tablo_veri.append([snt.capitalize(), str(sayi), oran])

    tablo = Table(tablo_veri, colWidths=[4*cm, 3*cm, 3*cm])
    tablo.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  RENK_MAVI),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  _fb()),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("FONTNAME",      (0,1), (-1,-1), _f()),
        ("ALIGN",         (1,0), (-1,-1), "CENTER"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [RENK_ACIK, colors.white]),
        ("GRID",          (0,0), (-1,-1), 0.5, RENK_CIZGI),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("TEXTCOLOR",     (0,1), (0,1),   RENK_YESIL),
        ("TEXTCOLOR",     (0,2), (0,2),   RENK_KIRMIZI),
        ("TEXTCOLOR",     (0,3), (0,3),   RENK_GRI),
    ]))

    # — Sentiment pasta grafik
    degerler_s = [sayim.get(snt, 0) for snt in sentimentler]
    if sum(degerler_s) > 0:
        pasta_s = _pasta_grafik(
            [s.capitalize() for s in sentimentler],
            degerler_s, renkler_s,
            genislik=8*cm, yukseklik=6*cm,
        )
        yan_yana = Table(
            [[tablo, pasta_s]],
            colWidths=[10*cm, 8*cm],
        )
        yan_yana.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING",  (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ]))
        ic.append(yan_yana)
    else:
        ic.append(tablo)

    ic.append(Spacer(1, 0.6*cm))

    # — Kategori çubuk grafik
    ic.append(Paragraph("Kategori Dağılımı", s["baslik2"]))
    kat_sayim = Counter(h.kategori for h in haberler)
    kat_etiket = [k.capitalize() for k in KATEGORI_SIRA if kat_sayim.get(k, 0) > 0]
    kat_deger  = [kat_sayim.get(k, 0) for k in KATEGORI_SIRA if kat_sayim.get(k, 0) > 0]
    kat_renkler = [KATEGORI_RENKLER[i] for i, k in enumerate(KATEGORI_SIRA) if kat_sayim.get(k, 0) > 0]

    if kat_deger:
        cubuk = _cubuk_grafik(kat_etiket, kat_deger, kat_renkler,
                              genislik=16*cm, yukseklik=7*cm)
        ic.append(cubuk)

    ic.append(Spacer(1, 0.6*cm))

    # — Dil ve kaynak pasta grafikleri yan yana
    dil_sayim  = Counter(h.dil for h in haberler)
    kaynak_sayim = Counter(
        "Google News" if "RSS" in h.kaynak
        else ("NewsAPI" if h.kaynak == "NewsAPI" else "Web")
        for h in haberler
    )

    dil_etiket    = list(dil_sayim.keys())
    dil_deger     = list(dil_sayim.values())
    dil_renkler   = [RENK_MAVI, RENK_TURUNCU][:len(dil_etiket)]

    kaynak_etiket  = list(kaynak_sayim.keys())
    kaynak_deger   = list(kaynak_sayim.values())
    kaynak_renkler = [RENK_MAVI, RENK_YESIL, RENK_TURUNCU][:len(kaynak_etiket)]

    if dil_deger and kaynak_deger:
        pasta_dil    = _pasta_grafik(dil_etiket, dil_deger, dil_renkler,
                                     genislik=8.5*cm, yukseklik=6*cm)
        pasta_kaynak = _pasta_grafik(kaynak_etiket, kaynak_deger, kaynak_renkler,
                                     genislik=8.5*cm, yukseklik=6*cm)

        baslik_dil    = Paragraph("Dil Dağılımı",    s["grafik_baslik"])
        baslik_kaynak = Paragraph("Kaynak Dağılımı", s["grafik_baslik"])

        iki_grafik = Table(
            [[baslik_dil, baslik_kaynak],
             [pasta_dil,  pasta_kaynak]],
            colWidths=[9*cm, 9*cm],
        )
        iki_grafik.setStyle(TableStyle([
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN",        (0,0), (-1,-1), "CENTER"),
            ("LEFTPADDING",  (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ]))
        ic.append(iki_grafik)

    ic.append(Spacer(1, 0.3*cm))

    # — Haftalık trend grafiği (DB'den)
    trend = _trend_grafigi()
    if trend:
        ic.append(Paragraph("Haftalık Sentiment Trendi (Son 8 Hafta)", s["baslik2"]))
        ic.append(trend)
        ic.append(Spacer(1, 0.3*cm))


def _kategori_bolumu(ic, s, haberler):
    ic.append(PageBreak())
    ic.append(Paragraph("Kategori Bazlı Haberler", s["baslik2"]))

    kategoriler: dict[str, list[Haber]] = {}
    for h in haberler:
        kategoriler.setdefault(h.kategori, []).append(h)

    for kat in KATEGORI_SIRA:
        grup = kategoriler.get(kat)
        if not grup:
            continue
        ic.append(Paragraph(f"{kat.capitalize()}  ({len(grup)} haber)", s["baslik3"]))
        ic.append(HRFlowable(width="100%", thickness=0.5, color=RENK_CIZGI))
        ic.append(Spacer(1, 0.15*cm))

        for h in grup:
            renk = SENTIMENT_RENK.get(h.sentiment, RENK_GRI)
            tarih_str = h.tarih.strftime("%d.%m.%Y") if h.tarih else ""
            baslik_html = (
                f'<b>{h.baslik}</b>  '
                f'<font color="#{renk.hexval()[2:]}">[{h.sentiment}]</font>  '
                f'<font color="#5D6D7E" size="8">{tarih_str}</font>'
            )
            ic.append(Paragraph(f"• {baslik_html}", s["bullet"]))
            ic.append(Paragraph(_guvli_metin(h.ai_ozet), s["govde_ic"]))
        ic.append(Spacer(1, 0.3*cm))


def _hisse_cizgi_grafik(hisse_listesi: list[HisseSenedi],
                         genislik=16*cm, yukseklik=6*cm) -> Drawing:
    """
    Her hisse için son 10 günlük fiyat değişimini normalize ederek (%) çizgi grafik döner.
    Farklı para birimleri (EUR, TRY) aynı eksende karşılaştırılabilir hale gelir.
    """
    d = Drawing(genislik, yukseklik)

    plot = LinePlot()
    plot.x      = 2*cm
    plot.y      = 1*cm
    plot.width  = genislik - 3*cm
    plot.height = yukseklik - 1.5*cm

    renk_paleti = [RENK_MAVI, RENK_YESIL, RENK_KIRMIZI,
                   RENK_TURUNCU, RENK_MOR, RENK_GRI]

    plot.data = []
    gecerli_hisseler = []
    tum_degisimler = []

    for hisse in hisse_listesi:
        if not hisse.haftalik_fiyatlar:
            continue
        fiyatlar = [f for _, f in hisse.haftalik_fiyatlar]
        baz = fiyatlar[0]
        if baz == 0:
            continue
        # Baz günden yüzde değişim olarak normalize et
        normalize = [(i, (f - baz) / baz * 100) for i, f in enumerate(fiyatlar)]
        plot.data.append(normalize)
        gecerli_hisseler.append(hisse)
        tum_degisimler.extend([v for _, v in normalize])

    if not tum_degisimler:
        return d

    # Sıfır çizgisi ekle
    d.add(Line(2*cm, 1*cm + (yukseklik - 1.5*cm) * (abs(min(tum_degisimler, default=0)) /
                              max(max(tum_degisimler, default=1) - min(tum_degisimler, default=0), 1)),
               genislik - 1*cm, 1*cm + (yukseklik - 1.5*cm) * (abs(min(tum_degisimler, default=0)) /
                              max(max(tum_degisimler, default=1) - min(tum_degisimler, default=0), 1)),
               strokeColor=RENK_GRI, strokeWidth=0.5, strokeDashArray=[2, 2]))

    spread = max(abs(min(tum_degisimler)), abs(max(tum_degisimler))) * 1.2 or 5
    plot.yValueAxis.valueMin  = -spread
    plot.yValueAxis.valueMax  =  spread
    plot.yValueAxis.valueStep = max(1, int(spread / 3))
    plot.yValueAxis.labelTextFormat = "%+.1f%%"
    plot.yValueAxis.labels.fontName = _f()
    plot.yValueAxis.labels.fontSize = 7
    plot.xValueAxis.valueMin  = 0
    plot.xValueAxis.valueMax  = 9
    plot.xValueAxis.valueStep = 1
    plot.xValueAxis.labels.fontName = _f()
    plot.xValueAxis.labels.fontSize = 7

    for i, (hisse, renk) in enumerate(zip(gecerli_hisseler, renk_paleti)):
        plot.lines[i].strokeColor = renk
        plot.lines[i].strokeWidth = 1.5

    legend = Legend()
    legend.x          = genislik - 4*cm
    legend.y          = yukseklik - 0.8*cm
    legend.dx          = 10
    legend.dy          = 6
    legend.fontName    = _f()
    legend.fontSize    = 7
    legend.strokeColor = None
    legend.colorNamePairs = [
        (renk_paleti[i], f"{h.firma_adi} ({h.ticker})")
        for i, h in enumerate(gecerli_hisseler)
    ]
    d.add(plot)
    d.add(legend)
    return d


def _rakip_bolumu(ic, s,
                  rakip_haberler: dict[str, list[RakipHaber]],
                  hisse_listesi: list[HisseSenedi]):
    ic.append(PageBreak())
    ic.append(Paragraph("Rakip Firma Analizi", s["baslik1"]))
    ic.append(HRFlowable(width="100%", thickness=1.5, color=RENK_MAVI))
    ic.append(Spacer(1, 0.4*cm))

    # — Borsa performans tablosu
    if hisse_listesi:
        ic.append(Paragraph("Borsa Performansı", s["baslik2"]))

        tablo_veri = [["Firma", "Ticker", "Fiyat", "Haftalık", "Aylık", "Piy. Değeri"]]
        for h in hisse_listesi:
            hd = f"%{h.haftalik_degisim:+.1f}"
            ad = f"%{h.aylik_degisim:+.1f}"
            tablo_veri.append([
                h.firma_adi,
                h.ticker,
                f"{h.guncel_fiyat:.2f} {h.para_birimi}",
                hd,
                ad,
                h.piyasa_degeri,
            ])

        col_w = [4*cm, 2.5*cm, 3.5*cm, 2.2*cm, 2.2*cm, 2.6*cm]
        tablo = Table(tablo_veri, colWidths=col_w)

        stil_cmds = [
            ("BACKGROUND",    (0,0), (-1,0),  RENK_MAVI),
            ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
            ("FONTNAME",      (0,0), (-1,0),  _fb()),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("FONTNAME",      (0,1), (-1,-1), _f()),
            ("ALIGN",         (2,0), (-1,-1), "CENTER"),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [RENK_ACIK, colors.white]),
            ("GRID",          (0,0), (-1,-1), 0.5, RENK_CIZGI),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]
        # Haftalık değişim renklendirme
        for i, h in enumerate(hisse_listesi, 1):
            renk = RENK_YESIL if h.haftalik_degisim >= 0 else RENK_KIRMIZI
            stil_cmds.append(("TEXTCOLOR", (3, i), (3, i), renk))
            renk2 = RENK_YESIL if h.aylik_degisim >= 0 else RENK_KIRMIZI
            stil_cmds.append(("TEXTCOLOR", (4, i), (4, i), renk2))

        tablo.setStyle(TableStyle(stil_cmds))
        ic.append(tablo)
        ic.append(Spacer(1, 0.4*cm))

        # Fiyat hareketi açıklamaları
        aciklamali = [h for h in hisse_listesi if h.hareket_aciklamasi]
        if aciklamali:
            ic.append(Paragraph("Fiyat Hareketi Analizi", s["baslik2"]))
            for h in aciklamali:
                yon_renk = "#1E8449" if h.haftalik_degisim >= 0 else "#C0392B"
                ic.append(Paragraph(
                    f'<b>{h.firma_adi}</b>  '
                    f'<font color="{yon_renk}">%{h.haftalik_degisim:+.1f} (haftalık)</font>',
                    s["baslik3"],
                ))
                ic.append(Paragraph(_guvli_metin(h.hareket_aciklamasi), s["govde_ic"]))
            ic.append(Spacer(1, 0.3*cm))

        # Çizgi grafik
        if len(hisse_listesi) > 0:
            ic.append(Paragraph("Son 10 Gün Fiyat Performansı", s["baslik2"]))
            grafik = _hisse_cizgi_grafik(hisse_listesi)
            ic.append(grafik)
            ic.append(Spacer(1, 0.4*cm))

    # — Rakip firma haberleri
    ic.append(Paragraph("Rakip Firma Haberleri", s["baslik2"]))
    ic.append(Spacer(1, 0.2*cm))

    for firma_adi, haberler in rakip_haberler.items():
        if not haberler:
            continue

        ic.append(Paragraph(f'<b>{firma_adi}</b>', s["baslik3"]))
        ic.append(HRFlowable(width="100%", thickness=0.5, color=RENK_CIZGI))
        ic.append(Spacer(1, 0.1*cm))

        for h in haberler:
            tarih_str = h.tarih.strftime("%d.%m.%Y") if h.tarih else ""
            ic.append(Paragraph(
                f'• <b>{h.baslik}</b>  '
                f'<font color="#5D6D7E" size="8">{h.kaynak} | {tarih_str}</font>',
                s["bullet"],
            ))
        ic.append(Spacer(1, 0.3*cm))


def _musteri_sesi_bolumu(ic, s, musteri_raporu: MusteriSesiRaporu):
    ic.append(PageBreak())
    ic.append(Paragraph("Müşteri Sesi Analizi", s["baslik1"]))
    ic.append(HRFlowable(width="100%", thickness=1.5, color=RENK_MAVI))
    ic.append(Spacer(1, 0.4*cm))

    yorumlar = musteri_raporu.yorumlar
    if not yorumlar:
        ic.append(Paragraph("Bu dönemde müşteri yorumu bulunamadı.", s["govde"]))
        return

    # — Özet metin
    if musteri_raporu.tema_ozeti:
        ic.append(Paragraph(_guvli_metin(musteri_raporu.tema_ozeti), s["govde"]))
        ic.append(Spacer(1, 0.4*cm))

    # — Genel istatistik tablo + tip dağılımı pasta grafik yan yana
    tip_sayim  = Counter(y.tip for y in yorumlar if y.tip)
    platform_sayim = Counter(y.platform for y in yorumlar)
    toplam = len(yorumlar)

    tablo_veri = [["Tip", "Yorum", "Oran"]]
    tip_sira = ["sikayet", "tesekkur", "oneri", "notr"]
    tip_renk = [RENK_KIRMIZI, RENK_YESIL, RENK_MAVI, RENK_GRI]
    tip_etiket_map = {"sikayet": "Şikayet", "tesekkur": "Teşekkür",
                      "oneri": "Öneri", "notr": "Nötr"}
    for tip in tip_sira:
        sayi = tip_sayim.get(tip, 0)
        if sayi == 0:
            continue
        oran = f"%{sayi/toplam*100:.1f}" if toplam else "%-"
        tablo_veri.append([tip_etiket_map.get(tip, tip), str(sayi), oran])

    tablo = Table(tablo_veri, colWidths=[4*cm, 3*cm, 3*cm])
    tablo.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  RENK_MAVI),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  _fb()),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("FONTNAME",      (0,1), (-1,-1), _f()),
        ("ALIGN",         (1,0), (-1,-1), "CENTER"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [RENK_ACIK, colors.white]),
        ("GRID",          (0,0), (-1,-1), 0.5, RENK_CIZGI),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))

    tip_degerler = [tip_sayim.get(t, 0) for t in tip_sira if tip_sayim.get(t, 0) > 0]
    tip_etiketler = [tip_etiket_map.get(t, t) for t in tip_sira if tip_sayim.get(t, 0) > 0]
    tip_renk_filtre = [tip_renk[i] for i, t in enumerate(tip_sira) if tip_sayim.get(t, 0) > 0]

    if sum(tip_degerler) > 0:
        pasta = _pasta_grafik(tip_etiketler, tip_degerler, tip_renk_filtre,
                              genislik=8*cm, yukseklik=6*cm)
        yan_yana = Table([[tablo, pasta]], colWidths=[10*cm, 8*cm])
        yan_yana.setStyle(TableStyle([
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING",  (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ]))
        ic.append(yan_yana)
    else:
        ic.append(tablo)

    ic.append(Spacer(1, 0.5*cm))

    # — Platform dağılımı
    if platform_sayim:
        ic.append(Paragraph("Platform Dağılımı", s["baslik2"]))
        plat_etiket = list(platform_sayim.keys())
        plat_deger  = list(platform_sayim.values())
        plat_renk   = [RENK_MAVI, RENK_YESIL, RENK_TURUNCU, RENK_MOR, RENK_GRI][:len(plat_etiket)]
        if sum(plat_deger) > 0:
            plat_pasta = _pasta_grafik(plat_etiket, plat_deger, plat_renk,
                                       genislik=12*cm, yukseklik=6*cm)
            ic.append(plat_pasta)
        ic.append(Spacer(1, 0.4*cm))

    # — En sık şikayet / teşekkür temaları
    if musteri_raporu.en_sik_sikayet or musteri_raporu.en_sik_tesekkur:
        tema_veri = [["En Sık Şikayet Temaları", "En Sık Teşekkür Temaları"]]
        sikayet_col = "\n".join(f"• {t}" for t in musteri_raporu.en_sik_sikayet) or "—"
        tesekkur_col = "\n".join(f"• {t}" for t in musteri_raporu.en_sik_tesekkur) or "—"
        tema_veri.append([sikayet_col, tesekkur_col])

        tema_tablo = Table(tema_veri, colWidths=[8.5*cm, 8.5*cm])
        tema_tablo.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  RENK_MAVI),
            ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
            ("FONTNAME",      (0,0), (-1,0),  _fb()),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("FONTNAME",      (0,1), (-1,-1), _f()),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("GRID",          (0,0), (-1,-1), 0.5, RENK_CIZGI),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("BACKGROUND",    (0,1), (0,1),   colors.HexColor("#FDEDEC")),
            ("BACKGROUND",    (1,1), (1,1),   colors.HexColor("#EAFAF1")),
        ]))
        ic.append(tema_tablo)
        ic.append(Spacer(1, 0.5*cm))

    # — Tüm yorumlar içerikleriyle listelenir (tip'e göre gruplandırılmış)
    tip_sira_goster = ["sikayet", "oneri", "notr", "tesekkur"]
    tip_baslik_map  = {
        "sikayet":  "Şikayetler",
        "tesekkur": "Teşekkür ve Olumlu Görüşler",
        "oneri":    "Öneriler",
        "notr":     "Genel Yorumlar",
    }
    tip_renk_hex = {
        "sikayet":  "#C0392B",
        "tesekkur": "#1E8449",
        "oneri":    "#1A5276",
        "notr":     "#5D6D7E",
    }

    for tip in tip_sira_goster:
        grup = [y for y in yorumlar if y.tip == tip]
        if not grup:
            continue
        ic.append(Paragraph(
            f'{tip_baslik_map.get(tip, tip.capitalize())} ({len(grup)})',
            s["baslik2"],
        ))
        ic.append(HRFlowable(width="100%", thickness=0.5, color=RENK_CIZGI))
        ic.append(Spacer(1, 0.15*cm))
        renk_hex = tip_renk_hex.get(tip, "#5D6D7E")

        for y in grup:
            tarih_str = y.tarih.strftime("%d.%m.%Y") if y.tarih else ""
            tema_str  = f" — {y.tema}" if y.tema else ""
            ic.append(Paragraph(
                f'<font color="{renk_hex}">■</font>  '
                f'<b>{_guvli_metin(y.baslik)}</b>  '
                f'<font color="#5D6D7E" size="8">{y.platform}{tema_str}  {tarih_str}</font>',
                s["bullet"],
            ))
            if y.icerik and y.icerik.strip() != y.baslik.strip():
                ozet = y.icerik[:400]
                ic.append(Paragraph(
                    f'{_guvli_metin(ozet)}{"…" if len(y.icerik) > 400 else ""}',
                    s["govde_ic"],
                ))
        ic.append(Spacer(1, 0.3*cm))

    # — Tip'i belirlenememiş yorumlar (fallback — tip boş)
    belirsiz = [y for y in yorumlar if not y.tip]
    if belirsiz:
        ic.append(Paragraph(f"Diğer Yorumlar ({len(belirsiz)})", s["baslik2"]))
        ic.append(HRFlowable(width="100%", thickness=0.5, color=RENK_CIZGI))
        ic.append(Spacer(1, 0.15*cm))
        for y in belirsiz:
            tarih_str = y.tarih.strftime("%d.%m.%Y") if y.tarih else ""
            ic.append(Paragraph(
                f'<b>{_guvli_metin(y.baslik)}</b>  '
                f'<font color="#5D6D7E" size="8">{y.platform}  {tarih_str}</font>',
                s["bullet"],
            ))
            if y.icerik and y.icerik.strip() != y.baslik.strip():
                ic.append(Paragraph(
                    f'{_guvli_metin(y.icerik[:400])}',
                    s["govde_ic"],
                ))
        ic.append(Spacer(1, 0.3*cm))


def _linkedin_bolumu(ic, s, linkedin_raporu: LinkedInRaporu):
    ic.append(PageBreak())
    ic.append(Paragraph("LinkedIn Şirket Sayfası", s["baslik1"]))
    ic.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0A66C2")))
    ic.append(Spacer(1, 0.4*cm))

    # LinkedIn logosu / renk bandı
    ic.append(Paragraph(
        '<font color="#0A66C2"><b>linkedin.com/company/ulakhaberlesme</b></font>  '
        '<font color="#5D6D7E" size="9">— Son 7 Günün Öne Çıkan Gönderileri</font>',
        s["govde"],
    ))
    ic.append(Spacer(1, 0.3*cm))

    if linkedin_raporu.ozet:
        ic.append(Paragraph(_guvli_metin(linkedin_raporu.ozet), s["govde"]))
        ic.append(Spacer(1, 0.4*cm))

    gonderiler = linkedin_raporu.gonderiler
    if not gonderiler:
        ic.append(Paragraph(
            "Bu hafta LinkedIn'den gönderi içeriği toplanamadı. "
            "Gerçek zamanlı etkileşim verileri için LinkedIn API Partnership gerekmektedir.",
            s["govde"],
        ))
        return

    # Her gönderi için kart
    ic.append(Paragraph(
        f"En Önemli {min(3, len(gonderiler))} Gönderi",
        s["baslik2"],
    ))
    ic.append(Spacer(1, 0.2*cm))

    onem_renk = {
        range(9, 11): colors.HexColor("#1E8449"),
        range(7, 9):  colors.HexColor("#2E86C1"),
        range(4, 7):  colors.HexColor("#D35400"),
    }

    def _onem_rengi(skor: int):
        for aralik, renk in onem_renk.items():
            if skor in aralik:
                return renk
        return RENK_GRI

    for i, g in enumerate(gonderiler[:3], 1):
        renk = _onem_rengi(g.etkilesim_tahmini)
        renk_hex = f"#{renk.hexval()[2:]}"

        # Başlık satırı
        ic.append(Paragraph(
            f'<b>#{i}</b>  '
            f'<font color="{renk_hex}">[Önem: {g.etkilesim_tahmini}/10]</font>  '
            f'<font color="#5D6D7E" size="8">{g.yazar}</font>',
            s["baslik3"],
        ))

        # Gönderi içeriği kutusu
        icerik_metni = g.icerik[:400] + ("…" if len(g.icerik) > 400 else "")
        ic.append(Paragraph(_guvli_metin(icerik_metni or g.baslik), s["govde_ic"]))

        # Gerekçe
        if g.etkilesim_aciklama:
            ic.append(Paragraph(
                f'<i>Neden önemli: {g.etkilesim_aciklama}</i>',
                s["kucuk"],
            ))

        # Link
        if g.url:
            ic.append(Paragraph(
                f'<font color="#0A66C2">{g.url[:80]}</font>',
                s["kucuk"],
            ))

        ic.append(HRFlowable(width="100%", thickness=0.5, color=RENK_CIZGI))
        ic.append(Spacer(1, 0.3*cm))

    # Not
    ic.append(Paragraph(
        "Not: Etkileşim sayıları (beğeni/yorum) LinkedIn API Partnership gerektirdiğinden "
        "gösterilmemektedir. Önem skorları Claude tarafından içerik analizi ile belirlenmiştir.",
        s["kucuk"],
    ))


def _referanslar(ic, s, haberler):
    ic.append(PageBreak())
    ic.append(Paragraph("Referanslar", s["baslik2"]))
    ic.append(HRFlowable(width="100%", thickness=1, color=RENK_CIZGI))
    ic.append(Spacer(1, 0.3*cm))

    for i, h in enumerate(haberler, 1):
        tarih_str = h.tarih.strftime("%d.%m.%Y") if h.tarih else "tarih bilinmiyor"
        ic.append(Paragraph(f"[{i}] {h.baslik}", s["ref_baslik"]))
        ic.append(Paragraph(f"{h.kaynak}  |  {tarih_str}  |  {h.url}", s["ref_link"]))


# ── Ana fonksiyon ────────────────────────────────────────────────────────────

def rapor_olustur(haberler: list[Haber], yonetici_ozeti: str,
                  rakip_haberler: dict | None = None,
                  hisse_listesi: list | None = None,
                  musteri_raporu: MusteriSesiRaporu | None = None,
                  linkedin_raporu: LinkedInRaporu | None = None) -> Path:
    bitis     = datetime.now()
    baslangic = bitis - timedelta(days=7)

    dosya_adi = f"Ulak_Haberlesme_Rapor_{bitis.strftime('%Y_%m_%d')}.pdf"
    cikti_yolu = REPORT_OUTPUT_DIR / dosya_adi

    doc = SimpleDocTemplate(
        str(cikti_yolu),
        pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        title=f"Ulak Haberleşme Haftalık Rapor {bitis.strftime('%d.%m.%Y')}",
        author="Ulak Haberleşme Medya Takip Sistemi",
    )

    s  = _stiller()
    ic = []

    _kapak(ic, s, baslangic, bitis, len(haberler))

    # Yönetici özeti
    ic.append(Paragraph("Yönetici Özeti", s["baslik1"]))
    ic.append(HRFlowable(width="100%", thickness=1.5, color=RENK_MAVI))
    ic.append(Spacer(1, 0.3*cm))
    for paragraf in yonetici_ozeti.split("\n"):
        if paragraf.strip():
            ic.append(Paragraph(_guvli_metin(paragraf.strip()), s["govde"]))
    ic.append(Spacer(1, 0.5*cm))

    # Grafikler + istatistikler
    _istatistik_paneli(ic, s, haberler)

    # Haber detayları
    _kategori_bolumu(ic, s, haberler)

    # Rakip firma analizi
    if rakip_haberler is not None or hisse_listesi:
        _rakip_bolumu(ic, s, rakip_haberler or {}, hisse_listesi or [])

    # Müşteri sesi analizi
    if musteri_raporu is not None:
        _musteri_sesi_bolumu(ic, s, musteri_raporu)

    # LinkedIn şirket sayfası
    if linkedin_raporu is not None:
        _linkedin_bolumu(ic, s, linkedin_raporu)

    # Kaynaklar
    _referanslar(ic, s, haberler)

    doc.build(ic, onFirstPage=_sayfa_numarasi, onLaterPages=_sayfa_numarasi)
    logger.info(f"PDF rapor kaydedildi: {cikti_yolu}")
    return cikti_yolu
