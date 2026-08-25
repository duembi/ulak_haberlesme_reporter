from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_current_user
from api.routers import auth, pipeline, competitors, tenant_competitors, yonetim
from api.schemas import IstatistikYanit
from src.database import init_db, istatistik_al, haber_seri_al, haberler_donem_al, haber_sayilari_donem_al
from src.competitor_tracker import rakip_kart_sayilari, rakip_kart_haberleri, DASHBOARD_FIRMALARI

app = FastAPI(
    title="Medya İstihbarat API",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()


# ── Auth (public) ─────────────────────────────────────────────────────────────
app.include_router(auth.router,               prefix="/api/auth",              tags=["Auth"])

# ── Protected ─────────────────────────────────────────────────────────────────
app.include_router(pipeline.router,           prefix="/api/pipeline",          tags=["Pipeline"])
app.include_router(competitors.router,        prefix="/api/competitors",       tags=["Rakipler"])
app.include_router(tenant_competitors.router, prefix="/api/tenant-competitors",tags=["Tenant Rakipleri"])
app.include_router(yonetim.router,            prefix="/api/yonetim",           tags=["Yönetim"])


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/api/stats", response_model=IstatistikYanit, tags=["Stats"])
async def istatistikler(user: dict = Depends(get_current_user)):
    return istatistik_al(tenant_id=user["tenant_id"], gun=7)


@app.get("/api/stats/timeline", tags=["Stats"])
async def timeline(gun: int = 30, user: dict = Depends(get_current_user)):
    """Günlük toplam + olumsuz haber sayısı (line chart için)."""
    return haber_seri_al(tenant_id=user["tenant_id"], gun=gun)


@app.get("/api/stats/news", tags=["Stats"])
async def stats_haberler(gun: int = 1, user: dict = Depends(get_current_user)):
    """Belirtilen dönemdeki (Bugün=1, Bu Hafta=7, Bu Ay=30, Bu Sene=365) haberler."""
    return haberler_donem_al(tenant_id=user["tenant_id"], gun=gun)


@app.get("/api/stats/news-counts", tags=["Stats"])
async def stats_haber_sayilari(user: dict = Depends(get_current_user)):
    """ULAK kartındaki Bugün/Bu Hafta/Bu Ay/Bu Sene butonlarının yanındaki sayılar."""
    return haber_sayilari_donem_al(tenant_id=user["tenant_id"])


@app.get("/api/stats/rakip-kartlar", tags=["Stats"])
def stats_rakip_kartlari(user: dict = Depends(get_current_user)):
    """
    Dashboard'daki sabit 4 firma kartı (ASELSAN, SSB, SSTEK, Havelsan) için
    dönem bazlı haber sayıları. Senkron/bloklayıcı (RSS + XML parse) olduğundan
    bilerek `def` (async değil) tanımlandı — FastAPI otomatik thread pool'a atar.
    """
    return rakip_kart_sayilari()


@app.get("/api/stats/rakip-haberler", tags=["Stats"])
def stats_rakip_haberleri(firma: str, gun: int = 7, user: dict = Depends(get_current_user)):
    """Dashboard'daki sabit bir firma kartı için belirtilen dönemdeki haberler."""
    if firma not in DASHBOARD_FIRMALARI:
        raise HTTPException(404, detail="Bilinmeyen firma")
    return rakip_kart_haberleri(firma, gun)


@app.get("/api/stats/linkedin", tags=["Stats"])
async def stats_linkedin(firma: str, gun: int = 30, user: dict = Depends(get_current_user)):
    """
    Dashboard'daki bir firma kartı (ULAK dahil) için LinkedIn paylaşımlarını getirir.
    Firmanın seçili LinkedIn tag'i yoksa LLM ile otomatik üretilir.
    """
    if firma != "ULAK" and firma not in DASHBOARD_FIRMALARI:
        raise HTTPException(404, detail="Bilinmeyen firma")
    ad_gorunen = "Ulak Haberleşme" if firma == "ULAK" else DASHBOARD_FIRMALARI[firma]
    from src.linkedin_tracker import firma_linkedin_tagleri_ve_gonderileri
    return await firma_linkedin_tagleri_ve_gonderileri(user["tenant_id"], firma, ad_gorunen, gun=gun)


@app.get("/api/health", tags=["Health"])
async def health():
    from datetime import datetime
    return {"durum": "ok", "versiyon": "2.0.0", "zaman": datetime.now().isoformat()}
