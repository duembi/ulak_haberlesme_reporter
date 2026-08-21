from fastapi import APIRouter, Depends, HTTPException, status
from api.deps import get_current_user
from api.schemas import AliciOlustur, AliciGuncelle, AliciYanit
from src.database import mail_ekle, mail_guncelle, mail_sil, mail_listesi_tumu

router = APIRouter()


@router.get("/", response_model=list[AliciYanit])
async def alici_listele(user: dict = Depends(get_current_user)):
    return mail_listesi_tumu(tenant_id=user["tenant_id"])


@router.post("/", response_model=AliciYanit, status_code=status.HTTP_201_CREATED)
async def alici_ekle(data: AliciOlustur, user: dict = Depends(get_current_user)):
    ok = mail_ekle(
        data.ad_soyad, data.email, data.rol,
        data.haftalik, data.kriz, data.hata,
        tenant_id=user["tenant_id"],
    )
    if not ok:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Bu e-posta zaten kayıtlı")
    kayitlar = mail_listesi_tumu(tenant_id=user["tenant_id"])
    yeni = next((k for k in kayitlar if k["email"] == data.email.lower().strip()), None)
    if not yeni:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Kayıt oluşturulamadı")
    return yeni


@router.patch("/{email}", response_model=AliciYanit)
async def alici_guncelle(email: str, data: AliciGuncelle,
                          user: dict = Depends(get_current_user)):
    guncellemeler = data.model_dump(exclude_none=True)
    if not guncellemeler:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="En az bir alan gerekli")
    ok = mail_guncelle(email, tenant_id=user["tenant_id"], **guncellemeler)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alıcı bulunamadı")
    kayitlar = mail_listesi_tumu(tenant_id=user["tenant_id"])
    guncellendi = next((k for k in kayitlar if k["email"] == email.lower().strip()), None)
    if not guncellendi:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alıcı bulunamadı")
    return guncellendi


@router.delete("/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def alici_sil_endpoint(email: str, user: dict = Depends(get_current_user)):
    ok = mail_sil(email, tenant_id=user["tenant_id"])
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alıcı bulunamadı")
