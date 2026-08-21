"""Auth endpoints — kayıt, giriş, mevcut kullanıcı."""
from datetime import datetime, timedelta, timezone
import json

import bcrypt as _bcrypt

from fastapi import APIRouter, HTTPException, status, Depends
from jose import jwt
from pydantic import BaseModel, field_validator

from api.deps import get_current_user
from config.settings import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET_KEY
from src.database import (
    kullanici_bul, kullanici_ekle, kullanici_sayisi,
    tenant_bul_veya_olustur, tenant_al,
    tenant_brand_colors_al, tenant_brand_colors_kaydet,
)
from src.llm_providers import LLMFactory
from src.brand_colors import marka_paleti_al, brandfetch_paleti_al

_GENERIC_DOMAINS = {
    "gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "yandex.com",
    "mail.com", "icloud.com", "live.com", "msn.com", "protonmail.com",
    "yahoo.com.tr", "hotmail.com.tr", "gmail.com.tr",
}

_BRANDING_SYSTEM = (
    "Sen bir marka tasarımı ve UI/UX uzmanısın. "
    "Eğitim verinle bilinen gerçek marka renklerini (resmi marka kılavuzları, "
    "BrandColors.net, BrandColorCode.com kaynaklı veriler) kullanırsın. "
    "WCAG AA erişilebilirlik standartlarına uygun kontrast oranlarını gözetirsin. "
    "Yanıtını daima geçerli JSON formatında ver, başka metin ekleme."
)

_BRANDING_PROMPT = """
Firma adı: {kimlik}

GÖREV: Bu firmanın kurumsal renklerinden esinlenerek bir SaaS UI renk sistemi oluştur.

KURALLAR:
1. Firma gerçek ve tanınan bir markaysa (örn. Türksat, Turkcell, Garanti, Nike, Google):
   - O markanın resmi kurumsal ana rengini brand_600 olarak kullan (tam HEX kodu).
   - brand_700 = %10-15 daha koyu tonu (HSL lightness azalt).
   - brand_500 = %10-15 daha açık tonu.
   - brand_50..brand_200 = çok açık, pastel tonlar (arka plan vurguları için).
   - brand_800 = dark modda okunabilir açık ton.
2. Firma bilinmiyorsa sektörüne uygun profesyonel bir palet öner.
3. Light modda text_main ile bg_base arasında WCAG AA kontrast (en az 4.5:1) sağla.
4. Dark modda text_main ile bg_base arasında aynı kontrast şartını sağla.
5. Sidebar her iki modda da #0F172A .. #1E293B aralığında koyu kalabilir.
6. bg_base (light) = #F1F5F9 ..#FFFFFF arası açık ton.
7. bg_base (dark)  = #0F172A .. #1A2332 arası koyu ton.

İKİ MOD ÜRET:
- light: açık arka plan, koyu yazı, pastel brand tonları
- dark: koyu arka plan, açık yazı, daha canlı/parlak brand tonları

YANITI SADECE ŞU JSON FORMATINDA VER (açıklama ekleme):
{{
  "light": {{
    "brand_600": "#hex", "brand_700": "#hex", "brand_500": "#hex",
    "brand_50": "#hex", "brand_100": "#hex", "brand_200": "#hex", "brand_800": "#hex",
    "sidebar": "#hex",
    "bg_base": "#hex", "bg_card": "#hex", "bg_input": "#hex", "bg_hover": "#hex",
    "text_main": "#hex", "text_sub": "#hex", "text_muted": "#hex", "border": "#hex"
  }},
  "dark": {{
    "brand_600": "#hex", "brand_700": "#hex", "brand_500": "#hex",
    "brand_50": "#hex", "brand_100": "#hex", "brand_200": "#hex", "brand_800": "#hex",
    "sidebar": "#hex",
    "bg_base": "#hex", "bg_card": "#hex", "bg_input": "#hex", "bg_hover": "#hex",
    "text_main": "#hex", "text_sub": "#hex", "text_muted": "#hex", "border": "#hex"
  }}
}}
"""

router = APIRouter()


def _hash(sifre: str) -> str:
    return _bcrypt.hashpw(sifre.encode(), _bcrypt.gensalt()).decode()


