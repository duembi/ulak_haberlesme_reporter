"""Asenkron raporlama motoru — kuyruk tabanlı rapor işleri."""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.deps import get_current_user
from src.database import (
    report_job_al, report_job_guncelle, report_job_listele,
    report_job_olustur, report_job_sil, rapor_kaydet, rapor_ad_guncelle, DB_PATH,
)

router = APIRouter()

_PROJE_KOKU = Path(__file__).resolve().parent.parent.parent


# ── Schemas ───────────────────────────────────────────────────────────────────

class RaporJobOlustur(BaseModel):
    gun: int = 7
    kapsam: str = "hepsi"          # sadece_ben | secili | hepsi
    rakipler: list[str] = []       # kapsam=secili ise rakip adları
    mail_alicilari: list[str] = [] # e-posta adresleri


class RaporJobYanit(BaseModel):
    id: int
    tenant_id: int
    durum: str
    gun: int
    kapsam: str
    rakipler_json: str
    mail_alicilari_json: str
    hata_mesaji: Optional[str] = None
    rapor_id: Optional[int] = None
    dosya_yolu: Optional[str] = None
    baslangic_at: Optional[str] = None
    bitis_at: Optional[str] = None
    olusturuldu_at: str


# ── Arka plan görevi ──────────────────────────────────────────────────────────

async def _ai_rapor_adi_ata(rapor_id: int, tenant_id: int, rapor_meta: dict,
                              gun: int, kapsam: str, rakipler: list[str]):
    """LLM ile rapor için kısa, açıklayıcı bir isim üretir ve kaydeder."""
    import sqlite3
    try:
        from src.llm_providers import LLMFactory
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT baslik FROM news WHERE rapor_id = ? ORDER BY tarih DESC LIMIT 10",
                (rapor_id,),
            ).fetchall()
        basliklar = [r["baslik"] for r in rows if r["baslik"]]

        bas = (rapor_meta.get("baslangic_tarih") or "")[:10]
        bit = (rapor_meta.get("bitis_tarih") or "")[:10]
        haber_sayisi = rapor_meta.get("haber_sayisi") or len(basliklar)

        kapsam_aciklama = {
            "sadece_ben": "yalnızca kurum haberleri",
            "secili": f"seçili rakipler ({', '.join(rakipler[:3])})",
            "hepsi": "tüm rakipler dahil",
        }.get(kapsam, kapsam)

        prompt = f"""Aşağıdaki bilgilere dayanarak bu medya raporu için kısa ve açıklayıcı bir Türkçe başlık üret.

Tarih aralığı: {bas} – {bit} ({gun} gün)
Kapsam: {kapsam_aciklama}
Haber sayısı: {haber_sayisi}
Örnek haberler:
{chr(10).join(f'- {b}' for b in basliklar[:8])}

SADECE başlık metnini yaz, başka hiçbir şey ekleme. Maksimum 60 karakter. Örnek: "Ulak Haberleşme Haftalık Analiz — 5-12 Mayıs 2026" """

        llm = await LLMFactory.for_tenant(tenant_id)
        ad = await llm.generate_text(prompt)
        ad = ad.strip().strip('"').strip("'")[:120]
        if ad:
            rapor_ad_guncelle(rapor_id, tenant_id, ad)
    except Exception:
        pass  # İsim üretimi başarısız olursa rapor yine kaydedildi


