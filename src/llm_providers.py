"""
LLM Provider Abstraction — Strategy Pattern
Her tenant kendi LLM konfigürasyonunu kullanabilir (BYOM).
"""
from __future__ import annotations

import asyncio
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from config.settings import (
    AI_BACKEND, BASE_DIR,
    CLAUDE_MODEL, CLAUDE_TIMEOUT,
    GEMINI_API_KEY, GEMINI_MODEL,
)


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        pass


# ── Anthropic CLI ─────────────────────────────────────────────────────────────

class AnthropicCLIProvider(BaseLLMProvider):
    """Mevcut Claude CLI subprocess yaklaşımı (Pro aboneliği)."""

    def __init__(self, model_name: str = CLAUDE_MODEL):
        self.model_name = model_name
        self._bin = self._find_claude()

    @staticmethod
    def _find_claude() -> str:
        import shutil
        found = shutil.which("claude")
        if found:
            return found
        # Fallback: Python bin dizini (pip install ile kurulduysa)
        candidate = Path(sys.executable).parent / "claude"
        if candidate.exists():
            return str(candidate)
        raise FileNotFoundError(
            "Claude CLI bulunamadı. 'claude' komutunun PATH'te olduğundan emin olun."
        )

    async def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        import subprocess
        full = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                [self._bin, "-p", full],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=CLAUDE_TIMEOUT,
                cwd=str(BASE_DIR),
            ),
        )
        return result.stdout.strip()


# ── Anthropic API ─────────────────────────────────────────────────────────────

class AnthropicAPIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "claude-sonnet-4-6"):
        self.api_key = api_key
        self.model_name = model_name

    async def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            system=system_prompt or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


# ── OpenAI / Custom OpenAI-compatible ────────────────────────────────────────

class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI, vLLM, Ollama veya herhangi bir OpenAI-uyumlu endpoint."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o",
                 base_url: str | None = None):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url

    async def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        from openai import AsyncOpenAI
        kwargs: dict = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = AsyncOpenAI(**kwargs)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = await client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""


# ── Gemini ────────────────────────────────────────────────────────────────────

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = GEMINI_MODEL):
        self.api_key = api_key
        self.model_name = model_name

    async def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        from google import genai
        client = genai.Client(api_key=self.api_key)
        full = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = client.models.generate_content(model=self.model_name, contents=full)
        return response.text or ""


# ── Factory ───────────────────────────────────────────────────────────────────

class LLMFactory:
    @staticmethod
    def create(provider_name: str, model_name: str,
               api_key: str, base_url: str | None = None) -> BaseLLMProvider:
        match provider_name.lower():
            case "anthropic":
                return AnthropicAPIProvider(api_key=api_key, model_name=model_name)
            case "openai":
                return OpenAICompatibleProvider(api_key=api_key, model_name=model_name)
            case "gemini":
                return GeminiProvider(api_key=api_key, model_name=model_name)
            case "custom":
                return OpenAICompatibleProvider(
                    api_key=api_key or "none",
                    model_name=model_name,
                    base_url=base_url,
                )
            case _:
                raise ValueError(f"Bilinmeyen provider: {provider_name}")

    @staticmethod
    async def for_tenant(tenant_id: int) -> BaseLLMProvider:
        """Tenant'ın aktif LLM konfigürasyonunu yükler. Yoksa sistem varsayılanı."""
        from src.database import tenant_llm_config_al
        from src.crypto import decrypt

        config = tenant_llm_config_al(tenant_id)
        if config:
            try:
                api_key = decrypt(config["api_key_encrypted"])
                return LLMFactory.create(
                    config["provider_name"],
                    config["model_name"],
                    api_key,
                    config.get("base_url"),
                )
            except Exception:
                pass  # Şifre çözme başarısız → sistem varsayılanına dön

        # Sistem varsayılanı
        if AI_BACKEND == "gemini" and GEMINI_API_KEY:
            return GeminiProvider(api_key=GEMINI_API_KEY, model_name=GEMINI_MODEL)
        return AnthropicCLIProvider(model_name=CLAUDE_MODEL)

    @staticmethod
    def system_default() -> BaseLLMProvider:
        """Tenant olmaksızın sistem geneli LLM provider'ı."""
        if AI_BACKEND == "gemini" and GEMINI_API_KEY:
            return GeminiProvider(api_key=GEMINI_API_KEY, model_name=GEMINI_MODEL)
        return AnthropicCLIProvider(model_name=CLAUDE_MODEL)
