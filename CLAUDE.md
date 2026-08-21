# Ulak Haberleşme Medya İstihbarat Sistemi — Proje Bağlamı

## Amaç
Ulak Haberleşme A.Ş. ile ilgili Türkçe ve İngilizce haberleri otomatik olarak toplayıp Claude CLI ile
analiz eden, PDF raporu ve Streamlit dashboard üreten haftalık medya takip sistemi.

Bu proje, Türksat için yazılmış aynı multi-tenant SaaS'ın (bkz. `C:\Users\bilal\Desktop\TÜRKSAT\ÖVEÇLER\Medya-Istihbarat`)
Ulak Haberleşme'ye özelleştirilmiş bağımsız bir kopyasıdır.

## Klasör Yapısı
```
Turksat-Rapor/
├── src/
│   ├── news_fetcher.py        Google News RSS haber çekme
│   ├── crawler_agent.py       DuckDuckGo web tarama ajanı
│   ├── press_scraper.py       Resmi basın odası scraper (Ulak Haberleşme için şu an devre dışı)
│   ├── analyzer.py            Claude CLI batch analizi (sentiment · kategori · triple)
│   ├── agent.py               Özerk Claude ajanı (önem skoru + aksiyon önerisi)
│   ├── mcp_server.py          MCP araç sunucusu (Claude'un kullandığı)
│   ├── clusterer.py           Sentence-transformer ile haber tekilleştirme
│   ├── competitor_tracker.py  Rakip haber + yfinance borsa verisi
│   ├── customer_voice.py      Şikayetvar, Ekşi Sözlük, Reddit, Google Play scraping
│   ├── linkedin_tracker.py    LinkedIn kamuya açık gönderi takibi
│   ├── crisis_detector.py     Kural tabanlı kriz tespiti + alerts/ dosyası
│   ├── graph_builder.py       pyvis varlık ilişki grafiği (triple → HTML)
│   ├── report_generator.py    ReportLab PDF rapor üretimi
│   ├── email_sender.py        SMTP — haftalık rapor + kriz + hata bildirimi
│   ├── database.py            SQLite kalıcı depolama
│   └── retry.py               Decorator tabanlı retry mekanizması
├── config/
│   └── settings.py            Merkezi konfigürasyon (.env okur)
├── scripts/
│   ├── setup_task.ps1         Windows Görev Zamanlayıcı kurulum scripti
│   └── run_report.ps1         Manuel tetikleme yardımcısı
├── templates/                 Logo ve rapor varlıkları
├── reports/                   Üretilen PDF'ler (git'e alınmaz)
├── logs/                      Log dosyaları (git'e alınmaz)
├── alerts/                    Kriz uyarı dosyaları (git'e alınmaz)
├── dashboard.py               Streamlit dashboard (9 sayfa)
├── main.py                    Pipeline giriş noktası (7 adım)
├── .env                       API key'ler ve SMTP (git'e alınmaz)
├── .env.example               Ortam değişkeni şablonu
├── .mcp.json                  Claude CLI MCP sunucu konfigürasyonu
└── requirements.txt
```

## Claude CLI Kullanımı
- AI analizi API key ile değil, `claude -p "..."` subprocess komutu ile yapılır
- Kullanıcının Claude Pro aboneliği CLI üzerinden kullanılır (sıfır ek maliyet)
- `subprocess.run([claude_bin, "-p", prompt], capture_output=True, text=True, encoding="utf-8")`
- Batch analiz: 10 haber tek çağrıda işlenir (rate-limit koruması)
- Yönetici özeti: MCP araçları etkinleştirilmiş (`--mcp-config .mcp.json`)
- Tüm çıktılar Türkçe

## MCP Araçları
`src/mcp_server.py` iki araç sunar — Claude yönetici özeti üretirken bunları çağırabilir:
- `search_company_news`: DuckDuckGo araması (alan adı + tarih filtresi opsiyonel)
- `get_sentiment_trend`: SQLite'tan haftalık sentiment dağılımı

## Veri Modeli

### `Haber` (src/news_fetcher.py)
```python
baslik, ozet, url, kaynak, tarih, dil        # Kaynak veriler
ai_ozet, sentiment, kategori, triples         # Analyzer tarafından doldurulur
```
`triples`: `[["Kaynak Varlık", "ilişki türü", "Hedef Varlık"], ...]` — max 3/haber

### SQLite tabloları
- `news`: tüm haber alanları + `triples` (JSON text)
- `reports`: rapor meta verisi + dosya yolu

## Rapor Formatı (PDF)
1. Kapak sayfası
2. Yönetici özeti (Claude + MCP araçlarıyla üretilir)
3. Sentiment dağılımı tablosu + pasta grafik
4. Kategori bazlı haber grupları
5. Rakip firma bölümü (borsa verisi dahil)
6. Müşteri sesi bölümü (tip + tema dağılımı)
7. LinkedIn gönderileri bölümü
8. Kaynak listesi

## Kriz Tespiti
İki katmanlı anahtar kelime sistemi:
- `KRITIK_KELIMELER_GENEL`: Ulak Haberleşme adı aranmaksızın her haberde tetikler
- `KRITIK_KELIMELER_BAGLAM`: Yalnızca Ulak Haberleşme adı da geçiyorsa tetikler (false positive önlemi)
- %40+ olumsuz → DİKKAT, %60+ olumsuz → KRİZ
- Tetiklenince: log uyarısı + `alerts/ALERT_*.txt` + kriz e-postası

## E-posta Bildirimleri
- `rapor_gonder()`: haftalık raporu PDF eki olarak gönderir
- `kriz_bildir()`: kriz/dikkat seviyesinde HTML e-posta
- `hata_bildir()`: pipeline çöktüğünde hangi adımda, traceback ile bildirim
- `SMTP_HOST` tanımlı değilse tüm e-posta gönderimi sessizce atlanır

## Zamanlama
- Her Pazartesi sabahı 08:00 (Windows Görev Zamanlayıcı)
- `scripts/setup_task.ps1` Yönetici olarak çalıştırılarak kurulur
- Manuel çalıştırma: `python main.py`

## Ortam Değişkenleri
| Değişken | Zorunlu | Açıklama |
|---|---|---|
| `CLAUDE_TIMEOUT` | Hayır | Claude CLI zaman aşımı sn (varsayılan: 120) |
| `REPORT_OUTPUT_DIR` | Hayır | Çıktı klasörü (varsayılan: `reports/`) |
| `LOG_DIR` | Hayır | Log klasörü (varsayılan: `logs/`) |
| `SMTP_HOST` | Hayır | E-posta sunucusu |
| `SMTP_PORT` | Hayır | SMTP port (varsayılan: 587) |
| `SMTP_USER` | Hayır | SMTP kullanıcı adı |
| `SMTP_PASSWORD` | Hayır | SMTP şifresi |
| `EMAIL_FROM` | Hayır | Gönderen adresi |
| `EMAIL_TO` | Hayır | Alıcı adresleri (virgülle ayrılır) |

## Kodlama Kuralları
- Python 3.11+
- Tüm log mesajları Türkçe
- Hata durumunda pipeline `raise` ile sonlanır, `hata_bildir()` e-posta gönderir
- `reports/`, `logs/`, `alerts/`, `ulak.db` git'e alınmaz
