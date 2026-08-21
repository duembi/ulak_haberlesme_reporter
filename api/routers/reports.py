import re
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from api.deps import get_current_user
from api.schemas import RaporYanit
from config.settings import RESEND_API_KEY
from src.database import DB_PATH, rapor_sil, rapor_ad_guncelle
from src.email_sender import rapor_tekil_gonder

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RaporAdGuncelle(BaseModel):
    ad: str


class RaporGonder(BaseModel):
    emails: list[str]
    mesaj: str = ""

    @field_validator("emails")
    @classmethod
    def emails_gecerli(cls, v: list[str]) -> list[str]:
        temiz = [e.strip().lower() for e in v if e.strip()]
        if not temiz:
            raise ValueError("En az bir e-posta adresi girin")
        gecersiz = [e for e in temiz if not _EMAIL_RE.match(e)]
        if gecersiz:
            raise ValueError(f"Geçersiz e-posta adresi: {', '.join(gecersiz)}")
        return temiz


def _raporlari_cek(tenant_id: int, limit: int, offset: int) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, ad, olusturuldu_at, baslangic_tarih, bitis_tarih,
                   haber_sayisi, dosya_yolu
            FROM reports
            WHERE tenant_id = ?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (tenant_id, limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/", response_model=list[RaporYanit])
async def rapor_listele(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    raporlar = _raporlari_cek(user["tenant_id"], limit, offset)
    return [
        {**r, "dosya_var": bool(r["dosya_yolu"] and Path(r["dosya_yolu"]).exists())}
        for r in raporlar
    ]


@router.patch("/{rapor_id}", response_model=RaporYanit)
async def rapor_ad_guncelle_endpoint(
    rapor_id: int,
    data: RaporAdGuncelle,
    user: dict = Depends(get_current_user),
):
    if not data.ad.strip():
        raise HTTPException(400, detail="Rapor adı boş olamaz")
    if not rapor_ad_guncelle(rapor_id, user["tenant_id"], data.ad):
        raise HTTPException(404, detail="Rapor bulunamadı")
    raporlar = _raporlari_cek(user["tenant_id"], 1, 0)
    # fetch the specific record
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, ad, olusturuldu_at, baslangic_tarih, bitis_tarih, haber_sayisi, dosya_yolu FROM reports WHERE id = ? AND tenant_id = ?",
            (rapor_id, user["tenant_id"]),
        ).fetchone()
    if not row:
        raise HTTPException(404, detail="Rapor bulunamadı")
    r = dict(row)
    return {**r, "dosya_var": bool(r["dosya_yolu"] and Path(r["dosya_yolu"]).exists())}


@router.delete("/{rapor_id}", status_code=204)
async def rapor_sil_endpoint(rapor_id: int, user: dict = Depends(get_current_user)):
    if not rapor_sil(rapor_id, user["tenant_id"]):
        raise HTTPException(404, detail="Rapor bulunamadı")


@router.get("/{rapor_id}/view")
async def rapor_goruntule(rapor_id: int, user: dict = Depends(get_current_user)):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT dosya_yolu FROM reports WHERE id = ? AND tenant_id = ?",
            (rapor_id, user["tenant_id"]),
        ).fetchone()
    if not row:
        raise HTTPException(404, detail="Rapor bulunamadı")
    yol = Path(row["dosya_yolu"]) if row["dosya_yolu"] else None
    if not yol or not yol.exists():
        raise HTTPException(404, detail="PDF dosyası mevcut değil")
    return FileResponse(path=str(yol), media_type="application/pdf",
                        content_disposition_type="inline")


@router.post("/{rapor_id}/send", status_code=200)
async def rapor_gonder_endpoint(
    rapor_id: int,
    data: RaporGonder,
    user: dict = Depends(get_current_user),
):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT ad, olusturuldu_at, dosya_yolu FROM reports WHERE id = ? AND tenant_id = ?",
            (rapor_id, user["tenant_id"]),
        ).fetchone()
    if not row:
        raise HTTPException(404, detail="Rapor bulunamadı")

    if not RESEND_API_KEY:
        raise HTTPException(
            400,
            detail="E-posta gönderimi yapılandırılmamış — .env dosyasında RESEND_API_KEY tanımlanmalı",
        )

    yol = Path(row["dosya_yolu"]) if row["dosya_yolu"] else None
    if not yol or not yol.exists():
        raise HTTPException(404, detail="PDF dosyası mevcut değil")

    rapor_adi = row["ad"] or row["olusturuldu_at"]
    basarili = rapor_tekil_gonder(yol, data.emails, rapor_adi, data.mesaj)
    if not basarili:
        raise HTTPException(500, detail="E-posta gönderilemedi, lütfen tekrar deneyin")

    return {"gonderildi": True, "alicilar": data.emails}


@router.get("/{rapor_id}/download")
async def rapor_indir(rapor_id: int, user: dict = Depends(get_current_user)):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT dosya_yolu FROM reports WHERE id = ? AND tenant_id = ?",
            (rapor_id, user["tenant_id"]),
        ).fetchone()

    if not row:
        raise HTTPException(404, detail="Rapor bulunamadı")
    yol = Path(row["dosya_yolu"]) if row["dosya_yolu"] else None
    if not yol or not yol.exists():
        raise HTTPException(404, detail="PDF dosyası mevcut değil")
    return FileResponse(path=str(yol), media_type="application/pdf", filename=yol.name)
