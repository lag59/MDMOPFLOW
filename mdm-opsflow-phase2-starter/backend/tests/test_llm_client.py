from __future__ import annotations

import pytest

from app.services.llm_client import LLMClientError, OpenAILLMClient, summarize_ticket_preview


def test_openai_client_requires_api_key() -> None:
    client = OpenAILLMClient(api_key=None)

    with pytest.raises(LLMClientError):
        client.generate_text(system_prompt="sys", user_prompt="user")


def test_openai_client_generates_text(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        class Choice:
            class Message:
                content = "  Ticket TCK-1042 ready  "

            message = Message()

        choices = [Choice()]

    class FakeCompletions:
        def create(self, **kwargs):
            self.kwargs = kwargs
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.chat = FakeChat()

    monkeypatch.setattr("app.services.llm_client.OpenAI", FakeOpenAI)

    client = OpenAILLMClient(api_key="test-key", model="gpt-5")
    text = client.generate_text(system_prompt="sys", user_prompt="user")

    assert text == "Ticket TCK-1042 ready"


def test_summarize_ticket_preview_returns_empty_without_key() -> None:
    summary = summarize_ticket_preview("Ticket: TCK-1042", entities={"ticket_number": "TCK-1042"})

    assert summary == ""