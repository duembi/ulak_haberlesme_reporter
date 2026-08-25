import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import BASE_DIR

DB_PATH = BASE_DIR / "ulak.db"

# ── Bağlantı ─────────────────────────────────────────────────────────────────

@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema Init ───────────────────────────────────────────────────────────────

def init_db():
    with _conn() as conn:
        conn.executescript("""
            -- ── Tenants (Kurumlar) ───────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS tenants (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                ad             TEXT    NOT NULL,
                domain         TEXT    NOT NULL UNIQUE,
                brand_colors   TEXT,
                aktif          INTEGER NOT NULL DEFAULT 1,
                olusturuldu_at TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            -- ── Users (Kullanıcılar) ─────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id      INTEGER NOT NULL REFERENCES tenants(id),
                email          TEXT    NOT NULL UNIQUE,
                password_hash  TEXT    NOT NULL,
                ad_soyad       TEXT    NOT NULL,
                rol            TEXT    NOT NULL DEFAULT 'kullanici',
                aktif          INTEGER NOT NULL DEFAULT 1,
                olusturuldu_at TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            -- ── Tenant LLM Konfigürasyonları ─────────────────────────────────
            CREATE TABLE IF NOT EXISTS tenant_llm_configs (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id          INTEGER NOT NULL REFERENCES tenants(id),
                provider_name      TEXT    NOT NULL,
                model_name         TEXT    NOT NULL,
                base_url           TEXT,
                api_key_encrypted  TEXT    NOT NULL,
                aktif              INTEGER NOT NULL DEFAULT 0,
                olusturuldu_at     TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            -- ── Tenant Rakipleri (AI Önerisi) ────────────────────────────────
            CREATE TABLE IF NOT EXISTS tenant_competitors (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id      INTEGER NOT NULL REFERENCES tenants(id),
                ad             TEXT    NOT NULL,
                aciklama       TEXT    NOT NULL DEFAULT '',
                bolge          TEXT    NOT NULL DEFAULT '',
                sektor         TEXT    NOT NULL DEFAULT '',
                aktif          INTEGER NOT NULL DEFAULT 1,
                ai_onerisi     INTEGER NOT NULL DEFAULT 1,
                olusturuldu_at TEXT    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tenant_id, ad)
            );

            -- ── Report Jobs (Asenkron Raporlama) ─────────────────────────────
            CREATE TABLE IF NOT EXISTS report_jobs (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id            INTEGER NOT NULL REFERENCES tenants(id),
                durum                TEXT    NOT NULL DEFAULT 'kuyrukta',
                gun                  INTEGER NOT NULL DEFAULT 7,
                kapsam               TEXT    NOT NULL DEFAULT 'hepsi',
                rakipler_json        TEXT    DEFAULT '[]',
                mail_alicilari_json  TEXT    DEFAULT '[]',
                hata_mesaji          TEXT,
                rapor_id             INTEGER,
                baslangic_at         TEXT,
                bitis_at             TEXT,
                olusturuldu_at       TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            -- ── Haberler ─────────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS news (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                baslik        TEXT    NOT NULL,
                url           TEXT    UNIQUE NOT NULL,
                kaynak        TEXT,
                tarih         TEXT,
                dil           TEXT,
                ai_ozet       TEXT,
                sentiment     TEXT,
                kategori      TEXT,
                triples       TEXT    DEFAULT '[]',
                rapor_id      INTEGER,
                tenant_id     INTEGER DEFAULT 1,
                eklendi_at    TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            -- ── Raporlar ─────────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS reports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ad              TEXT,
                olusturuldu_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                baslangic_tarih TEXT,
                bitis_tarih     TEXT,
                haber_sayisi    INTEGER,
                dosya_yolu      TEXT,
                tenant_id       INTEGER DEFAULT 1
            );

            -- ── Mail Listesi ─────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS mail_listesi (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_soyad    TEXT    NOT NULL,
                email       TEXT    NOT NULL,
                rol         TEXT    NOT NULL DEFAULT 'izleyici',
                haftalik    INTEGER NOT NULL DEFAULT 1,
                kriz        INTEGER NOT NULL DEFAULT 1,
                hata        INTEGER NOT NULL DEFAULT 0,
                aktif       INTEGER NOT NULL DEFAULT 1,
                tenant_id   INTEGER DEFAULT 1,
                eklendi_at  TEXT    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email, tenant_id)
            );

            -- ── Ayarlar ──────────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS ayarlar (
                anahtar TEXT PRIMARY KEY,
                deger   TEXT NOT NULL
            );

            -- ── Global Rakip Kataloğu (manuel yönetim) ───────────────────────
            CREATE TABLE IF NOT EXISTS rakipler (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ad          TEXT    NOT NULL UNIQUE,
                rss_sorgu   TEXT    NOT NULL,
                rss_dil     TEXT    NOT NULL DEFAULT 'en',
                ticker      TEXT,
                bolge       TEXT    NOT NULL,
                aciklama    TEXT    NOT NULL DEFAULT '',
                aktif       INTEGER NOT NULL DEFAULT 1,
                eklendi_at  TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            -- ── LinkedIn Takip Etiketleri ─────────────────────────────────────
            CREATE TABLE IF NOT EXISTS linkedin_tags (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id      INTEGER NOT NULL REFERENCES tenants(id),
                firma          TEXT    NOT NULL DEFAULT 'ULAK',
                tag            TEXT    NOT NULL,
                aciklama       TEXT    NOT NULL DEFAULT '',
                kaynak         TEXT    NOT NULL DEFAULT 'manuel',
                secili         INTEGER NOT NULL DEFAULT 1,
                olusturuldu_at TEXT    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tenant_id, firma, tag)
            );

            -- ── Yönetim Kurulu / Yönetim Takibi ────────────────────────────────
            CREATE TABLE IF NOT EXISTS yonetim_kisi (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id      INTEGER NOT NULL DEFAULT 1,
                ad_soyad       TEXT    NOT NULL,
                unvan          TEXT    NOT NULL DEFAULT '',
                grup           TEXT    NOT NULL DEFAULT 'kurul',
                foto_url       TEXT    NOT NULL DEFAULT '',
                linkedin_url   TEXT,
                kaynak         TEXT    NOT NULL DEFAULT 'resmi_site',
                aktif          INTEGER NOT NULL DEFAULT 1,
                olusturuldu_at TEXT    DEFAULT CURRENT_TIMESTAMP,
                guncellendi_at TEXT    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tenant_id, ad_soyad, grup)
            );

            CREATE TABLE IF NOT EXISTS yonetim_degisiklik (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL DEFAULT 1,
                ad_soyad  TEXT    NOT NULL,
                tur       TEXT    NOT NULL,
                detay     TEXT    NOT NULL DEFAULT '',
                tarih     TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            -- ── İndeksler ────────────────────────────────────────────────────
            CREATE INDEX IF NOT EXISTS idx_news_tarih          ON news(tarih);
            CREATE INDEX IF NOT EXISTS idx_news_sentiment      ON news(sentiment);
            CREATE INDEX IF NOT EXISTS idx_news_rapor          ON news(rapor_id);
            CREATE INDEX IF NOT EXISTS idx_mail_aktif          ON mail_listesi(aktif);
            CREATE INDEX IF NOT EXISTS idx_rakip_aktif         ON rakipler(aktif);
            CREATE INDEX IF NOT EXISTS idx_tenant_comp_tenant  ON tenant_competitors(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_report_jobs_tenant  ON report_jobs(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_users_email         ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_tenant        ON users(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_linkedin_tags_tenant ON linkedin_tags(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_yonetim_kisi_tenant ON yonetim_kisi(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_yonetim_degisiklik_tenant ON yonetim_degisiklik(tenant_id);
        """)

        conn.execute(
            "INSERT OR IGNORE INTO ayarlar (anahtar, deger) VALUES ('model', 'claude-sonnet-4-6')"
        )
        conn.commit()

    _mevcut_tablo_migrasyonu()
    _rakip_seed()


