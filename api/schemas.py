from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr


# ── Mail ─────────────────────────────────────────────────────────────────────

class AliciOlustur(BaseModel):
    ad_soyad: str
    email: str
    rol: Literal["yonetici", "izleyici", "teknik"] = "izleyici"
    haftalik: bool = True
    kriz: bool = True
    hata: bool = False


class AliciGuncelle(BaseModel):
    aktif: Optional[bool] = None
    rol: Optional[Literal["yonetici", "izleyici", "teknik"]] = None
    haftalik: Optional[bool] = None
    kriz: Optional[bool] = None
    hata: Optional[bool] = None


class AliciYanit(BaseModel):
    id: int
    ad_soyad: str
    email: str
    rol: str
    haftalik: bool
    kriz: bool
    hata: bool
    aktif: bool
    eklendi_at: str


# ── Reports ───────────────────────────────────────────────────────────────────

class RaporYanit(BaseModel):
    id: int
    ad: Optional[str] = None
    olusturuldu_at: str
    baslangic_tarih: Optional[str] = None
    bitis_tarih: Optional[str] = None
    haber_sayisi: Optional[int] = None
    dosya_yolu: Optional[str] = None
    dosya_var: bool = False


# ── Stats ─────────────────────────────────────────────────────────────────────

class IstatistikYanit(BaseModel):
    toplam_haber: int
    olumlu: int
    olumsuz: int
    notr: int
    son_rapor_tarihi: Optional[str] = None
    toplam_rapor: int
    aktif_alici: int


# ── Competitor ────────────────────────────────────────────────────────────────

class RakipYanit(BaseModel):
    ad: str
    bolge: str
    aciklama: str
    ticker: Optional[str] = None
    kategori: str


# ── Settings ─────────────────────────────────────────────────────────────────

class ModelAyar(BaseModel):
    model: str


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
    rakipler: Optional[list[str]] = None


class PipelineDurumu(BaseModel):
    calisiyor: bool
    baslangic_zamani: Optional[str] = None
    bitis_zamani: Optional[str] = None
    sonuc: Optional[str] = None
    hata: Optional[str] = None
