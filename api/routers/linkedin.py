"""LinkedIn hashtag / keyword yönetimi — tenant izolasyonlu, LLM destekli."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.deps import get_current_user
from src.database import (
    tenant_al,
    linkedin_tag_listele,
    linkedin_tag_ekle,
    linkedin_tag_guncelle,
    linkedin_tag_sil,
    linkedin_tag_toplu_sec,
)
from src.llm_providers import LLMFactory

router = APIRouter()

_SYSTEM = (
    "Sen bir sosyal medya ve pazar araştırması uzmanısın. "
    "LinkedIn'de takip edilecek anahtar kelimeleri ve hashtag'leri belirliyorsun. "
    "Yanıtlarını daima geçerli JSON formatında ver, başka metin ekleme."
)

_PROMPT = """
Aşağıdaki firma için LinkedIn'de takip edilmesi gereken hashtag ve anahtar kelimeleri belirle:

Firma domain: {domain}
Firma adı: {ad}

Görev: Bu firmanın sektörü, rakipleri, ürünleri ve iş alanlarıyla ilgili
LinkedIn'de takip edilecek 20-30 hashtag/keyword üret.

Kategorilere göre grupla. Örnek kategoriler: Kurumsal, Sektör, Teknoloji,
Kariyer, Rakipler, Ürünler & Hizmetler (firma sektörüne göre değiştir).

Her tag için:
- tag: # ile başlayan hashtag veya arama terimi
- aciklama: Neden takip edilmeli (kısa, Türkçe)
- kategori: Hangi kategoriye ait

Yanıtı SADECE şu JSON formatında ver:
{{
  "tagler": [
    {{"tag": "#Örnek", "aciklama": "...", "kategori": "Kurumsal"}}
  ]
}}
"""


# ── Schemas ───────────────────────────────────────────────────────────────────

class TagEkle(BaseModel):
    tag: str
    aciklama: str = ""


class TagGuncelle(BaseModel):
    secili: Optional[bool] = None
    aciklama: Optional[str] = None


class TopluSecim(BaseModel):
    secili_idler: list[int]


class TagYanit(BaseModel):
    id: int
    tenant_id: int
    tag: str
    aciklama: str
    kaynak: str
    secili: bool
    olusturuldu_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/tags", response_model=list[TagYanit])
async def tagleri_getir(user: dict = Depends(get_current_user)):
    return linkedin_tag_listele(user["tenant_id"])


@router.post("/tags/generate", response_model=list[TagYanit])
async def tagleri_uret(user: dict = Depends(get_current_user)):
    """LLM ile tenant domain'inden otomatik LinkedIn tagları üretir."""
    tenant_id = user["tenant_id"]
    tenant = tenant_al(tenant_id)
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant bulunamadı")

    try:
        llm = await LLMFactory.for_tenant(tenant_id)
        prompt = _PROMPT.format(domain=tenant["domain"], ad=tenant["ad"])
        yanit = await llm.generate_text(prompt, system_prompt=_SYSTEM)
    except Exception as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"LLM bağlantısı başarısız: {e}")

    try:
        baslangic = yanit.find("{")
        bitis = yanit.rfind("}") + 1
        if baslangic == -1 or bitis == 0:
            raise ValueError("JSON bulunamadı")
        veri = json.loads(yanit[baslangic:bitis])
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            detail="LLM geçersiz JSON döndürdü")

    for item in veri.get("tagler", []):
        tag = (item.get("tag") or "").strip()
        if not tag:
            continue
        aciklama = (item.get("aciklama") or "").strip()
        linkedin_tag_ekle(
            tenant_id=tenant_id,
            tag=tag,
            aciklama=aciklama,
            kaynak="ai",
            secili=True,
        )

    return linkedin_tag_listele(tenant_id)


@router.post("/tags", response_model=TagYanit, status_code=status.HTTP_201_CREATED)
async def tag_ekle(data: TagEkle, user: dict = Depends(get_current_user)):
    tag = data.tag.strip()
    if not tag:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Tag boş olamaz")
    if not tag.startswith("#"):
        tag = f"#{tag}"
    yeni = linkedin_tag_ekle(
        tenant_id=user["tenant_id"],
        tag=tag,
        aciklama=data.aciklama,
        kaynak="manuel",
        secili=True,
    )
    if yeni is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Bu tag zaten mevcut")
    return yeni


@router.patch("/tags/{tag_id}", response_model=TagYanit)
async def tag_guncelle(tag_id: int, data: TagGuncelle,
                        user: dict = Depends(get_current_user)):
    kwargs = {}
    if data.secili is not None:
        kwargs["secili"] = int(data.secili)
    if data.aciklama is not None:
        kwargs["aciklama"] = data.aciklama
    if not kwargs:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="En az bir alan gerekli")
    ok = linkedin_tag_guncelle(tag_id, user["tenant_id"], **kwargs)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tag bulunamadı")
    rows = linkedin_tag_listele(user["tenant_id"])
    row = next((r for r in rows if r["id"] == tag_id), None)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tag bulunamadı")
    return row


@router.post("/tags/batch-select", response_model=list[TagYanit])
async def toplu_sec(data: TopluSecim, user: dict = Depends(get_current_user)):
    linkedin_tag_toplu_sec(user["tenant_id"], data.secili_idler)
    return linkedin_tag_listele(user["tenant_id"])


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def tag_sil(tag_id: int, user: dict = Depends(get_current_user)):
    ok = linkedin_tag_sil(tag_id, user["tenant_id"])
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tag bulunamadı")