def _mevcut_tablo_migrasyonu():
    """Mevcut veritabanlarına eksik kolonları ve indexleri ekler (idempotent)."""
    ddl_listesi = [
        "ALTER TABLE news ADD COLUMN triples TEXT DEFAULT '[]'",
        "ALTER TABLE news ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE reports ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE mail_listesi ADD COLUMN tenant_id INTEGER DEFAULT 1",
        "ALTER TABLE tenants ADD COLUMN brand_colors TEXT",
        "ALTER TABLE reports ADD COLUMN ad TEXT",
        "ALTER TABLE linkedin_tags ADD COLUMN firma TEXT DEFAULT 'ULAK'",
        "ALTER TABLE yonetim_kisi ADD COLUMN linkedin_url TEXT",
        "ALTER TABLE yonetim_kisi ADD COLUMN kaynak TEXT DEFAULT 'resmi_site'",
        "CREATE INDEX IF NOT EXISTS idx_news_tenant    ON news(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_mail_tenant    ON mail_listesi(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_reports_tenant ON reports(tenant_id)",
    ]
    with _conn() as conn:
        for sql in ddl_listesi:
            try:
                conn.execute(sql)
                conn.commit()
            except Exception:
                pass


def _rakip_seed():
    """Rakipler tablosu boşsa varsayılan listeyi ekler."""
    with _conn() as conn:
        sayi = conn.execute("SELECT COUNT(*) FROM rakipler").fetchone()[0]
        if sayi > 0:
            return
        varsayilan = [
            ("Eutelsat",               "Eutelsat satellite news",                         "en", "ETL.PA",   "Fransa",         "Avrupa'nın önde gelen uydu operatörü"),
            ("SES",                    "SES satellite operator news",                     "en", "SESG.PA",  "Lüksemburg",     "Global uydu ve video dağıtım hizmetleri"),
            ("Arabsat",                "Arabsat satellite news",                          "en", None,       "Suudi Arabistan","Orta Doğu ve Kuzey Afrika uydu operatörü"),
            ("Intelsat",               "Intelsat satellite news",                         "en", None,       "ABD",            "Global uydu iletişim operatörü"),
            ("Starlink",               "Starlink SpaceX satellite internet",               "en", None,       "ABD",            "SpaceX'in düşük yörüngeli uydu internet hizmeti"),
            ("Turkcell",               "Turkcell uydu internet",                          "tr", "TCELL.IS", "Türkiye",        "Türkiye'nin önde gelen telekom operatörü"),
            ("Türk Telekom",           "Türk Telekom altyapı",                            "tr", "TTKOM.IS", "Türkiye",        "Türkiye sabit hat ve internet altyapısı"),
            ("TUSAŞ",                  "TUSAŞ TAI Türk havacılık uzay sanayii",           "tr", None,       "Türkiye",        "Türkiye'nin milli havacılık ve uzay sanayii kuruluşu"),
            ("SDT Uzay",               "SDT uzay savunma teknolojileri uydu",             "tr", None,       "Türkiye",        "Yerli uydu ve uzay sistemleri geliştiren savunma firması"),
            ("TUA",                    "TUA Türkiye Uzay Ajansı",                         "tr", None,       "Türkiye",        "Türkiye Uzay Ajansı — ulusal uzay politikası ve programları"),
            ("PLANS",                  "PLANS uzay Bilkent Cyberpark uydu",               "tr", None,       "Türkiye",        "Bilkent Cyberpark merkezli yerli uzay teknolojileri şirketi"),
            ("SpaceX",                 "SpaceX rocket launch satellite news",             "en", None,       "ABD",            "Elon Musk'ın özel uzay şirketi; Falcon, Starship, Starlink"),
            ("Planet Labs",            "Planet Labs satellite imagery earth observation", "en", "PL",        "ABD",            "Dünya gözlem uyduları ve görüntüleme hizmetleri (NYSE: PL)"),
            ("Blue Origin",            "Blue Origin New Glenn rocket launch",             "en", None,       "ABD",            "Jeff Bezos'un özel uzay şirketi"),
            ("Airbus Defence & Space", "Airbus Defence Space satellite contract",         "en", "AIR.PA",   "Avrupa",         "Avrupa'nın önde gelen uydu üreticisi ve savunma şirketi"),
            ("Thales Alenia Space",    "Thales Alenia Space satellite contract",          "en", None,       "Fransa/İtalya",  "Uydu üretimi ve uzay sistemleri entegratörü"),
            ("NASA",                   "NASA space mission launch satellite",             "en", None,       "ABD",            "ABD Ulusal Havacılık ve Uzay İdaresi"),
            ("ESA",                    "ESA European Space Agency mission satellite",     "en", None,       "Avrupa",         "Avrupa Uzay Ajansı"),
            ("JAXA",                   "JAXA Japan space agency mission launch",          "en", None,       "Japonya",        "Japonya Havacılık Araştırma Ajansı"),
            ("ISRO",                   "ISRO India space mission satellite launch",       "en", None,       "Hindistan",      "Hindistan Uzay Araştırma Örgütü"),
            ("CNSA",                   "CNSA China space agency Tiangong satellite",      "en", None,       "Çin",            "Çin Ulusal Uzay İdaresi"),
            ("Roscosmos",              "Roscosmos Russia space satellite Soyuz",          "en", None,       "Rusya",          "Rusya Federal Uzay Ajansı"),
            ("UK Space Agency",        "UK Space Agency satellite launch programme",      "en", None,       "İngiltere",      "İngiltere Uzay Ajansı"),
            ("CSA",                    "Canadian Space Agency CSA mission satellite",     "en", None,       "Kanada",         "Kanada Uzay Ajansı"),
            ("UAE Space Agency",       "UAE Space Agency Emirates Mission Mars satellite","en", None,       "BAE",            "Birleşik Arap Emirlikleri Uzay Ajansı"),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO rakipler (ad, rss_sorgu, rss_dil, ticker, bolge, aciklama) VALUES (?, ?, ?, ?, ?, ?)",
            varsayilan,
        )


