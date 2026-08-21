from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_current_user
from api.routers import (
    auth, mail, reports, pipeline, settings,
    linkedin, competitors,
)
from api.routers import llm_configs, tenant_competitors, report_jobs
from api.schemas import IstatistikYanit
from src.database import init_db, istatistik_al, haber_seri_al

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
app.include_router(mail.router,               prefix="/api/mail",              tags=["Mail"])
app.include_router(reports.router,            prefix="/api/reports",           tags=["Raporlar"])
app.include_router(pipeline.router,           prefix="/api/pipeline",          tags=["Pipeline"])
app.include_router(settings.router,           prefix="/api/settings",          tags=["Ayarlar"])
app.include_router(linkedin.router,           prefix="/api/linkedin",          tags=["LinkedIn"])
app.include_router(competitors.router,        prefix="/api/competitors",       tags=["Rakipler"])
app.include_router(llm_configs.router,        prefix="/api/llm-configs",       tags=["LLM Configs"])
app.include_router(tenant_competitors.router, prefix="/api/tenant-competitors",tags=["Tenant Rakipleri"])
app.include_router(report_jobs.router,        prefix="/api/report-jobs",       tags=["Rapor İşleri"])


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/api/stats", response_model=IstatistikYanit, tags=["Stats"])
async def istatistikler(user: dict = Depends(get_current_user)):
    return istatistik_al(tenant_id=user["tenant_id"], gun=7)


@app.get("/api/stats/timeline", tags=["Stats"])
async def timeline(gun: int = 30, user: dict = Depends(get_current_user)):
    """Günlük toplam + olumsuz haber sayısı (line chart için)."""
    return haber_seri_al(tenant_id=user["tenant_id"], gun=gun)


@app.get("/api/health", tags=["Health"])
async def health():
    from datetime import datetime
    return {"durum": "ok", "versiyon": "2.0.0", "zaman": datetime.now().isoformat()}
