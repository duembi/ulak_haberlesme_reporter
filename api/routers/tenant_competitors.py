"""Tenant rakip analizi — AI destekli otomatik keşif + CRUD."""
import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from api.deps import get_current_user
from src.database import (
    tenant_al, tenant_rakip_ekle, tenant_rakip_guncelle,
    tenant_rakip_listele, tenant_rakip_sil,
)
from src.llm_providers import LLMFactory

router = APIRouter()

_ANALIZ_SYSTEM = (
    "Sen bir pazar araştırması uzmanısın. "
    "Verilen firma ve sektör bilgisine göre yerli ve yabancı rakipleri analiz edersin. "
    "Yanıtlarını daima geçerli JSON formatında ver."
)

_ANALIZ_PROMPT = """
Aşağıdaki firmayı analiz et ve rakiplerini belirle:

Firma domain: {domain}
Firma adı: {ad}
Sektör notu: {sektor}

Görev: Bu firmanın en önemli 10-15 rakibini listele.
Her rakip için şu alanları doldur:
- ad: Rakip firma adı
- aciklama: Neden rakip olduğunu 1-2 cümleyle açıkla
- bolge: Firmanın bulunduğu ülke/bölge
- sektor: Hangi alt sektörde rekabet ediyor

Yanıtı SADECE bu JSON formatında ver (başka metin ekleme):
{{
  "rakipler": [
    {{"ad": "...", "aciklama": "...", "bolge": "...", "sektor": "..."}}
  ]
}}
"""


async def _ai_rakip_analizi(tenant_id: int, domain: str, ad: str, sektor: str = ""):
    """Arka planda çalışır; AI ile rakipleri analiz edip DB'ye kaydeder."""
    try:
        llm = await LLMFactory.for_tenant(tenant_id)
        prompt = _ANALIZ_PROMPT.format(domain=domain, ad=ad, sektor=sektor or "belirtilmedi")
        yanit = await llm.generate_text(prompt, system_prompt=_ANALIZ_SYSTEM)

        # JSON bloğunu ayıkla
        baslangic = yanit.find("{")
        bitis = yanit.rfind("}") + 1
        if baslangic == -1 or bitis == 0:
            return
        veri = json.loads(yanit[baslangic:bitis])

        for r in veri.get("rakipler", []):
            tenant_rakip_ekle(
                tenant_id=tenant_id,
                ad=r.get("ad", "").strip(),
                aciklama=r.get("aciklama", ""),
                bolge=r.get("bolge", ""),
                sektor=r.get("sektor", ""),
                ai_onerisi=True,
            )
    except Exception:
        pass  # Analiz başarısız → sessizce geç


# ── Schemas ───────────────────────────────────────────────────────────────────

class TenantRakipOlustur(BaseModel):
    ad: str
    aciklama: str = ""
    bolge: str = ""
    sektor: str = ""


class TenantRakipGuncelle(BaseModel):
    ad: Optional[str] = None
    aciklama: Optional[str] = None
    bolge: Optional[str] = None
    sektor: Optional[str] = None
    aktif: Optional[bool] = None


class TenantRakipYanit(BaseModel):
    id: int
    tenant_id: int
    ad: str
    aciklama: str
    bolge: str
    sektor: str
    aktif: bool
    ai_onerisi: bool
    olusturuldu_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[TenantRakipYanit])
async def listele(sadece_aktif: bool = True, user: dict = Depends(get_current_user)):
    return tenant_rakip_listele(user["tenant_id"], sadece_aktif=sadece_aktif)


@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analiz_baslat(
    background_tasks: BackgroundTasks,
    sektor: str = "",
    user: dict = Depends(get_current_user),
):
    """AI ile rakip analizini arka planda başlatır."""
    tenant = tenant_al(user["tenant_id"])
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant bulunamadı")

    background_tasks.add_task(
        _ai_rakip_analizi,
        user["tenant_id"],
        tenant["domain"],
        tenant["ad"],
        sektor,
    )
    return {"mesaj": "Rakip analizi başlatıldı. Birkaç saniye içinde rakipler listelenecek."}


@router.post("/", response_model=TenantRakipYanit, status_code=status.HTTP_201_CREATED)
async def ekle(data: TenantRakipOlustur, user: dict = Depends(get_current_user)):
    ok = tenant_rakip_ekle(
        tenant_id=user["tenant_id"],
        ad=data.ad,
        aciklama=data.aciklama,
        bolge=data.bolge,
        sektor=data.sektor,
        ai_onerisi=False,
    )
    if not ok:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Bu isimde rakip zaten mevcut")
    rakipler = tenant_rakip_listele(user["tenant_id"], sadece_aktif=False)
    yeni = next((r for r in rakipler if r["ad"] == data.ad.strip()), None)
    if not yeni:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Kayıt oluşturulamadı")
    return yeni


@router.patch("/{rakip_id}", response_model=TenantRakipYanit)
async def guncelle(rakip_id: int, data: TenantRakipGuncelle,
                   user: dict = Depends(get_current_user)):
    guncellemeler = data.model_dump(exclude_none=True)
    if not guncellemeler:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="En az bir alan gerekli")
    if "aktif" in guncellemeler:
        guncellemeler["aktif"] = int(guncellemeler["aktif"])
    ok = tenant_rakip_guncelle(rakip_id, user["tenant_id"], **guncellemeler)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rakip bulunamadı")
    rakipler = tenant_rakip_listele(user["tenant_id"], sadece_aktif=False)
    guncellendi = next((r for r in rakipler if r["id"] == rakip_id), None)
    if not guncellendi:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rakip bulunamadı")
    return guncellendi


@router.delete("/{rakip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def sil(rakip_id: int, user: dict = Depends(get_current_user)):
    ok = tenant_rakip_sil(rakip_id, user["tenant_id"])
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rakip bulunamadı")
