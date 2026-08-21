"""FastAPI bağımlılıkları — JWT auth + tenant izolasyonu."""
from fastapi import HTTPException, Request
from jose import JWTError, jwt

from config.settings import JWT_ALGORITHM, JWT_SECRET_KEY


def _token_from_request(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz veya süresi dolmuş token")


async def get_current_user(request: Request) -> dict:
    token = _token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Kimlik doğrulama gerekli")
    payload = _decode(token)
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(status_code=401, detail="Geçersiz token içeriği")
    return {
        "user_id": int(user_id),
        "tenant_id": int(tenant_id),
        "email": payload.get("email", ""),
        "ad_soyad": payload.get("ad_soyad", ""),
        "rol": payload.get("rol", "kullanici"),
    }


async def get_tenant_id(request: Request) -> int:
    user = await get_current_user(request)
    return user["tenant_id"]
