from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr


# ── Stats ─────────────────────────────────────────────────────────────────────

class IstatistikYanit(BaseModel):
    toplam_haber: int


# ── Rakip ────────────────────────────────────────────────────────────────────

class RakipOlustur(BaseModel):
    ad: str
    rss_sorgu: str
    rss_dil: Literal["tr", "en"] = "en"
    ticker: Optional[str] = None
    bolge: str
    aciklama: str = ""


class RakipGuncelle(BaseModel):
    ad: Optional[str] = None
    rss_sorgu: Optional[str] = None
    rss_dil: Optional[Literal["tr", "en"]] = None
    ticker: Optional[str] = None
    bolge: Optional[str] = None
    aciklama: Optional[str] = None
    aktif: Optional[bool] = None


class RakipTamYanit(BaseModel):
    id: int
    ad: str
    rss_sorgu: str
    rss_dil: str
    ticker: Optional[str] = None
    bolge: str
    aciklama: str
    aktif: bool
    eklendi_at: str


# ── Pipeline ──────────────────────────────────────────────────────────────────

class PipelineIstek(BaseModel):
    gun: int = 7


class PipelineDurumu(BaseModel):
    calisiyor: bool
    baslangic_zamani: Optional[str] = None
    bitis_zamani: Optional[str] = None
    sonuc: Optional[str] = None
    hata: Optional[str] = None
