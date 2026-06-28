"""
audit_engine.py

Orchestrates a single-path Cisco IOS configuration audit using an LLM
conversation over OpenRouter.

One call to :func:`audit_single_path` = one conversation = one
:class:`~prompt_generator.AuditResponse`.

Workflow
--------
1. Create a new :class:`~openrouter_client.OpenRouterConversation`.
2. Send the initial analysis prompt (:func:`~prompt_generator.prepare_initial_prompt`).
3. If the LLM responds with ``action == "request_context"`` **and** no context
   has been sent yet:
   - Build a context prompt via
     :func:`~prompt_generator.prepare_context_prompt` and send it through the
     *same* conversation.
4. Return the final :class:`~prompt_generator.AuditResponse`.
"""

from __future__ import annotations

import logging
from typing import List

from models import ParsedCiscoConfigPath
from openrouter_client import OpenRouterConversation
from prompt_generator import (
    AuditResponse,
    prepare_context_prompt,
    prepare_initial_prompt,
)

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def audit_single_path(
    path: ParsedCiscoConfigPath,
    all_paths: List[ParsedCiscoConfigPath],
) -> AuditResponse:
    """
    Analyze a single configuration path using a dedicated LLM conversation.

    The function:

    * Creates a *new* :class:`~openrouter_client.OpenRouterConversation`
      (one conversation = one path).
    * Sends the initial analysis prompt built by
      :func:`~prompt_generator.prepare_initial_prompt`.
    * If the LLM responds with ``action == "request_context"``, sends **at
      most one** context message via the same conversation.
    * Returns the final :class:`~prompt_generator.AuditResponse`.

    Parameters
    ----------
    path:
        The parsed configuration path to audit.
    all_paths:
        Every parsed configuration path from the same configuration file.
        Used to provide context (neighbors, similar paths, references) when
        the LLM requests it.

    Returns
    -------
    AuditResponse
        The final analysis result from the LLM.

    Raises
    ------
    RuntimeError
        If the initial API call fails completely (after retries).
    """
    # ── 1. Create a fresh conversation ──────────────────────────────────────
    conv = OpenRouterConversation()

    # ── 2. Initial prompt ───────────────────────────────────────────────────
    initial_prompt = prepare_initial_prompt(path)
    _logger.info(
        "Sending initial prompt (len=%d chars) for path: %s",
        len(initial_prompt),
        _path_summary(path),
    )

    try:
        response = conv.send_prompt(initial_prompt)
    except RuntimeError:
        _logger.exception("Initial prompt failed for path: %s", _path_summary(path))
        raise

    _logger.debug("Initial response action=%s", response.action)

    # ── 3. Optional: send at most ONE context message ───────────────────────
    context_sent = False

    if response.action == "request_context" and not context_sent:
        context_prompt = prepare_context_prompt(response, path, all_paths)
        _logger.info(
            "Sending context prompt (len=%d chars) for path: %s",
            len(context_prompt),
            _path_summary(path),
        )

        try:
            response = conv.send_prompt(context_prompt)
        except RuntimeError:
            _logger.exception(
                "Context prompt failed for path: %s. "
                "Returning previous response as fallback.",
                _path_summary(path),
            )
            # Fallback: return the original response that requested context.
            # Mark it as 'complete_analysis' with hasIssue=None since we
            # couldn't finish the analysis.
            return AuditResponse(
                action="complete_analysis",
                hasIssue=None,
                parameter=[],
                reason=[
                    "Failed to retrieve requested context. "
                    "Analysis could not be completed."
                ],
            )

        context_sent = True

    # ── 4. If LLM still requests context after we already sent it ───────────
    # Graceful degradation: force-complete with a neutral result.
    if response.action == "request_context":
        _logger.warning(
            "LLM requested additional context after context already sent. "
            "Force-completing analysis for path: %s",
            _path_summary(path),
        )
        return AuditResponse(
            action="complete_analysis",
            requestedInfo=[],
            hasIssue=None,
            parameter=[],
            reason=[
                "Additional context was requested but the maximum of one "
                "context message has already been provided. "
                "Analysis completed without confirmation."
            ],
        )

    return response


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _path_summary(path: ParsedCiscoConfigPath) -> str:
    """Return a short human-readable summary of a config path."""
    return " --> ".join(path.original_path.lines)