def _verify(sifre: str, hash_: str) -> bool:
    return _bcrypt.checkpw(sifre.encode(), hash_.encode())


# ── Schemas ───────────────────────────────────────────────────────────────────

class KayitIstek(BaseModel):
    email: str
    sifre: str
    ad_soyad: str
    kurum_adi: str = ""  # İsteğe bağlı; boşsa domain'den türetilir

    @field_validator("email")
    @classmethod
    def email_gecerli(cls, v: str) -> str:
        v = v.strip().replace("ı", "i").replace("İ", "I").lower()
        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError("Geçerli bir kurumsal e-posta adresi girin")
        return v

    @field_validator("sifre")
    @classmethod
    def sifre_uzunluk(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Şifre en az 8 karakter olmalı")
        return v


class GirisIstek(BaseModel):
    email: str
    sifre: str


class TokenYanit(BaseModel):
    access_token: str
    token_type: str = "bearer"
    kullanici: dict


# ── Helpers ───────────────────────────────────────────────────────────────────

def _token_olustur(user: dict) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user["id"]),
        "tenant_id": user["tenant_id"],
        "email": user["email"],
        "ad_soyad": user["ad_soyad"],
        "rol": user["rol"],
        "exp": exp,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenYanit, status_code=status.HTTP_201_CREATED)
async def kayit(data: KayitIstek):
    domain = data.email.split("@")[1]
    kurum_adi = data.kurum_adi.strip() or domain

    # Tenant bul veya oluştur (domain bazlı)
    tenant_id = tenant_bul_veya_olustur(domain, kurum_adi)

    # İlk kullanıcı → admin rolü
    rol = "admin" if kullanici_sayisi(tenant_id) == 0 else "kullanici"

    user_id = kullanici_ekle(
        tenant_id=tenant_id,
        email=data.email,
        password_hash=_hash(data.sifre),
        ad_soyad=data.ad_soyad,
        rol=rol,
    )
    if user_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Bu e-posta zaten kayıtlı")

    user = kullanici_bul(data.email)
    token = _token_olustur(user)
    return TokenYanit(
        access_token=token,
        kullanici={"id": user["id"], "email": user["email"],
                   "ad_soyad": user["ad_soyad"], "rol": user["rol"],
                   "tenant_id": tenant_id},
    )


@router.post("/login", response_model=TokenYanit)
async def giris(data: GirisIstek):
    user = kullanici_bul(data.email.strip().replace("ı", "i").replace("İ", "I").lower())
    if not user or not _verify(data.sifre, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            detail="E-posta veya şifre hatalı")
    token = _token_olustur(user)
    tenant = tenant_al(user["tenant_id"]) or {}
    return TokenYanit(
        access_token=token,
        kullanici={"id": user["id"], "email": user["email"],
                   "ad_soyad": user["ad_soyad"], "rol": user["rol"],
                   "tenant_id": user["tenant_id"],
                   "tenant_adi": tenant.get("ad", ""),
                   "tenant_domain": tenant.get("domain", "")},
    )


@router.get("/me")
async def beni_al(user: dict = Depends(get_current_user)):
    tenant = tenant_al(user["tenant_id"]) or {}
    return {**user, "tenant_adi": tenant.get("ad", ""), "tenant_domain": tenant.get("domain", "")}


_VARSAYILAN_LIGHT = {
    "brand_600": "#2563EB", "brand_700": "#1D4ED8", "brand_500": "#3B82F6",
    "brand_50":  "#EFF6FF", "brand_100": "#DBEAFE", "brand_200": "#BFDBFE",
    "brand_800": "#1E3A5F", "sidebar":   "#0F172A",
    "bg_base":   "#F1F5F9", "bg_card":   "#FFFFFF",
    "bg_input":  "#FFFFFF", "bg_hover":  "#F8FAFC",
    "text_main": "#0F172A", "text_sub":  "#475569",
    "text_muted":"#94A3B8", "border":    "#E2E8F0",
}
_VARSAYILAN_DARK = {
    "brand_600": "#3B82F6", "brand_700": "#2563EB", "brand_500": "#60A5FA",
    "brand_50":  "#0C1A2E", "brand_100": "#152744", "brand_200": "#1E3A5F",
    "brand_800": "#93C5FD", "sidebar":   "#020617",
    "bg_base":   "#0F172A", "bg_card":   "#1E293B",
    "bg_input":  "#0F172A", "bg_hover":  "#1E293B",
    "text_main": "#F8FAFC", "text_sub":  "#CBD5E1",
    "text_muted":"#64748B", "border":    "#334155",
}
_VARSAYILAN_BRANDING = {"light": _VARSAYILAN_LIGHT, "dark": _VARSAYILAN_DARK}

