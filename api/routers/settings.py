from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user
from api.schemas import ModelAyar
from src.database import ayar_al, ayar_guncelle

router = APIRouter()

GECERLI_MODELLER = {
    # Claude
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
    "claude-opus-4-7",
    # Gemini
    "gemini-3.1-pro",
    "gemini-3-flash",
    "gemini-3.1-flash-lite",
    # OpenAI
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.4-mini",
    # Meta
    "llama3",
    # xAI
    "grok-4.3",
}


@router.get("/model", response_model=ModelAyar)
async def model_al(user: dict = Depends(get_current_user)):
    return {"model": ayar_al("model", "claude-sonnet-4-6")}


@router.patch("/model", response_model=ModelAyar)
async def model_guncelle(data: ModelAyar, user: dict = Depends(get_current_user)):
    if data.model not in GECERLI_MODELLER:
        raise HTTPException(400, detail=f"Geçersiz model: {data.model}")
    ayar_guncelle("model", data.model)
    return {"model": data.model}
