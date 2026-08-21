import asyncio
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.deps import get_current_user
from api.schemas import PipelineIstek, PipelineDurumu, RakipYanit

router = APIRouter()

_state: dict = {
    "calisiyor": False,
    "baslangic_zamani": None,
    "bitis_zamani": None,
    "sonuc": None,
    "hata": None,
}

_PROJE_KOKU = Path(__file__).resolve().parent.parent.parent


def _rakip_kategorisi(ad: str) -> str:
    uydu = {"Eutelsat", "SES", "Arabsat", "Intelsat", "Starlink"}
    turk_telekom = {"Turkcell", "Türk Telekom"}
    turk_uzay = {"TUSAŞ", "SDT Uzay", "TUA", "PLANS"}
    ajanslar = {"NASA", "ESA", "JAXA", "ISRO", "CNSA", "Roscosmos",
                "UK Space Agency", "CSA", "UAE Space Agency"}
    if ad in uydu:
        return "Uydu Operatörleri"
    if ad in turk_telekom:
        return "Türk Telekom"
    if ad in turk_uzay:
        return "Türk Uzay Sanayii"
    if ad in ajanslar:
        return "Uzay Ajansları"
    return "Global Uzay Firmaları"


async def _pipeline_calistir(istek: PipelineIstek):
    _state["calisiyor"] = True
    _state["baslangic_zamani"] = datetime.now().isoformat()
    _state["bitis_zamani"] = None
    _state["sonuc"] = None
    _state["hata"] = None

    cmd = [sys.executable, str(_PROJE_KOKU / "main.py"), "--gun", str(istek.gun)]
    if istek.rakipler:
        cmd += ["--rakipler", ",".join(istek.rakipler)]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(_PROJE_KOKU),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            _state["sonuc"] = "basarili"
        else:
            _state["hata"] = (stdout or b"").decode("utf-8", errors="replace")[-500:]
            _state["sonuc"] = "hata"
    except Exception as e:
        _state["hata"] = str(e)
        _state["sonuc"] = "hata"
    finally:
        _state["calisiyor"] = False
        _state["bitis_zamani"] = datetime.now().isoformat()


@router.get("/status", response_model=PipelineDurumu)
async def pipeline_durumu(user: dict = Depends(get_current_user)):
    return _state


@router.post("/run", status_code=202)
async def pipeline_baslat(istek: PipelineIstek, background_tasks: BackgroundTasks,
                           user: dict = Depends(get_current_user)):
    if _state["calisiyor"]:
        raise HTTPException(409, detail="Pipeline zaten çalışıyor")
    background_tasks.add_task(_pipeline_calistir, istek)
    return {"mesaj": "Pipeline başlatıldı", "gun": istek.gun}


@router.get("/competitors", response_model=list[RakipYanit])
async def rakipleri_listele(user: dict = Depends(get_current_user)):
    from src.database import rakip_listesi_al
    rows = rakip_listesi_al(sadece_aktif=True)
    return [
        {
            "ad": r["ad"],
            "bolge": r["bolge"],
            "aciklama": r["aciklama"],
            "ticker": r["ticker"],
            "kategori": _rakip_kategorisi(r["ad"]),
        }
        for r in rows
    ]