_PALET_ANAHTARLARI = list(_VARSAYILAN_LIGHT.keys())


def _dogrula_palet(palet: dict, varsayilan: dict) -> dict:
    temiz = {}
    for k in _PALET_ANAHTARLARI:
        v = palet.get(k, "")
        if isinstance(v, str) and v.startswith("#") and len(v) in (4, 7):
            temiz[k] = v
        else:
            temiz[k] = varsayilan[k]
    return temiz


async def _llm_branding_uret(tenant_id: int) -> dict:
    """LLM ile marka rengi üretir ve DB'ye kaydeder. Hata olursa fırlatır."""
    tenant = tenant_al(tenant_id) or {}
    ad     = tenant.get("ad", "")
    domain = tenant.get("domain", "")

    # Genel e-posta sağlayıcı domainleri için kurum adı yoksa varsayılan dön
    domain_generic = domain.lower() in _GENERIC_DOMAINS
    if domain_generic and (not ad or ad == domain):
        return _VARSAYILAN_BRANDING

    # Genel domain varsa sadece kurum adını kullan, yoksa ikisini birden
    if domain_generic:
        kimlik = ad
    else:
        kimlik = f"{ad} ({domain})" if ad and ad != domain else (ad or domain)

    # Adım 1: yerel marka rengi veritabanı (anlık, LLM/API yok)
    yerel_palet = marka_paleti_al(ad or domain)
    if yerel_palet:
        tenant_brand_colors_kaydet(tenant_id, yerel_palet)
        return yerel_palet

    # Adım 2: Brandfetch API (domain bazlı, key varsa)
    if not domain_generic:
        bf_palet = await brandfetch_paleti_al(domain)
        if bf_palet:
            tenant_brand_colors_kaydet(tenant_id, bf_palet)
            return bf_palet

    llm    = await LLMFactory.for_tenant(tenant_id)
    prompt = _BRANDING_PROMPT.format(kimlik=kimlik)
    yanit  = await llm.generate_text(prompt, system_prompt=_BRANDING_SYSTEM)

    bas = yanit.find("{")
    bit = yanit.rfind("}") + 1
    if bas == -1 or bit == 0:
        raise ValueError(f"LLM geçerli JSON döndürmedi. Yanıt: {yanit[:200]}")
    veri = json.loads(yanit[bas:bit])

    branding = {
        "light": _dogrula_palet(veri.get("light", {}), _VARSAYILAN_LIGHT),
        "dark":  _dogrula_palet(veri.get("dark",  {}), _VARSAYILAN_DARK),
    }
    tenant_brand_colors_kaydet(tenant_id, branding)
    return branding


@router.get("/branding")
async def branding_al(user: dict = Depends(get_current_user)):
    """Light + dark renk paletini döndürür. DB'de yoksa LLM ile üretir."""
    tenant_id = user["tenant_id"]

    cached = tenant_brand_colors_al(tenant_id)
    if cached and "light" in cached and "dark" in cached:
        return cached

    try:
        return await _llm_branding_uret(tenant_id)
    except Exception:
        return _VARSAYILAN_BRANDING


@router.post("/branding/refresh")
async def branding_yenile(user: dict = Depends(get_current_user)):
    """DB cache'ini temizler ve LLM ile yeni marka rengi üretir."""
    tenant_id = user["tenant_id"]
    tenant_brand_colors_kaydet(tenant_id, {})  # cache'i sıfırla

    try:
        result = await _llm_branding_uret(tenant_id)
        # _llm_branding_uret generic domain → varsayılan döndürebilir (DB'ye kaydetmez)
        # Bu durumda varsayılanı da cache'e kaydet ki her login'de LLM çağrılmasın
        tenant_brand_colors_kaydet(tenant_id, result)
        return result
    except Exception as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM marka rengi üretemedi: {e}",
        )
