"""
openrouter_client.py

Provides the :class:`OpenRouterConversation` class that encapsulates a single
LLM conversation session via the official OpenRouter SDK.

One instance = one conversation thread.  The instance keeps the full message
history and automatically appends each user prompt and assistant response,
enabling multi-turn interactions (e.g. initial prompt -> request context ->
send context -> complete analysis).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from dotenv import load_dotenv
from openrouter import OpenRouter
from openrouter.components import FormatJSONObjectConfig

from prompt_generator import AuditResponse

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MODEL = "openai/gpt-5.4-nano"


def _normalize_audit_response_json(raw: str) -> str:
    """
    Normalize model output to a plain JSON object string.

    Handles common formatting drift where the model wraps JSON in markdown
    code fences or adds short prose around the JSON object.
    """
    text = raw.strip()

    # Case 1: fenced code block (```json ... ``` or ``` ... ```)
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.IGNORECASE | re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Case 2: extra leading/trailing text around JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and start < end:
        text = text[start:end + 1].strip()

    return text

# ---------------------------------------------------------------------------
# Conversation class
# ---------------------------------------------------------------------------


class OpenRouterConversation:
    """
    A single LLM conversation session over the OpenRouter API.

    Usage::

        conv = OpenRouterConversation(
            system_prompt="You are a Cisco IOS configuration auditor."
        )
        resp = conv.send_prompt(initial_prompt)

        while resp.action == "request_context":
            context = prepare_context_prompt(resp, current_path, all_paths)
            resp = conv.send_prompt(context)

        print(resp.model_dump_json(indent=2))

    Parameters
    ----------
    api_key:
        OpenRouter API key.  If *None* the key is read from the
        ``OPENROUTER_API_KEY`` environment variable.
    model:
        Model identifier (e.g. ``"openai/gpt-5.4-nano"``).  Falls back to the
        ``OPENROUTER_MODEL`` environment variable or
        :data:`_DEFAULT_MODEL`.
    system_prompt:
        Optional system-level instruction prepended to the conversation.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        # Load .env if present
        load_dotenv()

        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self._api_key:
            raise RuntimeError(
                "OpenRouter API key is required. "
                "Set OPENROUTER_API_KEY in .env or pass api_key directly."
            )

        self._model = (
            model
            or os.environ.get("OPENROUTER_MODEL")
            or _DEFAULT_MODEL
        )

        self._client = OpenRouter(
            api_key=self._api_key
        )

        # Conversation history (plain dicts compatible with the SDK)
        self.messages: list[dict[str, Any]] = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

        # Last raw response string (before parsing)
        self._last_raw: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def last_raw(self) -> str | None:
        """The raw JSON string of the most recent assistant response."""
        return self._last_raw

    def send_prompt_raw(self, prompt: str) -> str:
        """
        Send a user message to the LLM and return the raw response string
        without parsing it into an :class:`~prompt_generator.AuditResponse`.

        The *prompt* and the assistant's reply are automatically appended to
        :attr:`messages`, preserving the conversation history for subsequent
        turns.

        Parameters
        ----------
        prompt:
            The user message to send.

        Returns
        -------
        str
            The raw JSON string returned by the LLM.

        Raises
        ------
        RuntimeError
            If the API call fails.
        """
        _logger.debug(
            "Model=%s | Prompt start\n%s\nPrompt end",
            self._model,
            prompt,
        )

        # 1. Append user message
        self.messages.append({"role": "user", "content": prompt})

        # 2. Call OpenRouter via the official SDK
        try:
            raw = self._call_api()
        except Exception as exc:
            # Remove the just-appended user message so the caller can retry
            self.messages.pop()
            raise RuntimeError(f"OpenRouter API call failed: {exc}") from exc

        # 3. Store raw output and append assistant response to history
        self._last_raw = raw
        self.messages.append({"role": "assistant", "content": raw})

        _logger.debug(
            "Model=%s | Raw response start\n%s\nRaw response end",
            self._model,
            raw,
        )

        return raw

    def send_prompt(self, prompt: str) -> AuditResponse:
        """
        Send a user message to the LLM and return a validated
        :class:`~prompt_generator.AuditResponse`.

        Internally calls :meth:`send_prompt_raw` and parses the result.

        The *prompt* and the assistant's reply are automatically appended to
        :attr:`messages`, preserving the conversation history for subsequent
        turns.

        Parameters
        ----------
        prompt:
            The user message to send.

        Returns
        -------
        AuditResponse
            Parsed and validated response from the LLM.

        Raises
        ------
        RuntimeError
            If the API call fails or the response cannot be parsed into a
            valid :class:`~prompt_generator.AuditResponse`.
        """
        raw = self.send_prompt_raw(prompt)
        normalized = _normalize_audit_response_json(raw)

        # Parse & validate
        try:
            return AuditResponse.model_validate_json(normalized)
        except Exception as exc:
            _logger.warning(
                "Failed to parse LLM response as AuditResponse. "
                "Raw content: %.200s",
                raw,
            )
            _logger.debug(
                "Model=%s | Normalized response candidate\n%s",
                self._model,
                normalized,
            )
            raise RuntimeError(
                f"LLM response could not be parsed as AuditResponse: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_api(self) -> str:
        """
        Perform the actual chat completion request using the OpenRouter SDK.

        Returns
        -------
        str
            The raw content string from the assistant's reply.
        """
        # Build response_format using the SDK's typed model
        response_format = FormatJSONObjectConfig(type="json_object")

        result = self._client.chat.send(
            model=self._model,
            messages=self.messages,  # type: ignore[arg-type]
            response_format=response_format,
        )

        # The response is a ChatResult (since stream=False by default).
        # ChatResult has .choices[0].message (.content).
        choice = result.choices[0]
        content = choice.message.content

        if content is None:
            raise RuntimeError(
                f"LLM returned empty content (finish_reason={choice.finish_reason})"
            )

        return content.strip()


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(name)s | %(message)s",
    )

    print("=" * 72)
    print("  OpenRouterConversation — Smoke Test")
    print("=" * 72)

    try:
        conv = OpenRouterConversation()

        # Demonstrate send_prompt_raw (returns string, no parsing)
        print("[1] send_prompt_raw (no AuditResponse parsing):")
        raw = conv.send_prompt_raw(
            'Respond with a valid AuditResponse JSON:\n'
            '{"action":"complete_analysis","requestedInfo":[],'
            '"hasIssue":false,"parameter":[],"reason":[]}'
        )
        print(f"    Raw output: {raw}")
        print(f"    Messages in history: {len(conv.messages)}\n")

        # Demonstrate send_prompt (parses into AuditResponse)
        print("[2] send_prompt (parsed AuditResponse):")
        parsed = conv.send_prompt(
            "Tell me what I asked you in the first message. "
            "Respond with a valid AuditResponse JSON."
        )
        print(f"    Parsed: {parsed.model_dump_json(indent=2)}")
        print(f"    Raw:    {conv.last_raw}")
        print(f"    Messages in history: {len(conv.messages)}\n")

        print(f"{'=' * 72}")
        print("  Smoke test passed!")
        print(f"{'=' * 72}")

    except RuntimeError as e:
        print(f"\nERROR: {e}")
        print("\nThis is expected if no OPENROUTER_API_KEY is configured.")
        print("Create a .env file based on .env.template and try again.")