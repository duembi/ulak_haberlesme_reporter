import asyncio
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.deps import get_current_user
from api.schemas import PipelineIstek, PipelineDurumu

router = APIRouter()

_state: dict = {
    "calisiyor": False,
    "baslangic_zamani": None,
    "bitis_zamani": None,
    "sonuc": None,
    "hata": None,
}

_PROJE_KOKU = Path(__file__).resolve().parent.parent.parent


async def _pipeline_calistir(istek: PipelineIstek):
    _state["calisiyor"] = True
    _state["baslangic_zamani"] = datetime.now().isoformat()
    _state["bitis_zamani"] = None
    _state["sonuc"] = None
    _state["hata"] = None

    cmd = [sys.executable, str(_PROJE_KOKU / "main.py"), "--gun", str(istek.gun)]

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
