"""LLM konfigürasyon yönetimi — BYOM (Bring Your Own Model)."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.deps import get_current_user
from src.crypto import decrypt, encrypt
from src.database import (
    tenant_llm_config_al, tenant_llm_config_aktifle,
    tenant_llm_config_ekle, tenant_llm_config_listele,
    tenant_llm_config_sil,
)

router = APIRouter()

ProviderTip = Literal["anthropic", "openai", "gemini", "custom"]


class LLMConfigOlustur(BaseModel):
    provider_name: ProviderTip
    model_name: str
    api_key: str
    base_url: Optional[str] = None


class LLMConfigYanit(BaseModel):
    id: int
    tenant_id: int
    provider_name: str
    model_name: str
    base_url: Optional[str]
    aktif: bool
    olusturuldu_at: str


@router.get("/", response_model=list[LLMConfigYanit])
async def listele(user: dict = Depends(get_current_user)):
    return tenant_llm_config_listele(user["tenant_id"])


@router.post("/", response_model=LLMConfigYanit, status_code=status.HTTP_201_CREATED)
async def ekle(data: LLMConfigOlustur, user: dict = Depends(get_current_user)):
    encrypted = encrypt(data.api_key)
    config_id = tenant_llm_config_ekle(
        tenant_id=user["tenant_id"],
        provider_name=data.provider_name,
        model_name=data.model_name,
        api_key_encrypted=encrypted,
        base_url=data.base_url,
    )
    configs = tenant_llm_config_listele(user["tenant_id"])
    yeni = next((c for c in configs if c["id"] == config_id), None)
    if not yeni:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Kayıt oluşturulamadı")
    return yeni


@router.post("/{config_id}/activate")
async def aktifle(config_id: int, user: dict = Depends(get_current_user)):
    ok = tenant_llm_config_aktifle(config_id, user["tenant_id"])
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Konfigürasyon bulunamadı")
    return {"mesaj": "Konfigürasyon aktifleştirildi"}


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def sil(config_id: int, user: dict = Depends(get_current_user)):
    ok = tenant_llm_config_sil(config_id, user["tenant_id"])
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Konfigürasyon bulunamadı")


@router.get("/active")
async def aktif_config(user: dict = Depends(get_current_user)):
    config = tenant_llm_config_al(user["tenant_id"])
    if not config:
        return {"aktif": False, "mesaj": "Aktif LLM konfigürasyonu yok — sistem varsayılanı kullanılıyor"}
    return {
        "aktif": True,
        "provider_name": config["provider_name"],
        "model_name": config["model_name"],
    }
