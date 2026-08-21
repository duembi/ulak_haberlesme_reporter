import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Auth & Multi-Tenant ───────────────────────────────────────────────────────
JWT_SECRET_KEY  = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_in_production_min_32_chars!!")
JWT_ALGORITHM   = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", str(60 * 24 * 7)))  # 7 gün

# API key şifreleme — boşsa otomatik olarak .encryption_key dosyasına üretilir
ENCRYPTION_KEY  = os.getenv("ENCRYPTION_KEY", "")

REPORT_OUTPUT_DIR = BASE_DIR / os.getenv("REPORT_OUTPUT_DIR", "reports")
LOG_DIR = BASE_DIR / os.getenv("LOG_DIR", "logs")

REPORT_OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ── AI backend seçimi ────────────────────────────────────────────────────────
# AI_BACKEND: 'gemini' (varsayılan) | 'claude'
AI_BACKEND = os.getenv("AI_BACKEND", "gemini")

# Claude CLI
CLAUDE_TIMEOUT = int(os.getenv("CLAUDE_TIMEOUT", "300"))
CLAUDE_MODEL   = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Brandfetch API — marka rengi sorgulama (isteğe bağlı)
BRANDFETCH_API_KEY = os.getenv("BRANDFETCH_API_KEY", "")

# E-posta — Resend API
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM    = os.getenv("RESEND_FROM", "Ulak Haberleşme Rapor <onboarding@resend.dev>")
EMAIL_TO       = [a.strip() for a in os.getenv("EMAIL_TO", "").split(",") if a.strip()]

SEARCH_KEYWORDS_TR = ["Ulak Haberleşme", "ULAK Haberleşme A.Ş."]
SEARCH_KEYWORDS_EN = ["Ulak Haberlesme", "Ulak Communications Turkey"]

# Kategori bazlı arama sorguları — DuckDuckGo'da kullanılır
# Her kategori ayrı bir API çağrısı olarak çalışır; bağlamsal kelimeler
# yanlış pozitif almamak için "Ulak Haberleşme" öneki ile birleştirilir.
ARAMA_KATEGORILERI = {
    "Corporate": {
        "tr": ["Ulak Haberleşme A.Ş.", "Ulak Haberleşme ASELSAN HAVELSAN SSTEK", "Ulak Haberleşme genel müdür"],
        "en": ["Ulak Haberlesme CEO", "Ulak Haberlesme management", "Ulak Haberlesme ASELSAN"],
    },
    "5G_Network": {
        "tr": ["ULAK 5G baz istasyonu", "yerli milli 5G Ulak", "Ulak çekirdek şebeke yazılımı"],
        "en": ["ULAK 5G base station Turkey", "Turkey domestic 5G network", "Ulak core network software"],
    },
    "Tactical_Comms": {
        "tr": ["ULAK Yazılım Tabanlı Telsiz", "V/UHF telsiz Ulak", "SSB ULAK projesi"],
        "en": ["ULAK software defined radio", "V/UHF radio Turkey defense"],
    },
    "Public_Safety_Smart_City": {
        "tr": ["Ulak Mobil Haberleşme Sistemi", "acil durum haberleşme şebekesi Ulak", "akıllı şehir Ulak Haberleşme"],
        "en": ["Ulak public safety network", "Ulak smart city communication"],
    },
    "Crisis_Alerts": {
        "tr": ["Ulak Haberleşme arıza", "Ulak Haberleşme ihale iptal", "Ulak Haberleşme gecikme"],
        "en": ["Ulak Haberlesme outage", "Ulak Haberlesme delay"],
    },
}

GOOGLE_NEWS_RSS_TR = "https://news.google.com/rss/search?q=%22Ulak+Haberle%C5%9Fme%22&hl=tr&gl=TR&ceid=TR:tr"
GOOGLE_NEWS_RSS_EN = "https://news.google.com/rss/search?q=%22Ulak+Haberlesme%22&hl=en&gl=US&ceid=US:en"

# Anadolu Ajansı — Google News üzerinden AA haberleri
AA_RSS_TR = "https://news.google.com/rss/search?q=%22Ulak+Haberle%C5%9Fme%22+site%3Aaa.com.tr&hl=tr&gl=TR&ceid=TR:tr"
AA_RSS_EN = "https://news.google.com/rss/search?q=%22Ulak+Haberlesme%22+site%3Aaa.com.tr&hl=en&gl=US&ceid=US:en"

NEWS_API_LOOKBACK_DAYS = 7
