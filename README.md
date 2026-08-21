# Medya İstihbarat Sistemi · Media Intelligence System

<p align="center">
  <strong>Kurumsal medya takip, rakip analizi ve otomatik raporlama platformu</strong><br>
  <em>Corporate media monitoring, competitor analysis, and automated reporting platform</em>
</p>

---

## 🇹🇷 Türkçe

### Nedir?

Kurumunuzla ilgili Türkçe ve İngilizce haberleri otomatik olarak toplar, yapay zeka ile analiz eder, PDF raporu üretir ve haftalık olarak e-posta ile gönderir. Multi-tenant SaaS mimarisiyle farklı kurumlar aynı platform üzerinde izole çalışır.

### Özellikler

- **Haber Toplama** — Google News RSS, NewsAPI, DuckDuckGo, basın odası scraping
- **AI Analizi** — Sentiment analizi, kategori sınıflandırma, varlık ilişki tripleti çıkarma
- **Rakip Takibi** — Rakip haberleri + borsa verisi (yfinance)
- **LinkedIn Takibi** — Kamuya açık LinkedIn gönderileri
- **Kriz Tespiti** — İki katmanlı anahtar kelime sistemi, %40/%60 olumsuz eşiği
- **PDF Raporu** — Yönetici özeti, sentiment grafikleri, kaynak listesi
- **E-posta Bildirimi** — Haftalık rapor, kriz uyarısı, hata bildirimi (Resend API)
- **Streamlit Dashboard** — 9 sayfalık interaktif dashboard
- **Multi-Tenant SaaS** — FastAPI backend + React/TypeScript frontend
- **Dinamik Marka Rengi** — Kuruma özel arayüz rengi (yerel DB + Brandfetch API + LLM)

### Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/duembi/Medya-Istihbarat-.git
cd Medya-Istihbarat-

# 2. Sanal ortam oluştur
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Ortam değişkenlerini ayarla
copy .env.example .env
# .env dosyasını düzenle (NEWS_API_KEY zorunlu, diğerleri isteğe bağlı)

# 5. Frontend bağımlılıkları
cd frontend
npm install
npm run build
cd ..
```

### Çalıştırma

```bash
# Backend API (port 8000)
uvicorn api.main:app --reload

# Frontend geliştirme sunucusu (port 5173)
cd frontend && npm run dev

# Streamlit dashboard (port 8501)
streamlit run dashboard.py

# Manuel rapor üretimi
python main.py
```

### Ortam Değişkenleri

| Değişken | Zorunlu | Açıklama |
|---|:---:|---|
| `NEWS_API_KEY` | ✅ | [newsapi.org](https://newsapi.org/register) ücretsiz key |
| `JWT_SECRET_KEY` | ✅ | Üretim için en az 32 karakter rastgele string |
| `AI_BACKEND` | — | `gemini` (varsayılan) veya `claude` |
| `GEMINI_API_KEY` | — | [Google AI Studio](https://aistudio.google.com/app/apikey) ücretsiz key |
| `BRANDFETCH_API_KEY` | — | [Brandfetch](https://developers.brandfetch.com/register) — marka rengi API |
| `RESEND_API_KEY` | — | [Resend](https://resend.com) — e-posta bildirimleri |
| `EMAIL_TO` | — | Alıcı adresleri (virgülle ayrılır) |

Tüm değişkenler için `.env.example` dosyasına bakın.

### Teknoloji Yığını

- **Backend:** Python 3.11+, FastAPI, SQLite, uvicorn
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
- **AI:** Gemini 2.5 Flash / Claude Haiku (yapılandırılabilir)
- **Raporlama:** ReportLab (PDF), Streamlit (dashboard)
- **E-posta:** Resend API

---

## 🇬🇧 English

### What is it?

An automated media monitoring platform that collects Turkish and English news about your organization, analyzes them with AI, generates PDF reports, and sends them via email weekly. Built on a multi-tenant SaaS architecture so multiple organizations can run in isolation on the same platform.

### Features

- **News Collection** — Google News RSS, NewsAPI, DuckDuckGo, press room scraping
- **AI Analysis** — Sentiment analysis, category classification, entity relationship triple extraction
- **Competitor Tracking** — Competitor news + stock data (yfinance)
- **LinkedIn Monitoring** — Public LinkedIn post tracking
- **Crisis Detection** — Two-tier keyword system, 40%/60% negative sentiment thresholds
- **PDF Reports** — Executive summary, sentiment charts, source list
- **Email Notifications** — Weekly report, crisis alerts, error notifications (Resend API)
- **Streamlit Dashboard** — 9-page interactive dashboard
- **Multi-Tenant SaaS** — FastAPI backend + React/TypeScript frontend
- **Dynamic Brand Theming** — Per-tenant UI colors (local DB + Brandfetch API + LLM fallback)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/duembi/Medya-Istihbarat-.git
cd Medya-Istihbarat-

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS
# Edit .env (NEWS_API_KEY required, others optional)

# 5. Frontend dependencies
cd frontend
npm install
npm run build
cd ..
```

### Running

```bash
# Backend API (port 8000)
uvicorn api.main:app --reload

# Frontend dev server (port 5173)
cd frontend && npm run dev

# Streamlit dashboard (port 8501)
streamlit run dashboard.py

# Manual report generation
python main.py
```

### Environment Variables

| Variable | Required | Description |
|---|:---:|---|
| `NEWS_API_KEY` | ✅ | [newsapi.org](https://newsapi.org/register) free key |
| `JWT_SECRET_KEY` | ✅ | At least 32 random characters for production |
| `AI_BACKEND` | — | `gemini` (default) or `claude` |
| `GEMINI_API_KEY` | — | [Google AI Studio](https://aistudio.google.com/app/apikey) free key |
| `BRANDFETCH_API_KEY` | — | [Brandfetch](https://developers.brandfetch.com/register) — brand color API |
| `RESEND_API_KEY` | — | [Resend](https://resend.com) — email notifications |
| `EMAIL_TO` | — | Recipient addresses (comma-separated) |

See `.env.example` for all variables.

### Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLite, uvicorn
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
- **AI:** Gemini 2.5 Flash / Claude Haiku (configurable)
- **Reporting:** ReportLab (PDF), Streamlit (dashboard)
- **Email:** Resend API

### Brand Color Resolution Chain

When a user logs in, the system resolves brand colors in this order:

1. **Local DB** (731 brands from reimertz/brand-colors + curated Turkish companies) — instant, no API call
2. **Brandfetch API** (domain-based lookup, requires `BRANDFETCH_API_KEY`) — real official brand colors
3. **LLM** (Gemini/Claude generates colors based on company knowledge) — fallback for unknown brands
4. **Defaults** (blue theme) — if all above fail

---

## License

MIT