async def _rapor_uret(job_id: int, tenant_id: int, gun: int,
                       kapsam: str, rakipler: list[str]):
    report_job_guncelle(
        job_id,
        durum="calisiyor",
        baslangic_at=datetime.now().isoformat(),
    )
    cmd = [
        sys.executable, str(_PROJE_KOKU / "main.py"),
        "--gun", str(gun),
        "--tenant", str(tenant_id),
    ]
    if kapsam == "sadece_ben":
        cmd += ["--sadece-ben"]
    elif kapsam == "secili" and rakipler:
        cmd += ["--rakipler", ",".join(rakipler)]

    import sqlite3
    with sqlite3.connect(DB_PATH) as conn:
        onceki_max_id = conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM reports WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()[0]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(_PROJE_KOKU),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, baslangic_tarih, bitis_tarih, haber_sayisi FROM reports WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
                (tenant_id,),
            ).fetchone()

        # Bu çalıştırmada gerçekten YENİ bir rapor satırı oluşmuş mu, diye
        # kontrol ediyoruz (id, çalıştırma öncesindeki en yüksek id'den büyük
        # mü). Sadece returncode==0'a güvenmek yetmiyor: main.py seçilen
        # dönemde alakalı haber bulamazsa hata fırlatmadan sessizce hiçbir
        # rapor üretmeden çıkabiliyordu (exit code 0) — bu durumda burada
        # DB'deki EN SON (önceki, muhtemelen eski/silinmiş dosyalı) rapor
        # yanlışlıkla bu işe "tamamlandı" diye bağlanıyor, kullanıcı da
        # "PDF yok" / "Görüntüle butonu yok" gibi kafa karıştırıcı bir sahte
        # başarıyla karşılaşıyordu.
        yeni_rapor_var = row is not None and row["id"] > onceki_max_id

        if proc.returncode == 0 and yeni_rapor_var:
            rapor_id = row["id"]
            report_job_guncelle(
                job_id,
                durum="tamamlandi",
                rapor_id=rapor_id,
                bitis_at=datetime.now().isoformat(),
            )
            await _ai_rapor_adi_ata(rapor_id, tenant_id, dict(row), gun, kapsam, rakipler)
        elif proc.returncode == 2:
            report_job_guncelle(
                job_id,
                durum="hata",
                hata_mesaji="Seçilen dönemde ilgili haber bulunamadı, rapor oluşturulamadı.",
                bitis_at=datetime.now().isoformat(),
            )
        elif proc.returncode == 0:
            # returncode 0 ama yeni rapor satırı yok — beklenmeyen durum
            report_job_guncelle(
                job_id,
                durum="hata",
                hata_mesaji="Rapor üretim süreci tamamlandı ama yeni bir rapor kaydı oluşmadı.",
                bitis_at=datetime.now().isoformat(),
            )
        else:
            hata = (stdout or b"").decode("utf-8", errors="replace")[-1000:]
            report_job_guncelle(
                job_id,
                durum="hata",
                hata_mesaji=hata,
                bitis_at=datetime.now().isoformat(),
            )
    except Exception as e:
        report_job_guncelle(
            job_id,
            durum="hata",
            hata_mesaji=str(e),
            bitis_at=datetime.now().isoformat(),
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[RaporJobYanit])
async def listele(user: dict = Depends(get_current_user)):
    return report_job_listele(user["tenant_id"])


@router.post("/", response_model=RaporJobYanit, status_code=status.HTTP_202_ACCEPTED)
async def olustur(data: RaporJobOlustur, background_tasks: BackgroundTasks,
                   user: dict = Depends(get_current_user)):
    if data.gun not in (3, 7, 15, 30):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="Geçerli zaman aralıkları: 3, 7, 15, 30 gün")

    job_id = report_job_olustur(
        tenant_id=user["tenant_id"],
        gun=data.gun,
        kapsam=data.kapsam,
        rakipler=data.rakipler,
        mail_alicilari=data.mail_alicilari,
    )

    background_tasks.add_task(
        _rapor_uret,
        job_id,
        user["tenant_id"],
        data.gun,
        data.kapsam,
        data.rakipler,
    )

    jobs = report_job_listele(user["tenant_id"])
    yeni = next((j for j in jobs if j["id"] == job_id), None)
    if not yeni:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR)
    return yeni


@router.get("/{job_id}", response_model=RaporJobYanit)
async def durum_al(job_id: int, user: dict = Depends(get_current_user)):
    job = report_job_al(job_id, user["tenant_id"])
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="İş bulunamadı")
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def sil(job_id: int, user: dict = Depends(get_current_user)):
    """Çalışmayan (hata/tamamlandi/kuyrukta-takılı) bir job kaydını siler."""
    job = report_job_al(job_id, user["tenant_id"])
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="İş bulunamadı")
    if job["durum"] == "calisiyor":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Çalışan bir iş silinemez")
    ok = report_job_sil(job_id, user["tenant_id"])
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="İş silinemedi")


@router.delete("/", status_code=status.HTTP_200_OK)
async def hatalari_temizle(user: dict = Depends(get_current_user)):
    """Tüm hatalı ve takılı (kuyrukta) job kayıtlarını siler."""
    from src.database import report_job_hatalilari_sil
    sayi = report_job_hatalilari_sil(user["tenant_id"])
    return {"silinen": sayi}


@router.get("/{job_id}/download")
async def indir(job_id: int, user: dict = Depends(get_current_user)):
    job = report_job_al(job_id, user["tenant_id"])
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="İş bulunamadı")
    if job["durum"] != "tamamlandi" or not job.get("dosya_yolu"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rapor henüz hazır değil")
    yol = Path(job["dosya_yolu"])
    if not yol.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="PDF dosyası bulunamadı")
    return FileResponse(path=str(yol), media_type="application/pdf", filename=yol.name)
