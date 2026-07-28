from __future__ import annotations

import json
from dataclasses import dataclass, field

from openai import OpenAI

from app.core.config import settings


class LLMClientError(RuntimeError):
    pass


@dataclass(slots=True)
class OpenAILLMClient:
    api_key: str | None = settings.OPENAI_API_KEY
    model: str = settings.OPENAI_MODEL
    _client: OpenAI | None = field(init=False, default=None, repr=False)

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> OpenAI:
        if not self.api_key:
            raise LLMClientError("OPENAI_API_KEY is not configured")

        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)

        return self._client

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=model or self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )

        if not response.choices:
            return ""

        content = response.choices[0].message.content or ""
        return content.strip()

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> dict:
        raw_text = self.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
        )
        if not raw_text:
            return {}
        return json.loads(raw_text)


def summarize_ticket_preview(
    raw_text: str,
    *,
    entities: dict[str, str],
    original_filename: str = "",
) -> str:
    client = OpenAILLMClient()
    if not client.available:
        return ""

    system_prompt = (
        "Summarize OCR ticket text for an internal review queue. "
        "Return one short plain-text sentence, no markdown, no bullets, no JSON. "
        "Prefer ticket number, driver, truck, material, and job location if present."
    )
    user_prompt = (
        f"Filename: {original_filename or 'unknown'}\n"
        f"Detected fields: {json.dumps(entities, sort_keys=True)}\n"
        f"OCR text:\n{raw_text[:6000]}"
    )

    try:
        summary = client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )
    except Exception:
        return ""

    return " ".join(summary.split())