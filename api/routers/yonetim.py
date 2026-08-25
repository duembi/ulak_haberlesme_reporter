"""Yönetim Kurulu / Yönetim / Üst Kademe takibi — resmi site senkronizasyonu,
LinkedIn keşfi ve kişi bazlı haber + LinkedIn takibi."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.deps import get_current_user
from src.database import (
    yonetim_listele, yonetim_degisiklikleri_al, yonetim_senkronize,
    ust_kademe_ekle,
)

router = APIRouter()

_CACHE_SN = 1800  # 30 dakika
_cache: dict = {"zaman": None, "veri": None}


class YonetimKisiYanit(BaseModel):
    id: int
    tenant_id: int
    ad_soyad: str
    unvan: str
    grup: str
    foto_url: str
    linkedin_url: Optional[str] = None
    kaynak: str
    aktif: bool
    olusturuldu_at: str
    guncellendi_at: str


class DegisiklikYanit(BaseModel):
    id: int
    ad_soyad: str
    tur: str
    detay: str
    tarih: str


class HaberOgesi(BaseModel):
    baslik: str
    url: str
    kaynak: str
    tarih: Optional[str] = None


class LinkedInOgesi(BaseModel):
    baslik: str
    ozet: str
    url: str
    tag: Optional[str] = None


class KisiSonucYanit(BaseModel):
    haberler: list[HaberOgesi]
    linkedin: list[LinkedInOgesi]


def _senkronize_et(tenant_id: int) -> list[dict]:
    from src.yonetim_scraper import yonetim_kisilerini_cek
    cekilen = yonetim_kisilerini_cek()
    return yonetim_senkronize(tenant_id, cekilen)


@router.get("/", response_model=list[YonetimKisiYanit])
async def listele(user: dict = Depends(get_current_user)):
    """
    Yönetim Kurulu + Yönetim + Üst Kademe listesini döner. Resmi site
    ~30 dakikada bir yeniden taranır (senkron/bloklayıcı olduğundan
    `asyncio.to_thread`'e atılır); üst kademe kişiler bu senkronizasyondan
    etkilenmez, ayrı yönetilir.
    """
    tenant_id = user["tenant_id"]
    simdi = datetime.now()

    onbellek_zaman = _cache["zaman"]
    if onbellek_zaman and (simdi - onbellek_zaman).total_seconds() < _CACHE_SN:
        return _cache["veri"]

    import asyncio
    veri = await asyncio.to_thread(_senkronize_et, tenant_id)
    _cache["zaman"] = simdi
    _cache["veri"] = veri
    return veri


@router.post("/senkronize", response_model=list[YonetimKisiYanit])
async def manuel_senkronize(user: dict = Depends(get_current_user)):
    """Resmi siteyi hemen yeniden tarar (önbelleği atlar)."""
    import asyncio
    tenant_id = user["tenant_id"]
    veri = await asyncio.to_thread(_senkronize_et, tenant_id)
    _cache["zaman"] = datetime.now()
    _cache["veri"] = veri
    return veri


@router.get("/degisiklikler", response_model=list[DegisiklikYanit])
async def degisiklikler(user: dict = Depends(get_current_user)):
    return yonetim_degisiklikleri_al(user["tenant_id"], limit=10)


@router.post("/ust-kademe/kesif", response_model=list[YonetimKisiYanit])
async def ust_kademe_kesfet(user: dict = Depends(get_current_user)):
    """
    LinkedIn'de "Ulak Haberleşme"de Direktör/Müdür unvanlı profilleri arar
    (LLM ile ham sonuçları doğrulayarak), yeni bulunanları üst kademe
    listesine ekler.
    """
    from src.linkedin_tracker import ust_kademe_kesif
    tenant_id = user["tenant_id"]

    bulunanlar = await ust_kademe_kesif(tenant_id)
    for kisi in bulunanlar:
        ust_kademe_ekle(
            tenant_id=tenant_id,
            ad_soyad=kisi["ad_soyad"],
            unvan=kisi["unvan"],
            linkedin_url=kisi.get("linkedin_url", ""),
        )

    _cache["zaman"] = None  # bir sonraki listele çağrısında güncel veri gelsin
    return yonetim_listele(tenant_id)


@router.delete("/ust-kademe/{kisi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def ust_kademe_kaldir(kisi_id: int, user: dict = Depends(get_current_user)):
    from src.database import ust_kademe_sil
    ok = ust_kademe_sil(kisi_id, user["tenant_id"])
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kişi bulunamadı")
    _cache["zaman"] = None


@router.get("/{kisi_id}/haberler", response_model=KisiSonucYanit)
async def kisi_haberleri(kisi_id: int, gun: int = 180, user: dict = Depends(get_current_user)):
    """
    Bir kişi için hem Google News'te isim bazlı haber araması hem de LinkedIn
    paylaşım araması yapar (ikisi de relevans doğrulamasından geçer — anahtar
    kelime + LLM teyidi). Kişinin seçili LinkedIn tag'i yoksa otomatik üretilir.
    """
    kisiler = yonetim_listele(user["tenant_id"])
    kisi = next((k for k in kisiler if k["id"] == kisi_id), None)
    if not kisi:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kişi bulunamadı")

    import asyncio
    from src.competitor_tracker import tenant_rakip_haberleri_cek
    from src.linkedin_tracker import firma_linkedin_tagleri_ve_gonderileri

    ad_soyad = kisi["ad_soyad"]
    haber_gorevi = asyncio.to_thread(tenant_rakip_haberleri_cek, [ad_soyad], gun, 10)
    linkedin_gorevi = firma_linkedin_tagleri_ve_gonderileri(
        user["tenant_id"], ad_soyad, ad_soyad, gun=gun,
    )
    haber_sonuc, linkedin_sonuc = await asyncio.gather(haber_gorevi, linkedin_gorevi)

    return KisiSonucYanit(
        haberler=haber_sonuc.get(ad_soyad, []),
        linkedin=linkedin_sonuc,
    )
