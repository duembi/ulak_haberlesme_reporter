"""
Birleşik AI istemcisi.

Aktif model, UI'dan seçilip DB'de saklanır (ayarlar.model).
Model ID'sinin önekine göre backend otomatik belirlenir:
  claude-*  → Claude Code CLI (subprocess)
  gemini-*  → Google Gemini API
  gpt-*     → OpenAI API          (henüz entegre edilmedi)
  llama*    → Meta / Ollama       (henüz entegre edilmedi)
  grok-*    → xAI Grok API        (henüz entegre edilmedi)
"""
from __future__ import annotations

import shutil
import subprocess
import time

from loguru import logger

from config.settings import (
    AI_BACKEND, BASE_DIR,
    CLAUDE_MODEL, CLAUDE_TIMEOUT,
    GEMINI_API_KEY, GEMINI_MODEL,
)
from src.retry import retry

_MCP_CONFIG = BASE_DIR / ".mcp.json"
_CLAUDE_BIN = shutil.which("claude")

_VARSAYILAN_MODEL = "claude-sonnet-4-6"


def _model_al() -> str:
    """DB'deki seçili modeli döner; hata varsa varsayılana döner."""
    try:
        from src.database import ayar_al
        return ayar_al("model", _VARSAYILAN_MODEL)
    except Exception:
        return CLAUDE_MODEL if AI_BACKEND.lower() == "claude" else GEMINI_MODEL


def _backend_belirle(model_id: str) -> str:
    if model_id.startswith("claude"):
        return "claude"
    if model_id.startswith("gemini"):
        return "gemini"
    if model_id.startswith("gpt"):
        return "openai"
    if model_id.startswith("llama"):
        return "meta"
    if model_id.startswith("grok"):
        return "grok"
    return "gemini"


# ── Claude CLI backend ────────────────────────────────────────────────────────

def _claude_cagir(prompt: str, sistem: str = "", mcp: bool = False,
                  timeout: int | None = None, model: str | None = None) -> str:
    if not _CLAUDE_BIN:
        raise EnvironmentError("'claude' komutu PATH'te bulunamadı. Claude Code CLI kurulu mu?")
    cmd = [_CLAUDE_BIN, "--model", model or CLAUDE_MODEL, "-p", prompt]
    if sistem:
        cmd += ["--append-system-prompt", sistem]
    if mcp and _MCP_CONFIG.exists():
        cmd += ["--mcp-config", str(_MCP_CONFIG)]
    sonuc = subprocess.run(
        cmd,
        capture_output=True, text=True,
        timeout=timeout or CLAUDE_TIMEOUT,
        encoding="utf-8",
    )
    if sonuc.returncode != 0:
        raise RuntimeError(sonuc.stderr.strip() or sonuc.stdout.strip() or "bilinmeyen hata")
    return sonuc.stdout.strip()


# ── Gemini API backend ────────────────────────────────────────────────────────

def _gemini_cagir(prompt: str, sistem: str = "", model: str | None = None) -> str:
    if not GEMINI_API_KEY:
        raise EnvironmentError("GEMINI_API_KEY .env'de tanımlı değil")
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)
    config = types.GenerateContentConfig(system_instruction=sistem) if sistem else None
    yanit = client.models.generate_content(
        model=model or GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    return yanit.text.strip()


# ── Ortak arayüz ──────────────────────────────────────────────────────────────

@retry(max_deneme=4, bekleme=60.0, carpan=2.0, istisnalar=(RuntimeError, Exception))
def sorgula(prompt: str, sistem: str = "", mcp: bool = False,
            timeout: int | None = None) -> str:
    """
    Seçili modele prompt gönderir ve yanıt döner.

    Model, UI'dan seçilip DB'de saklanır. Backend otomatik belirlenir.
    mcp: yalnızca Claude backend'inde geçerli.
    """
    model_id = _model_al()
    backend  = _backend_belirle(model_id)
    logger.debug(f"AI çağrısı [{backend}/{model_id}]")

    if backend == "gemini":
        try:
            return _gemini_cagir(prompt, sistem, model=model_id)
        except Exception as e:
            hata_str = str(e).lower()
            if "429" in hata_str or "resource_exhausted" in hata_str or "quota" in hata_str:
                logger.warning("Gemini 429 RESOURCE_EXHAUSTED — 90 saniye bekleniyor...")
                time.sleep(90)
            raise

    if backend == "claude":
        return _claude_cagir(prompt, sistem, mcp, timeout, model=model_id)

    raise NotImplementedError(
        f"'{backend}' backend henüz entegre edilmedi. "
        f"Model '{model_id}' yakında desteklenecek."
    )
