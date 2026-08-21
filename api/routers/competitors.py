import json

from fastapi import APIRouter, Depends, HTTPException, status
from api.deps import get_current_user
from api.schemas import RakipOlustur, RakipGuncelle, RakipTamYanit
from src.database import rakip_listesi_al, rakip_ekle, rakip_guncelle, rakip_sil, tenant_al
from src.llm_providers import LLMFactory

router = APIRouter()

_SYSTEM = (
    "Sen bir pazar araştırması uzmanısın. "
    "Verilen firma bilgisine göre sektördeki rakipleri analiz edersin. "
    "Yanıtlarını daima geçerli JSON formatında ver, başka metin ekleme."
)

_PROMPT = """
Aşağıdaki firma için en önemli 10-15 rakip firmayı belirle:

Firma domain: {domain}
Firma adı: {ad}
Ek not: {sektor}

Her rakip için şu alanları doldur:
- ad: Rakip firma adı
- aciklama: Neden rakip olduğunu 1-2 cümleyle açıkla (Türkçe)
- bolge: Firmanın bulunduğu ülke/bölge (Türkçe)
- rss_sorgu: Google News RSS için İngilizce arama sorgusu (örnek: "Eutelsat satellite news")
- rss_dil: Haber dilini "tr" veya "en" olarak belirt

Yanıtı SADECE şu JSON formatında ver:
{{
  "rakipler": [
    {{"ad": "...", "aciklama": "...", "bolge": "...", "rss_sorgu": "...", "rss_dil": "en"}}
  ]
}}
"""


@router.post("/analyze", response_model=list[RakipTamYanit])
async def analiz_baslat(sektor: str = "", user: dict = Depends(get_current_user)):
    """Tenant domain'inden LLM ile rakip firmalar tespit eder, rakipler tablosuna ekler."""
    tenant_id = user["tenant_id"]
    tenant = tenant_al(tenant_id)
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant bulunamadı")

    try:
        llm = await LLMFactory.for_tenant(tenant_id)
        prompt = _PROMPT.format(
            domain=tenant["domain"],
            ad=tenant["ad"],
            sektor=sektor.strip() or "belirtilmedi",
        )
        yanit = await llm.generate_text(prompt, system_prompt=_SYSTEM)
    except Exception as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"LLM bağlantısı başarısız: {type(e).__name__}: {e}")

    try:
        baslangic = yanit.find("{")
        bitis = yanit.rfind("}") + 1
        if baslangic == -1 or bitis == 0:
            raise ValueError("JSON bulunamadı")
        veri = json.loads(yanit[baslangic:bitis])
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            detail="LLM geçersiz JSON döndürdü")

    eklenenler = 0
    for r in veri.get("rakipler", []):
        ad = (r.get("ad") or "").strip()
        rss_sorgu = (r.get("rss_sorgu") or "").strip()
        if not ad or not rss_sorgu:
            continue
        ok = rakip_ekle(
            ad=ad,
            rss_sorgu=rss_sorgu,
            rss_dil=r.get("rss_dil", "en"),
            bolge=(r.get("bolge") or "").strip(),
            aciklama=(r.get("aciklama") or "").strip(),
        )
        if ok:
            eklenenler += 1

    return rakip_listesi_al(sadece_aktif=False)


@router.get("/", response_model=list[RakipTamYanit])
async def listele(user: dict = Depends(get_current_user)):
    return rakip_listesi_al(sadece_aktif=False)


@router.post("/", response_model=RakipTamYanit, status_code=status.HTTP_201_CREATED)
async def ekle(data: RakipOlustur, user: dict = Depends(get_current_user)):
    ok = rakip_ekle(
        ad=data.ad, rss_sorgu=data.rss_sorgu, rss_dil=data.rss_dil,
        bolge=data.bolge, aciklama=data.aciklama, ticker=data.ticker or None,
    )
    if not ok:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Bu isimde rakip zaten mevcut")
    tum = rakip_listesi_al(sadece_aktif=False)
    yeni = next((r for r in tum if r["ad"] == data.ad.strip()), None)
    if not yeni:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Kayıt oluşturulamadı")
    return yeni


@router.patch("/{rakip_id}", response_model=RakipTamYanit)
async def guncelle(rakip_id: int, data: RakipGuncelle,
                   user: dict = Depends(get_current_user)):
    guncellemeler = data.model_dump(exclude_none=True)
    if not guncellemeler:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="En az bir alan gerekli")
    if "aktif" in guncellemeler:
        guncellemeler["aktif"] = int(guncellemeler["aktif"])
    ok = rakip_guncelle(rakip_id, **guncellemeler)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rakip bulunamadı")
    tum = rakip_listesi_al(sadece_aktif=False)
    guncellendi = next((r for r in tum if r["id"] == rakip_id), None)
    if not guncellendi:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rakip bulunamadı")
    return guncellendi


@router.delete("/{rakip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def sil(rakip_id: int, user: dict = Depends(get_current_user)):
    ok = rakip_sil(rakip_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rakip bulunamadı")