# ── Tenant CRUD ───────────────────────────────────────────────────────────────

def tenant_bul_veya_olustur(domain: str, ad: str) -> int:
    """Domain'e göre tenant bulur veya oluşturur. tenant_id döner."""
    domain = domain.lower().strip()
    with _conn() as conn:
        row = conn.execute("SELECT id FROM tenants WHERE domain = ?", (domain,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO tenants (ad, domain) VALUES (?, ?)", (ad, domain)
        )
        return cur.lastrowid


def tenant_al(tenant_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
    return dict(row) if row else None


def tenant_brand_colors_al(tenant_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT brand_colors FROM tenants WHERE id = ?", (tenant_id,)
        ).fetchone()
    if not row or not row["brand_colors"]:
        return None
    import json as _json
    try:
        return _json.loads(row["brand_colors"])
    except Exception:
        return None


def tenant_brand_colors_kaydet(tenant_id: int, colors: dict) -> None:
    import json as _json
    with _conn() as conn:
        conn.execute(
            "UPDATE tenants SET brand_colors = ? WHERE id = ?",
            (_json.dumps(colors, ensure_ascii=False), tenant_id),
        )


# ── User CRUD ─────────────────────────────────────────────────────────────────

def kullanici_ekle(tenant_id: int, email: str, password_hash: str,
                   ad_soyad: str, rol: str = "kullanici") -> int | None:
    """Kullanıcı ekler. E-posta zaten varsa None döner."""
    try:
        with _conn() as conn:
            cur = conn.execute(
                """INSERT INTO users (tenant_id, email, password_hash, ad_soyad, rol)
                   VALUES (?, ?, ?, ?, ?)""",
                (tenant_id, email.lower().strip(), password_hash, ad_soyad, rol),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def kullanici_bul(email: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? AND aktif = 1",
            (email.lower().strip(),),
        ).fetchone()
    return dict(row) if row else None


def kullanici_sayisi(tenant_id: int) -> int:
    with _conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM users WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()[0]


# ── Tenant LLM Config CRUD ────────────────────────────────────────────────────

def tenant_llm_config_ekle(tenant_id: int, provider_name: str, model_name: str,
                            api_key_encrypted: str, base_url: str | None = None) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO tenant_llm_configs
               (tenant_id, provider_name, model_name, api_key_encrypted, base_url)
               VALUES (?, ?, ?, ?, ?)""",
            (tenant_id, provider_name, model_name, api_key_encrypted, base_url),
        )
        return cur.lastrowid


def tenant_llm_config_al(tenant_id: int) -> dict | None:
    """Tenant'ın aktif LLM konfigürasyonunu döner."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM tenant_llm_configs WHERE tenant_id = ? AND aktif = 1 ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        ).fetchone()
    return dict(row) if row else None


def tenant_llm_config_listele(tenant_id: int) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tenant_llm_configs WHERE tenant_id = ? ORDER BY id DESC",
            (tenant_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def tenant_llm_config_aktifle(config_id: int, tenant_id: int) -> bool:
    """Önce tüm konfigürasyonları pasife alır, sonra seçileni aktifleştirir."""
    with _conn() as conn:
        conn.execute(
            "UPDATE tenant_llm_configs SET aktif = 0 WHERE tenant_id = ?", (tenant_id,)
        )
        c = conn.execute(
            "UPDATE tenant_llm_configs SET aktif = 1 WHERE id = ? AND tenant_id = ?",
            (config_id, tenant_id),
        )
    return c.rowcount > 0


def tenant_llm_config_sil(config_id: int, tenant_id: int) -> bool:
    with _conn() as conn:
        c = conn.execute(
            "DELETE FROM tenant_llm_configs WHERE id = ? AND tenant_id = ?",
            (config_id, tenant_id),
        )
    return c.rowcount > 0


# ── Tenant Competitors CRUD ───────────────────────────────────────────────────

def tenant_rakip_ekle(tenant_id: int, ad: str, aciklama: str = "",
                       bolge: str = "", sektor: str = "", ai_onerisi: bool = True) -> bool:
    try:
        with _conn() as conn:
            conn.execute(
                """INSERT INTO tenant_competitors
                   (tenant_id, ad, aciklama, bolge, sektor, ai_onerisi)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (tenant_id, ad.strip(), aciklama, bolge, sektor, int(ai_onerisi)),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def tenant_rakip_listele(tenant_id: int, sadece_aktif: bool = True) -> list[dict]:
    with _conn() as conn:
        if sadece_aktif:
            rows = conn.execute(
                "SELECT * FROM tenant_competitors WHERE tenant_id = ? AND aktif = 1 ORDER BY ad",
                (tenant_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tenant_competitors WHERE tenant_id = ? ORDER BY aktif DESC, ad",
                (tenant_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def tenant_rakip_guncelle(rakip_id: int, tenant_id: int, **kwargs) -> bool:
    izin_verilen = {"ad", "aciklama", "bolge", "sektor", "aktif"}
    guncellenecek = {k: v for k, v in kwargs.items() if k in izin_verilen}
    if not guncellenecek:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in guncellenecek)
    degerler = list(guncellenecek.values()) + [rakip_id, tenant_id]
    with _conn() as conn:
        c = conn.execute(
            f"UPDATE tenant_competitors SET {set_clause} WHERE id = ? AND tenant_id = ?",
            degerler,
        )
    return c.rowcount > 0


def tenant_rakip_sil(rakip_id: int, tenant_id: int) -> bool:
    with _conn() as conn:
        c = conn.execute(
            "DELETE FROM tenant_competitors WHERE id = ? AND tenant_id = ?",
            (rakip_id, tenant_id),
        )
    return c.rowcount > 0


# ── Report Jobs CRUD ──────────────────────────────────────────────────────────

def report_job_olustur(tenant_id: int, gun: int, kapsam: str,
                        rakipler: list[str], mail_alicilari: list[str]) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO report_jobs
               (tenant_id, gun, kapsam, rakipler_json, mail_alicilari_json)
               VALUES (?, ?, ?, ?, ?)""",
            (tenant_id, gun, kapsam,
             json.dumps(rakipler, ensure_ascii=False),
             json.dumps(mail_alicilari, ensure_ascii=False)),
        )
        return cur.lastrowid


def report_job_guncelle(job_id: int, **kwargs) -> bool:
    izin_verilen = {"durum", "hata_mesaji", "rapor_id", "baslangic_at", "bitis_at"}
    guncellenecek = {k: v for k, v in kwargs.items() if k in izin_verilen}
    if not guncellenecek:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in guncellenecek)
    degerler = list(guncellenecek.values()) + [job_id]
    with _conn() as conn:
        c = conn.execute(
            f"UPDATE report_jobs SET {set_clause} WHERE id = ?", degerler
        )
    return c.rowcount > 0


def report_job_listele(tenant_id: int, limit: int = 50) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            """SELECT rj.*, r.dosya_yolu
               FROM report_jobs rj
               LEFT JOIN reports r ON rj.rapor_id = r.id
               WHERE rj.tenant_id = ?
               ORDER BY rj.id DESC
               LIMIT ?""",
            (tenant_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def report_job_sil(job_id: int, tenant_id: int) -> bool:
    with _conn() as conn:
        c = conn.execute(
            "DELETE FROM report_jobs WHERE id = ? AND tenant_id = ?",
            (job_id, tenant_id),
        )
    return c.rowcount > 0


def report_job_hatalilari_sil(tenant_id: int) -> int:
    """hata durumundaki ve 1 saatten uzun süredir kuyrukta takılı tüm job'ları siler."""
    esik = (datetime.now() - timedelta(hours=1)).isoformat()
    with _conn() as conn:
        c = conn.execute(
            """DELETE FROM report_jobs
               WHERE tenant_id = ?
               AND (durum = 'hata'
                    OR (durum = 'kuyrukta' AND olusturuldu_at < ?))""",
            (tenant_id, esik),
        )
    return c.rowcount


def report_job_al(job_id: int, tenant_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM report_jobs WHERE id = ? AND tenant_id = ?",
            (job_id, tenant_id),
        ).fetchone()
    return dict(row) if row else None


# ── Haber İstatistikleri (Timeline) ──────────────────────────────────────────

def haberler_donem_al(tenant_id: int, gun: int = 1, limit: int = 100) -> list[dict]:
    """Belirtilen dönemdeki (son {gun} gün) haberleri, en yeniden eskiye, listeler."""
    esik = (datetime.now() - timedelta(days=gun)).isoformat()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT id, baslik, url, kaynak, tarih, kategori
            FROM news
            WHERE tarih >= ? AND tenant_id = ?
            ORDER BY tarih DESC
            LIMIT ?
            """,
            (esik, tenant_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def haber_sayilari_donem_al(tenant_id: int, gunler: tuple[int, ...] = (1, 7, 30, 365)) -> dict[int, int]:
    """ULAK kartındaki dönem butonlarının yanında gösterilecek haber sayıları."""
    with _conn() as conn:
        sonuc: dict[int, int] = {}
        for gun in gunler:
            esik = (datetime.now() - timedelta(days=gun)).isoformat()
            sonuc[gun] = conn.execute(
                "SELECT COUNT(*) FROM news WHERE tarih >= ? AND tenant_id = ?",
                (esik, tenant_id),
            ).fetchone()[0]
    return sonuc


def haber_seri_al(tenant_id: int, gun: int = 30) -> list[dict]:
    """Günlük toplam ve olumsuz haber sayılarını döner (line chart için)."""
    esik = (datetime.now() - timedelta(days=gun)).isoformat()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT
                DATE(tarih) AS gun,
                COUNT(*) AS toplam,
                SUM(CASE WHEN sentiment = 'olumsuz' THEN 1 ELSE 0 END) AS olumsuz
            FROM news
            WHERE tarih >= ?
              AND tenant_id = ?
              AND tarih IS NOT NULL
            GROUP BY DATE(tarih)
            ORDER BY gun
            """,
            (esik, tenant_id),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Haber CRUD ────────────────────────────────────────────────────────────────

def haber_kaydet(haber, rapor_id: int | None = None, tenant_id: int = 1) -> bool:
    try:
        with _conn() as conn:
            conn.execute(
                """
                INSERT INTO news
                  (baslik, url, kaynak, tarih, dil, ai_ozet, sentiment, kategori, triples, rapor_id, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    haber.baslik,
                    haber.url,
                    haber.kaynak,
                    haber.tarih.isoformat() if haber.tarih else None,
                    haber.dil,
                    haber.ai_ozet,
                    haber.sentiment,
                    haber.kategori,
                    json.dumps(getattr(haber, "triples", []), ensure_ascii=False),
                    rapor_id,
                    tenant_id,
                ),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def rapor_kaydet(baslangic: datetime, bitis: datetime, haber_sayisi: int,
                  dosya_yolu: Path, tenant_id: int = 1) -> int:
    with _conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reports (baslangic_tarih, bitis_tarih, haber_sayisi, dosya_yolu, tenant_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (baslangic.isoformat(), bitis.isoformat(), haber_sayisi, str(dosya_yolu), tenant_id),
        )
        return cursor.lastrowid


def rapor_sil(rapor_id: int, tenant_id: int) -> bool:
    with _conn() as conn:
        c = conn.execute(
            "DELETE FROM reports WHERE id = ? AND tenant_id = ?",
            (rapor_id, tenant_id),
        )
    return c.rowcount > 0


def rapor_ad_guncelle(rapor_id: int, tenant_id: int, ad: str) -> bool:
    with _conn() as conn:
        c = conn.execute(
            "UPDATE reports SET ad = ? WHERE id = ? AND tenant_id = ?",
            (ad.strip(), rapor_id, tenant_id),
        )
    return c.rowcount > 0


def url_mevcut_mu(url: str) -> bool:
    with _conn() as conn:
        row = conn.execute("SELECT 1 FROM news WHERE url = ?", (url,)).fetchone()
        return row is not None


def sentiment_trend_al(hafta_sayisi: int = 4, tenant_id: int = 1) -> list[dict]:
    esik = (datetime.now() - timedelta(weeks=hafta_sayisi)).isoformat()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT strftime('%Y-W%W', tarih) AS hafta, sentiment, COUNT(*) AS sayi
            FROM news
            WHERE tarih >= ? AND sentiment IS NOT NULL AND tenant_id = ?
            GROUP BY hafta, sentiment
            ORDER BY hafta
            """,
            (esik, tenant_id),
        ).fetchall()
    return [dict(r) for r in rows]


def son_haberler_al(gun: int = 7, tenant_id: int = 1) -> list[dict]:
    esik = (datetime.now() - timedelta(days=gun)).isoformat()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT baslik, url, kaynak, tarih, dil, ai_ozet, sentiment, kategori
            FROM news
            WHERE tarih >= ? AND tenant_id = ?
            ORDER BY tarih DESC
            """,
            (esik, tenant_id),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Mail Listesi ──────────────────────────────────────────────────────────────

def mail_ekle(ad_soyad: str, email: str, rol: str = "izleyici",
              haftalik: bool = True, kriz: bool = True, hata: bool = False,
              tenant_id: int = 1) -> bool:
    try:
        with _conn() as conn:
            conn.execute(
                """INSERT INTO mail_listesi (ad_soyad, email, rol, haftalik, kriz, hata, tenant_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (ad_soyad, email.lower().strip(), rol,
                 int(haftalik), int(kriz), int(hata), tenant_id),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def mail_guncelle(email: str, tenant_id: int = 1, **kwargs) -> bool:
    izin_verilen = {"aktif", "haftalik", "kriz", "hata", "rol", "ad_soyad"}
    guncellenecek = {k: v for k, v in kwargs.items() if k in izin_verilen}
    if not guncellenecek:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in guncellenecek)
    degerler = list(guncellenecek.values()) + [email.lower().strip(), tenant_id]
    with _conn() as conn:
        c = conn.execute(
            f"UPDATE mail_listesi SET {set_clause} WHERE email = ? AND tenant_id = ?",
            degerler,
        )
    return c.rowcount > 0


def mail_sil(email: str, tenant_id: int = 1) -> bool:
    with _conn() as conn:
        c = conn.execute(
            "DELETE FROM mail_listesi WHERE email = ? AND tenant_id = ?",
            (email.lower().strip(), tenant_id),
        )
    return c.rowcount > 0


def mail_listesi_al(tur: str | None = None, tenant_id: int = 1) -> list[dict]:
    with _conn() as conn:
        if tur and tur in ("haftalik", "kriz", "hata"):
            rows = conn.execute(
                f"SELECT * FROM mail_listesi WHERE aktif = 1 AND tenant_id = ? AND {tur} = 1 ORDER BY ad_soyad",
                (tenant_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM mail_listesi WHERE aktif = 1 AND tenant_id = ? ORDER BY ad_soyad",
                (tenant_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def mail_listesi_tumu(tenant_id: int = 1) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM mail_listesi WHERE tenant_id = ? ORDER BY ad_soyad",
            (tenant_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Global Rakip CRUD (manuel katalog) ───────────────────────────────────────

def rakip_listesi_al(sadece_aktif: bool = True) -> list[dict]:
    """Global rakip kataloğunu döner — tüm tenantlar paylaşır."""
    with _conn() as conn:
        if sadece_aktif:
            rows = conn.execute(
                "SELECT * FROM rakipler WHERE aktif = 1 ORDER BY ad"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM rakipler ORDER BY aktif DESC, ad"
            ).fetchall()
    return [dict(r) for r in rows]


def rakip_ekle(ad: str, rss_sorgu: str, rss_dil: str, bolge: str,
               aciklama: str, ticker: str | None = None) -> bool:
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO rakipler (ad, rss_sorgu, rss_dil, ticker, bolge, aciklama) VALUES (?, ?, ?, ?, ?, ?)",
                (ad.strip(), rss_sorgu.strip(), rss_dil, ticker or None, bolge.strip(), aciklama.strip()),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def rakip_guncelle(rakip_id: int, **kwargs) -> bool:
    izin_verilen = {"ad", "rss_sorgu", "rss_dil", "ticker", "bolge", "aciklama", "aktif"}
    guncellenecek = {k: v for k, v in kwargs.items() if k in izin_verilen}
    if not guncellenecek:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in guncellenecek)
    degerler = list(guncellenecek.values()) + [rakip_id]
    with _conn() as conn:
        c = conn.execute(
            f"UPDATE rakipler SET {set_clause} WHERE id = ?", degerler
        )
    return c.rowcount > 0


def rakip_sil(rakip_id: int) -> bool:
    with _conn() as conn:
        c = conn.execute("DELETE FROM rakipler WHERE id = ?", (rakip_id,))
    return c.rowcount > 0


# ── LinkedIn Tags CRUD ────────────────────────────────────────────────────────

def linkedin_tag_listele(tenant_id: int, firma: str = "ULAK") -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM linkedin_tags WHERE tenant_id = ? AND firma = ? ORDER BY kaynak, tag",
            (tenant_id, firma),
        ).fetchall()
    return [dict(r) for r in rows]


def linkedin_tag_ekle(tenant_id: int, tag: str, aciklama: str = "",
                      kaynak: str = "manuel", secili: bool = True,
                      firma: str = "ULAK") -> dict | None:
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO linkedin_tags (tenant_id, tag, aciklama, kaynak, secili, firma) VALUES (?, ?, ?, ?, ?, ?)",
                (tenant_id, tag.strip(), aciklama.strip(), kaynak, int(secili), firma),
            )
        with _conn() as conn:
            row = conn.execute(
                "SELECT * FROM linkedin_tags WHERE tenant_id = ? AND tag = ? AND firma = ?",
                (tenant_id, tag.strip(), firma),
            ).fetchone()
        return dict(row) if row else None
    except sqlite3.IntegrityError:
        return None


def linkedin_tag_al(tag_id: int, tenant_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM linkedin_tags WHERE id = ? AND tenant_id = ?", (tag_id, tenant_id)
        ).fetchone()
    return dict(row) if row else None


def linkedin_tag_guncelle(tag_id: int, tenant_id: int, **kwargs) -> bool:
    izin = {"tag", "aciklama", "secili"}
    vals = {k: v for k, v in kwargs.items() if k in izin}
    if not vals:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in vals)
    degerler = list(vals.values()) + [tag_id, tenant_id]
    with _conn() as conn:
        c = conn.execute(
            f"UPDATE linkedin_tags SET {set_clause} WHERE id = ? AND tenant_id = ?", degerler
        )
    return c.rowcount > 0


def linkedin_tag_sil(tag_id: int, tenant_id: int) -> bool:
    with _conn() as conn:
        c = conn.execute(
            "DELETE FROM linkedin_tags WHERE id = ? AND tenant_id = ?", (tag_id, tenant_id)
        )
    return c.rowcount > 0


def linkedin_tag_toplu_sec(tenant_id: int, secili_idler: list[int], firma: str = "ULAK") -> None:
    """Verilen ID listesini seçili, geri kalanları seçilmemiş yapar (tek firma kapsamında)."""
    secili_set = set(secili_idler)
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id FROM linkedin_tags WHERE tenant_id = ? AND firma = ?", (tenant_id, firma)
        ).fetchall()
        for row in rows:
            yeni = 1 if row["id"] in secili_set else 0
            conn.execute(
                "UPDATE linkedin_tags SET secili = ? WHERE id = ?", (yeni, row["id"])
            )


# ── Yönetim Kurulu / Yönetim ────────────────────────────────────────────────────

def yonetim_listele(tenant_id: int = 1) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM yonetim_kisi WHERE tenant_id = ? AND aktif = 1 ORDER BY grup, id",
            (tenant_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def yonetim_degisiklikleri_al(tenant_id: int = 1, limit: int = 10) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM yonetim_degisiklik WHERE tenant_id = ? ORDER BY id DESC LIMIT ?",
            (tenant_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def yonetim_senkronize(tenant_id: int, cekilen: list) -> list[dict]:
    """
    Resmi siteden çekilen güncel kişi listesini DB'deki kayıtla karşılaştırır:
    yeni kişi ekler, unvan/foto değişikliklerini günceller, artık sitede
    olmayanları pasifleştirir. Her değişiklik yonetim_degisiklik tablosuna
    loglanır. Güncel (aktif) listeyi döner.
    """
    with _conn() as conn:
        # ust_kademe kişileri bu senkronizasyonun kapsamı dışında — resmi
        # sitede zaten yer almıyorlar (LLM/LinkedIn keşfi veya elle eklendiler),
        # bu yüzden karşılaştırma/pasifleştirme mantığına dahil edilmemeliler.
        mevcutlar = {
            (r["ad_soyad"], r["grup"]): dict(r)
            for r in conn.execute(
                "SELECT * FROM yonetim_kisi WHERE tenant_id = ? AND grup != 'ust_kademe'",
                (tenant_id,),
            ).fetchall()
        }

        gorulen_anahtarlar: set[tuple[str, str]] = set()

        for kisi in cekilen:
            anahtar = (kisi.ad_soyad, kisi.grup)
            gorulen_anahtarlar.add(anahtar)
            eski = mevcutlar.get(anahtar)

            if eski is None:
                conn.execute(
                    """INSERT INTO yonetim_kisi (tenant_id, ad_soyad, unvan, grup, foto_url, aktif)
                       VALUES (?, ?, ?, ?, ?, 1)""",
                    (tenant_id, kisi.ad_soyad, kisi.unvan, kisi.grup, kisi.foto_url),
                )
                conn.execute(
                    """INSERT INTO yonetim_degisiklik (tenant_id, ad_soyad, tur, detay)
                       VALUES (?, ?, 'eklendi', ?)""",
                    (tenant_id, kisi.ad_soyad, kisi.unvan),
                )
            else:
                guncellemeler = {}
                if eski["unvan"] != kisi.unvan:
                    guncellemeler["unvan"] = kisi.unvan
                    conn.execute(
                        """INSERT INTO yonetim_degisiklik (tenant_id, ad_soyad, tur, detay)
                           VALUES (?, ?, 'unvan_degisti', ?)""",
                        (tenant_id, kisi.ad_soyad, f"{eski['unvan']} → {kisi.unvan}"),
                    )
                if eski["foto_url"] != kisi.foto_url:
                    guncellemeler["foto_url"] = kisi.foto_url
                if not eski["aktif"]:
                    guncellemeler["aktif"] = 1
                    conn.execute(
                        """INSERT INTO yonetim_degisiklik (tenant_id, ad_soyad, tur, detay)
                           VALUES (?, ?, 'eklendi', ?)""",
                        (tenant_id, kisi.ad_soyad, kisi.unvan),
                    )
                if guncellemeler:
                    guncellemeler["guncellendi_at"] = datetime.now().isoformat()
                    set_clause = ", ".join(f"{k} = ?" for k in guncellemeler)
                    conn.execute(
                        f"UPDATE yonetim_kisi SET {set_clause} WHERE id = ?",
                        (*guncellemeler.values(), eski["id"]),
                    )

        # Sitede artık görünmeyen ama DB'de aktif olan kişileri pasifleştir
        for anahtar, eski in mevcutlar.items():
            if anahtar not in gorulen_anahtarlar and eski["aktif"]:
                conn.execute("UPDATE yonetim_kisi SET aktif = 0 WHERE id = ?", (eski["id"],))
                conn.execute(
                    """INSERT INTO yonetim_degisiklik (tenant_id, ad_soyad, tur, detay)
                       VALUES (?, ?, 'ayrildi', ?)""",
                    (tenant_id, eski["ad_soyad"], eski["unvan"]),
                )

    return yonetim_listele(tenant_id)


def ust_kademe_ekle(tenant_id: int, ad_soyad: str, unvan: str, linkedin_url: str = "") -> bool:
    """
    LLM/LinkedIn keşfiyle bulunan üst kademe çalışanı ekler. Zaten varsa
    (büyük/küçük harf veya boşluk farkı gözetmeksizin — LLM aynı kişiyi farklı
    yazımla çıkarabiliyor) sessizce geçer.
    """
    normalize = lambda s: " ".join(s.split()).lower()
    with _conn() as conn:
        mevcutlar = conn.execute(
            "SELECT ad_soyad FROM yonetim_kisi WHERE tenant_id = ? AND grup = 'ust_kademe'",
            (tenant_id,),
        ).fetchall()
        if any(normalize(r["ad_soyad"]) == normalize(ad_soyad) for r in mevcutlar):
            return False
        try:
            conn.execute(
                """INSERT INTO yonetim_kisi
                   (tenant_id, ad_soyad, unvan, grup, linkedin_url, kaynak, aktif)
                   VALUES (?, ?, ?, 'ust_kademe', ?, 'linkedin', 1)""",
                (tenant_id, ad_soyad, unvan, linkedin_url),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def yonetim_foto_guncelle(kisi_id: int, tenant_id: int, foto_url: str) -> bool:
    with _conn() as conn:
        c = conn.execute(
            "UPDATE yonetim_kisi SET foto_url = ? WHERE id = ? AND tenant_id = ?",
            (foto_url, kisi_id, tenant_id),
        )
    return c.rowcount > 0


def ust_kademe_sil(kisi_id: int, tenant_id: int) -> bool:
    with _conn() as conn:
        c = conn.execute(
            "DELETE FROM yonetim_kisi WHERE id = ? AND tenant_id = ? AND grup = 'ust_kademe'",
            (kisi_id, tenant_id),
        )
    return c.rowcount > 0


# ── Ayarlar ───────────────────────────────────────────────────────────────────

def ayar_al(anahtar: str, varsayilan: str = "") -> str:
    with _conn() as conn:
        row = conn.execute(
            "SELECT deger FROM ayarlar WHERE anahtar = ?", (anahtar,)
        ).fetchone()
    return row["deger"] if row else varsayilan


def ayar_guncelle(anahtar: str, deger: str) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO ayarlar (anahtar, deger) VALUES (?, ?)
               ON CONFLICT(anahtar) DO UPDATE SET deger = excluded.deger""",
            (anahtar, deger),
        )


# ── Stats (Dashboard) ─────────────────────────────────────────────────────────

def istatistik_al(tenant_id: int, gun: int = 7) -> dict:
    esik = (datetime.now() - timedelta(days=gun)).isoformat()
    with _conn() as conn:
        toplam = conn.execute(
            "SELECT COUNT(*) FROM news WHERE tarih >= ? AND tenant_id = ?",
            (esik, tenant_id),
        ).fetchone()[0]

    return {"toplam_haber": toplam}
