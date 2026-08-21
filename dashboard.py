"""
Ulak Haberleşme Medya Takip — Streamlit Dashboard
Çalıştırma: streamlit run dashboard.py
"""
import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from datetime import datetime, timedelta
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS

# Proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).parent))
from config.settings import BASE_DIR, REPORT_OUTPUT_DIR
from src.database import DB_PATH, sentiment_trend_al

# ── Sayfa ayarları ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ulak Haberleşme Medya Takip",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Stiller ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 28px; font-weight: bold;
        color: #1A5276; border-bottom: 3px solid #AED6F1;
        padding-bottom: 10px; margin-bottom: 20px;
    }
    .metric-card {
        background: #EBF5FB; border-radius: 8px;
        padding: 16px; text-align: center;
    }
    .sentiment-olumlu { color: #1E8449; font-weight: bold; }
    .sentiment-olumsuz { color: #C0392B; font-weight: bold; }
    .sentiment-notr    { color: #5D6D7E; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ── Veri yükleme ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def haberleri_yukle(gun: int = 30) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    esik = (datetime.now() - timedelta(days=gun)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM news WHERE tarih >= ? ORDER BY tarih DESC",
            conn, params=(esik,)
        )
    if not df.empty and "tarih" in df.columns:
        df["tarih"] = pd.to_datetime(df["tarih"], errors="coerce")
        df["hafta"] = df["tarih"].dt.strftime("%Y-W%V")
    return df


@st.cache_data(ttl=300)
def raporlari_yukle() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "SELECT * FROM reports ORDER BY olusturuldu_at DESC",
            conn
        )


@st.cache_data(ttl=300)
def trend_yukle(hafta: int = 8) -> list[dict]:
    return sentiment_trend_al(hafta_sayisi=hafta)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Medya İstihbarat")
    st.divider()

    gun_filtre = st.slider("Gösterilecek gün aralığı", 7, 90, 30)
    st.divider()

    sayfa = st.radio("Sayfa", [
        "📊 Genel Bakış",
        "📰 Haberler",
        "📈 Trend Analizi",
        "🤖 Ajan Kararları",
        "💬 Müşteri Sesi",
        "💼 LinkedIn",
        "☁️ Kelime Bulutu",
        "🕸️ İlişki Ağı",
        "📁 Raporlar",
    ])

df = haberleri_yukle(gun_filtre)

# ── SAYFA: Genel Bakış ───────────────────────────────────────────────────────
if sayfa == "📊 Genel Bakış":
    st.markdown('<div class="main-header">📡 Ulak Haberleşme Medya Takip Sistemi</div>',
                unsafe_allow_html=True)

    if df.empty:
        st.warning("Veritabanında henüz haber yok. `python main.py` çalıştırın.")
        st.stop()

    # Üst metrik kartları
    toplam   = len(df)
    olumlu   = len(df[df.sentiment == "olumlu"])
    olumsuz  = len(df[df.sentiment == "olumsuz"])
    notr     = len(df[df.sentiment == "nötr"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Haber",  toplam)
    c2.metric("Olumlu",  olumlu,  f"%{olumlu/toplam*100:.0f}" if toplam else "")
    c3.metric("Olumsuz", olumsuz, f"%{olumsuz/toplam*100:.0f}" if toplam else "")
    c4.metric("Nötr",    notr,    f"%{notr/toplam*100:.0f}" if toplam else "")

    st.divider()

    col1, col2 = st.columns(2)

    # Sentiment pasta grafik
    with col1:
        st.subheader("Sentiment Dağılımı")
        sayim = df["sentiment"].value_counts().reset_index()
        sayim.columns = ["sentiment", "sayi"]
        renk_map = {"olumlu": "#1E8449", "olumsuz": "#C0392B", "nötr": "#5D6D7E"}
        fig = px.pie(sayim, names="sentiment", values="sayi",
                     color="sentiment", color_discrete_map=renk_map,
                     hole=0.4)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # Kategori çubuk grafik
    with col2:
        st.subheader("Kategori Dağılımı")
        kat = df["kategori"].value_counts().reset_index()
        kat.columns = ["kategori", "sayi"]
        fig2 = px.bar(kat, x="kategori", y="sayi",
                      color="sayi", color_continuous_scale="Blues",
                      text="sayi")
        fig2.update_traces(textposition="outside")
        fig2.update_layout(showlegend=False, coloraxis_showscale=False,
                           margin=dict(t=10, b=10), xaxis_title="", yaxis_title="")
        st.plotly_chart(fig2, use_container_width=True)

    # Kaynak dağılımı
    st.subheader("Kaynak Dağılımı")
    kaynak = df["kaynak"].value_counts().reset_index()
    kaynak.columns = ["kaynak", "sayi"]
    fig3 = px.bar(kaynak, x="sayi", y="kaynak", orientation="h",
                  color="sayi", color_continuous_scale="Teal", text="sayi")
    fig3.update_traces(textposition="outside")
    fig3.update_layout(showlegend=False, coloraxis_showscale=False,
                       margin=dict(t=10, b=10), yaxis_title="", xaxis_title="")
    st.plotly_chart(fig3, use_container_width=True)


# ── SAYFA: Haberler ──────────────────────────────────────────────────────────
elif sayfa == "📰 Haberler":
    st.markdown('<div class="main-header">📰 Haber Listesi</div>',
                unsafe_allow_html=True)

    if df.empty:
        st.warning("Veritabanında henüz haber yok.")
        st.stop()

    # Filtreler
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        snt_filtre = st.multiselect("Sentiment", ["olumlu", "olumsuz", "nötr"],
                                     default=["olumlu", "olumsuz", "nötr"])
    with fc2:
        kat_filtre = st.multiselect("Kategori", df["kategori"].dropna().unique().tolist(),
                                     default=df["kategori"].dropna().unique().tolist())
    with fc3:
        arama = st.text_input("Başlıkta ara", "")

    filtreli = df[
        df["sentiment"].isin(snt_filtre) &
        df["kategori"].isin(kat_filtre)
    ]
    if arama:
        filtreli = filtreli[filtreli["baslik"].str.contains(arama, case=False, na=False)]

    st.caption(f"{len(filtreli)} haber gösteriliyor")

    for _, row in filtreli.head(50).iterrows():
        renk = {"olumlu": "🟢", "olumsuz": "🔴", "nötr": "⚪"}.get(row.sentiment, "⚪")
        tarih_str = row["tarih"].strftime("%d.%m.%Y") if pd.notna(row["tarih"]) else ""
        with st.expander(f"{renk} {row['baslik'][:90]}  `{tarih_str}`"):
            st.write(f"**Kaynak:** {row['kaynak']}  |  **Kategori:** {row['kategori']}")
            st.write(row["ai_ozet"] or row.get("ozet", ""))
            if row["url"]:
                st.markdown(f"[🔗 Habere git]({row['url']})")


# ── SAYFA: Trend Analizi ──────────────────────────────────────────────────────
elif sayfa == "📈 Trend Analizi":
    st.markdown('<div class="main-header">📈 Haftalık Trend Analizi</div>',
                unsafe_allow_html=True)

    trend = trend_yukle(8)
    if not trend:
        st.info("Trend verisi için en az 2 haftanın raporu gerekiyor.")
        st.stop()

    trend_df = pd.DataFrame(trend)
    pivot = trend_df.pivot_table(
        index="hafta", columns="sentiment", values="sayi", fill_value=0
    ).reset_index()

    fig = go.Figure()
    renk_map = {"olumlu": "#1E8449", "olumsuz": "#C0392B", "nötr": "#5D6D7E"}
    for snt in ["olumlu", "olumsuz", "nötr"]:
        if snt in pivot.columns:
            fig.add_trace(go.Scatter(
                x=pivot["hafta"], y=pivot[snt],
                name=snt.capitalize(),
                line=dict(color=renk_map[snt], width=2.5),
                mode="lines+markers",
            ))

    fig.update_layout(
        title="Haftalık Sentiment Trendi",
        xaxis_title="Hafta", yaxis_title="Haber Sayısı",
        legend_title="Sentiment",
        hovermode="x unified",
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Haftalık özet tablo
    st.subheader("Haftalık Özet Tablo")
    st.dataframe(pivot.set_index("hafta"), use_container_width=True)


# ── SAYFA: Ajan Kararları ────────────────────────────────────────────────────
elif sayfa == "🤖 Ajan Kararları":
    st.markdown('<div class="main-header">🤖 Özerk Ajan Kararları</div>',
                unsafe_allow_html=True)

    alerts_dir = BASE_DIR / "alerts"
    dosyalar = sorted(alerts_dir.glob("AJAN_ALERT_*.txt"), reverse=True)

    if not dosyalar:
        st.info("Henüz ajan kararı yok. `python main.py` çalıştırın.")
        st.stop()

    secili = st.selectbox(
        "Alert dosyası seç",
        dosyalar,
        format_func=lambda p: p.stem.replace("AJAN_ALERT_", "").replace("_", " ")
    )

    if secili:
        icerik = secili.read_text(encoding="utf-8")
        satirlar = icerik.split("\n")
        for satir in satirlar:
            if satir.startswith("⚠️"):
                st.error(satir)
            elif satir.startswith("•"):
                st.warning(satir)
            elif satir.startswith("GENEL"):
                st.subheader(satir)
            elif satir.strip():
                st.write(satir)

    st.divider()
    st.caption(f"Toplam {len(dosyalar)} ajan alert dosyası mevcut.")


# ── SAYFA: Müşteri Sesi ──────────────────────────────────────────────────────
elif sayfa == "💬 Müşteri Sesi":
    st.markdown('<div class="main-header">💬 Müşteri Sesi</div>',
                unsafe_allow_html=True)

    with st.spinner("Müşteri yorumları toplanıyor (bu birkaç dakika sürebilir)..."):
        try:
            from src.customer_voice import musteri_sesi_topla
            musteri_raporu = musteri_sesi_topla(gun=gun_filtre)
        except Exception as e:
            st.error(f"Müşteri sesi toplanamadı: {e}")
            st.stop()

    yorumlar = musteri_raporu.yorumlar
    if not yorumlar:
        st.info("Seçilen dönemde müşteri yorumu bulunamadı.")
        st.stop()

    st.success(f"{len(yorumlar)} müşteri yorumu toplandı ve analiz edildi.")

    # Özet metin
    if musteri_raporu.tema_ozeti:
        st.info(musteri_raporu.tema_ozeti)

    st.divider()

    # Metrik kartları
    tip_sayim = {}
    for y in yorumlar:
        tip_sayim[y.tip] = tip_sayim.get(y.tip, 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Yorum", len(yorumlar))
    c2.metric("🔴 Şikayet",  tip_sayim.get("sikayet",  0))
    c3.metric("🟢 Teşekkür", tip_sayim.get("tesekkur", 0))
    c4.metric("💡 Öneri",    tip_sayim.get("oneri",    0))

    st.divider()

    col1, col2 = st.columns(2)

    # Tip dağılımı pasta
    with col1:
        st.subheader("Yorum Tipi Dağılımı")
        tip_df = pd.DataFrame([
            {"tip": k or "bilinmiyor", "sayi": v}
            for k, v in tip_sayim.items()
        ])
        if not tip_df.empty:
            renk_map = {
                "sikayet": "#C0392B", "tesekkur": "#1E8449",
                "oneri": "#1A5276", "notr": "#5D6D7E", "bilinmiyor": "#AED6F1",
            }
            fig_tip = px.pie(tip_df, names="tip", values="sayi",
                             color="tip", color_discrete_map=renk_map, hole=0.4)
            fig_tip.update_traces(textposition="inside", textinfo="percent+label")
            fig_tip.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_tip, use_container_width=True)

    # Platform dağılımı pasta
    with col2:
        st.subheader("Platform Dağılımı")
        plat_sayim = {}
        for y in yorumlar:
            plat_sayim[y.platform] = plat_sayim.get(y.platform, 0) + 1
        plat_df = pd.DataFrame([{"platform": k, "sayi": v} for k, v in plat_sayim.items()])
        if not plat_df.empty:
            fig_plat = px.pie(plat_df, names="platform", values="sayi", hole=0.4)
            fig_plat.update_traces(textposition="inside", textinfo="percent+label")
            fig_plat.update_layout(showlegend=True, margin=dict(t=10, b=10))
            st.plotly_chart(fig_plat, use_container_width=True)

    # Tema çubuk grafik
    tema_sayim = {}
    for y in yorumlar:
        if y.tema:
            tema_sayim[y.tema] = tema_sayim.get(y.tema, 0) + 1
    if tema_sayim:
        st.subheader("Tema Dağılımı")
        tema_df = pd.DataFrame([
            {"tema": k, "sayi": v} for k, v in
            sorted(tema_sayim.items(), key=lambda x: x[1], reverse=True)
        ])
        fig_tema = px.bar(tema_df, x="tema", y="sayi",
                          color="sayi", color_continuous_scale="Blues", text="sayi")
        fig_tema.update_traces(textposition="outside")
        fig_tema.update_layout(showlegend=False, coloraxis_showscale=False,
                               xaxis_title="", yaxis_title="Yorum Sayısı",
                               margin=dict(t=10, b=10))
        st.plotly_chart(fig_tema, use_container_width=True)

    st.divider()

    # En sık temalar
    if musteri_raporu.en_sik_sikayet or musteri_raporu.en_sik_tesekkur:
        tc1, tc2 = st.columns(2)
        with tc1:
            st.subheader("🔴 En Sık Şikayet Temaları")
            for t in musteri_raporu.en_sik_sikayet:
                st.write(f"• {t}")
        with tc2:
            st.subheader("🟢 En Sık Teşekkür Temaları")
            for t in musteri_raporu.en_sik_tesekkur:
                st.write(f"• {t}")
        st.divider()

    # Yorum listesi
    st.subheader("Yorum Listesi")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        tip_filtre = st.multiselect("Tip", ["sikayet", "tesekkur", "oneri", "notr"],
                                     default=["sikayet", "tesekkur", "oneri", "notr"])
    with fc2:
        platform_secenekler = list({y.platform for y in yorumlar})
        plat_filtre = st.multiselect("Platform", platform_secenekler,
                                      default=platform_secenekler)
    with fc3:
        min_onem = st.slider("Min. önem skoru", 1, 10, 1)

    filtreli_yorumlar = [
        y for y in yorumlar
        if (not y.tip or y.tip in tip_filtre)
        and y.platform in plat_filtre
        and y.onem >= min_onem
    ]
    filtreli_yorumlar.sort(key=lambda y: y.onem, reverse=True)
    st.caption(f"{len(filtreli_yorumlar)} yorum gösteriliyor")

    for y in filtreli_yorumlar[:50]:
        emoji_map = {"sikayet": "🔴", "tesekkur": "🟢", "oneri": "💡", "notr": "⚪"}
        emoji = emoji_map.get(y.tip, "⚪")
        tarih_str = y.tarih.strftime("%d.%m.%Y") if y.tarih else ""
        baslik = y.baslik or y.icerik[:60]
        with st.expander(
            f"{emoji} [{y.onem}/10] {baslik[:80]}  "
            f"`{y.platform}`  `{tarih_str}`"
        ):
            st.write(f"**Tema:** {y.tema or '—'}  |  **Platform:** {y.platform}")
            st.write(y.icerik)
            if y.url:
                st.markdown(f"[🔗 Kaynağa git]({y.url})")


# ── SAYFA: LinkedIn ──────────────────────────────────────────────────────────
elif sayfa == "💼 LinkedIn":
    st.markdown('<div class="main-header">💼 LinkedIn Şirket Sayfası</div>',
                unsafe_allow_html=True)
    st.caption("linkedin.com/company/ulakhaberlesme — Son 7 günün öne çıkan gönderileri")

    with st.spinner("LinkedIn gönderileri toplanıyor..."):
        try:
            from src.linkedin_tracker import linkedin_gonderileri_cek
            linkedin_raporu = linkedin_gonderileri_cek(gun=gun_filtre)
        except Exception as e:
            st.error(f"LinkedIn verisi toplanamadı: {e}")
            st.stop()

    if linkedin_raporu.ozet:
        st.info(linkedin_raporu.ozet)

    gonderiler = linkedin_raporu.gonderiler
    if not gonderiler:
        st.warning(
            "Bu dönemde LinkedIn gönderisi bulunamadı. "
            "LinkedIn içeriği JavaScript ile yüklendiğinden public erişim kısıtlı olabilir."
        )
        st.stop()

    st.success(f"{len(gonderiler)} öne çıkan gönderi bulundu ve analiz edildi.")
    st.divider()

    # Önem skoru metrik kartları
    if gonderiler:
        cols = st.columns(len(gonderiler))
        for i, (g, col) in enumerate(zip(gonderiler, cols), 1):
            col.metric(f"#{i} Gönderi", f"{g.etkilesim_tahmini}/10", g.yazar or "")

    st.divider()

    # Gönderi kartları
    renk_map = {
        range(9, 11): "🟢",
        range(7, 9):  "🔵",
        range(4, 7):  "🟡",
    }

    def _emoji(skor):
        for r, e in renk_map.items():
            if skor in r:
                return e
        return "⚪"

    for i, g in enumerate(gonderiler, 1):
        emoji = _emoji(g.etkilesim_tahmini)
        with st.container():
            st.markdown(
                f"### {emoji} Gönderi #{i}  "
                f"`Önem: {g.etkilesim_tahmini}/10`"
            )
            if g.yazar:
                st.caption(f"Paylaşan: {g.yazar}")
            st.write(g.icerik or g.baslik)
            if g.etkilesim_aciklama:
                st.info(f"Neden önemli: {g.etkilesim_aciklama}")
            if g.url:
                st.markdown(
                    f"[🔗 LinkedIn'de görüntüle]({g.url})",
                    unsafe_allow_html=False,
                )
            st.divider()

    st.caption(
        "Not: Beğeni/yorum/paylaşım sayıları LinkedIn API Partnership "
        "gerektirdiğinden gösterilmemektedir. Önem skorları Claude içerik analiziyle belirlenir."
    )


# ── SAYFA: Kelime Bulutu ─────────────────────────────────────────────────────
elif sayfa == "☁️ Kelime Bulutu":
    st.markdown('<div class="main-header">☁️ Kelime Bulutu Analizi</div>',
                unsafe_allow_html=True)

    if df.empty:
        st.warning("Veritabanında henüz haber yok. `python main.py` çalıştırın.")
        st.stop()

    # Türkçe + İngilizce stop words
    TURKCE_STOP = {
        "ve", "ile", "bir", "bu", "da", "de", "den", "için", "olan", "olarak",
        "olan", "daha", "en", "çok", "hem", "ya", "veya", "ama", "ancak",
        "ki", "mi", "mı", "mu", "mü", "ne", "o", "şu", "bu", "her",
        "hiç", "tüm", "bazı", "diğer", "gibi", "kadar", "sonra", "önce",
        "göre", "karşı", "üzere", "dolayı", "itibaren", "arasında", "içinde",
        "üzerinde", "altında", "yanında", "ulak", "haberleşme", "haberlesme",
        "ulakın", "ulaka", "ulaktan", "şirket", "haber", "yıl",
        "ay", "gün", "yeni", "büyük", "ilk", "son", "geldi", "etti", "oldu",
        "edildi", "yapıldı", "açıklandı", "belirtti", "söyledi", "dedi",
        # Kaynak adları
        "anadolu", "ajansı", "ajans", "google", "news", "rss",
        "newsapi", "reuters", "bloomberg", "haberi", "haberleri",
    }
    stop_words = STOPWORDS.union(TURKCE_STOP)

    # Renk fonksiyonu — Ulak Haberleşme kurumsal renk paleti (mavi tonları)
    def ulak_renk(word, font_size, position, orientation, random_state=None, **kwargs):
        import random
        rnd = random.Random(hash(word))
        renkler = [
            "#1A5276", "#1F618D", "#2874A6", "#2E86C1",
            "#3498DB", "#5DADE2", "#85C1E9", "#AED6F1",
        ]
        return rnd.choice(renkler)

    def kelime_bulutu_olustur(metin: str, genislik=800, yukseklik=400) -> BytesIO:
        wc = WordCloud(
            width=genislik,
            height=yukseklik,
            background_color="white",
            stopwords=stop_words,
            color_func=ulak_renk,
            max_words=120,
            min_font_size=10,
            max_font_size=80,
            prefer_horizontal=0.85,
            collocations=False,
        ).generate(metin)
        fig, ax = plt.subplots(figsize=(genislik / 100, yukseklik / 100))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        fig.tight_layout(pad=0)
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf

    # ── Kontroller ──
    fc1, fc2 = st.columns(2)
    with fc1:
        bulut_turu = st.selectbox(
            "Kelime bulutu kaynağı",
            ["Haber Başlıkları", "Haber Özetleri (AI)", "Müşteri Şikayetleri", "Tüm İçerik"],
        )
    with fc2:
        sentiment_sec = st.multiselect(
            "Sentiment filtresi",
            ["olumlu", "olumsuz", "nötr"],
            default=["olumlu", "olumsuz", "nötr"],
        )

    filtreli_df = df[df["sentiment"].isin(sentiment_sec)] if sentiment_sec else df

    # ── Metin hazırlama ──
    if bulut_turu == "Haber Başlıkları":
        metin = " ".join(filtreli_df["baslik"].dropna().tolist())
    elif bulut_turu == "Haber Özetleri (AI)":
        metin = " ".join(filtreli_df["ai_ozet"].dropna().tolist())
    elif bulut_turu == "Müşteri Şikayetleri":
        try:
            from src.customer_voice import musteri_sesi_topla
            with st.spinner("Müşteri yorumları toplanıyor..."):
                ms = musteri_sesi_topla(gun=gun_filtre)
            metin = " ".join(
                [y.baslik + " " + y.icerik for y in ms.yorumlar]
            )
            if ms.tema_ozeti:
                st.info(ms.tema_ozeti)
        except Exception as e:
            st.error(f"Müşteri sesi alınamadı: {e}")
            metin = ""
    else:
        basliklar = " ".join(filtreli_df["baslik"].dropna().tolist())
        ozetler   = " ".join(filtreli_df["ai_ozet"].dropna().tolist())
        metin = basliklar + " " + ozetler

    if not metin or len(metin.strip()) < 50:
        st.warning("Kelime bulutu için yeterli metin bulunamadı.")
        st.stop()

    # ── Ana kelime bulutu ──
    st.subheader(f"📰 {bulut_turu} — Son {gun_filtre} Gün")
    with st.spinner("Kelime bulutu oluşturuluyor..."):
        buf = kelime_bulutu_olustur(metin, genislik=900, yukseklik=420)
    st.image(buf, use_container_width=True)

    st.divider()

    # ── Sentiment bazlı yan yana 3 bulut ──
    st.subheader("Sentiment Bazlı Karşılaştırma")
    cols = st.columns(3)
    sentiment_config = [
        ("olumlu",  "🟢 Olumlu Haberler",  "#1E8449"),
        ("olumsuz", "🔴 Olumsuz Haberler", "#C0392B"),
        ("nötr",    "⚪ Nötr Haberler",    "#5D6D7E"),
    ]

    for col, (snt, baslik, renk_hex) in zip(cols, sentiment_config):
        snt_df  = df[df["sentiment"] == snt]
        snt_txt = " ".join(snt_df["baslik"].dropna().tolist())
        if len(snt_txt.strip()) < 30:
            col.caption(f"{baslik}\n_(yeterli veri yok)_")
            continue

        def _renk_func(r=renk_hex):
            def _f(word, font_size, position, orientation, random_state=None, **kwargs):
                return r
            return _f

        with col:
            st.caption(baslik)
            wc = WordCloud(
                width=400, height=300,
                background_color="white",
                stopwords=stop_words,
                color_func=_renk_func(),
                max_words=60,
                min_font_size=8,
                collocations=False,
            ).generate(snt_txt)
            fig, ax = plt.subplots(figsize=(4, 3))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            fig.tight_layout(pad=0)
            buf2 = BytesIO()
            fig.savefig(buf2, format="png", dpi=120, bbox_inches="tight")
            plt.close(fig)
            buf2.seek(0)
            st.image(buf2, use_container_width=True)

    st.divider()

    # ── En sık kelimeler bar chart ──
    st.subheader("En Sık Geçen Kelimeler (Top 20)")
    from collections import Counter
    import re

    kelimeler = [
        k.lower() for k in re.findall(r'\b[a-zA-ZçğışöüÇĞİŞÖÜ]{4,}\b', metin)
        if k.lower() not in stop_words
    ]
    sayac = Counter(kelimeler).most_common(20)
    if sayac:
        kelime_df = pd.DataFrame(sayac, columns=["kelime", "sayi"])
        fig_bar = px.bar(
            kelime_df, x="sayi", y="kelime",
            orientation="h",
            color="sayi",
            color_continuous_scale=["#AED6F1", "#1A5276"],
            text="sayi",
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="Frekans",
            yaxis_title="",
            margin=dict(t=10, b=10),
            height=500,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── PNG indirme butonu ──
    st.divider()
    buf_dl = kelime_bulutu_olustur(metin, genislik=1200, yukseklik=600)
    st.download_button(
        "⬇ Kelime Bulutunu İndir (PNG)",
        data=buf_dl,
        file_name=f"kelime_bulutu_{datetime.now().strftime('%Y%m%d')}.png",
        mime="image/png",
    )


# ── SAYFA: İlişki Ağı ───────────────────────────────────────────────────────
elif sayfa == "🕸️ İlişki Ağı":
    import json as _json
    import streamlit.components.v1 as components
    from src.graph_builder import ag_html_uret, triple_istatistik, TripleIstatistik
    from src.news_fetcher import Haber as _Haber

    st.markdown('<div class="main-header">🕸️ Varlık İlişki Ağı</div>',
                unsafe_allow_html=True)

    if df.empty:
        st.warning("Veritabanında henüz haber yok. `python main.py` çalıştırın.")
        st.stop()

    # DB'den triple'ları yükle
    @st.cache_data(ttl=300)
    def triple_haberler_yukle(gun: int) -> list[_Haber]:
        import sqlite3
        from src.database import DB_PATH
        from datetime import datetime, timedelta
        esik = (datetime.now() - timedelta(days=gun)).isoformat()
        haberler = []
        if not DB_PATH.exists():
            return haberler
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT baslik, url, kaynak, tarih, dil, ai_ozet, sentiment, kategori, triples "
                "FROM news WHERE tarih >= ? ORDER BY tarih DESC",
                (esik,)
            ).fetchall()
        for row in rows:
            h = _Haber(
                baslik=row[0] or "",
                ozet="",
                url=row[1] or "",
                kaynak=row[2] or "",
                tarih=None,
                dil=row[4] or "tr",
            )
            h.ai_ozet   = row[5] or ""
            h.sentiment = row[6] or "nötr"
            h.kategori  = row[7] or "diğer"
            try:
                h.triples = _json.loads(row[8] or "[]")
            except Exception:
                h.triples = []
            haberler.append(h)
        return haberler

    ag_haberler = triple_haberler_yukle(gun_filtre)
    toplam_triple = sum(len(h.triples) for h in ag_haberler)

    if toplam_triple == 0:
        st.info(
            "Henüz triple verisi yok. Bu özellik son analiz çalıştırıldığında "
            "otomatik olarak doldurulur (`python main.py`). "
            "Mevcut veritabanındaki haberler eski format ile kaydedilmiştir."
        )
        st.stop()

    # İstatistikler
    istat: TripleIstatistik = triple_istatistik(ag_haberler)
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Triple", istat.toplam_triple)
    c2.metric("Benzersiz Varlık", istat.benzersiz_varlik)
    c3.metric("İlişki Türü", istat.benzersiz_iliski)

    st.divider()

    col_sol, col_sag = st.columns([3, 1])

    with col_sag:
        st.subheader("Filtreler")
        min_kenar = st.slider("Min. kenar tekrarı", 1, 5, 1,
                               help="Aynı iki varlık arasındaki min. ilişki sayısı")
        grafik_yukseklik = st.select_slider(
            "Grafik yüksekliği",
            options=["450px", "600px", "750px", "900px"],
            value="600px",
        )

        st.divider()
        st.subheader("En Sık Varlıklar")
        for varlik, sayi in istat.en_sik_varliklar[:10]:
            st.markdown(f"**{varlik}** — {sayi}")

        st.divider()
        st.subheader("En Sık İlişkiler")
        for iliski, sayi in istat.en_sik_iliskiler[:8]:
            st.markdown(f"`{iliski}` — {sayi}")

    with col_sol:
        st.subheader("Etkileşimli Ağ Grafiği")
        st.caption(
            "Düğümlere tıklayarak bilgi alabilir, sürükleyerek yerleştirme yapabilirsiniz. "
            "Kırmızı düğümler Ulak Haberleşme varlıklarını gösterir."
        )
        with st.spinner("Ağ grafiği oluşturuluyor..."):
            html_icerik = ag_html_uret(
                ag_haberler,
                min_kenar_agirlik=min_kenar,
                yukseklik=grafik_yukseklik,
            )
        components.html(html_icerik, height=int(grafik_yukseklik.replace("px", "")) + 30, scrolling=False)

    st.divider()

    # Triple tablosu
    st.subheader("Triple Listesi")
    triple_satirlar = []
    for h in ag_haberler:
        for triple in h.triples:
            if len(triple) == 3:
                triple_satirlar.append({
                    "Kaynak Varlık": triple[0],
                    "İlişki": triple[1],
                    "Hedef Varlık": triple[2],
                    "Haber": h.baslik[:80],
                    "Sentiment": h.sentiment,
                })
    if triple_satirlar:
        triple_df = pd.DataFrame(triple_satirlar)
        st.dataframe(triple_df, use_container_width=True, height=300)


# ── SAYFA: Raporlar ──────────────────────────────────────────────────────────
elif sayfa == "📁 Raporlar":
    st.markdown('<div class="main-header">📁 Geçmiş Raporlar</div>',
                unsafe_allow_html=True)

    raporlar = raporlari_yukle()
    if raporlar.empty:
        st.info("Henüz rapor üretilmemiş.")
        st.stop()

    for _, row in raporlar.iterrows():
        pdf_yolu = Path(row["dosya_yolu"]) if row["dosya_yolu"] else None
        tarih    = row["olusturuldu_at"][:10] if row["olusturuldu_at"] else "?"
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"📄 **{tarih}** — {row['haber_sayisi']} haber analiz edildi")
        with col2:
            if pdf_yolu and pdf_yolu.exists():
                with open(pdf_yolu, "rb") as f:
                    st.download_button(
                        "⬇ İndir", f.read(),
                        file_name=pdf_yolu.name,
                        mime="application/pdf",
                        key=str(row["id"]),
                    )
            else:
                st.caption("Dosya bulunamadı")
