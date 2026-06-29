"""
audit_engine.py

Orchestrates a single-path Cisco IOS configuration audit using an LLM
conversation over OpenRouter.

Provides two public functions:

- :func:`audit_single_path` — Analyze a path using a single LLM (original behavior).
- :func:`audit_single_path_ensemble` — Analyze a path using two different LLMs,
  then summarize their results with a third model.

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
import os
from typing import List

from dotenv import load_dotenv

from models import ParsedCiscoConfigPath
from openrouter_client import OpenRouterConversation
from prompt_generator import (
    AuditResponse,
    prepare_context_prompt,
    prepare_initial_prompt,
    prepare_summarization_prompt,
)

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def audit_single_path(
    path: ParsedCiscoConfigPath,
    all_paths: List[ParsedCiscoConfigPath],
    model: str | None = None,
) -> AuditResponse:
    """
    Analyze a single configuration path using a dedicated LLM conversation.

    This is a convenience wrapper around :func:`_run_single_audit` that uses
    the default model from configuration (``OPENROUTER_MODEL``).

    Parameters
    ----------
    path:
        The parsed configuration path to audit.
    all_paths:
        Every parsed configuration path from the same configuration file.
        Used to provide context (neighbors, similar paths, references) when
        the LLM requests it.
    model:
        Optional model identifier. If *None*, falls back to the
        ``OPENROUTER_MODEL`` environment variable.

    Returns
    -------
    AuditResponse
        The final analysis result from the LLM.

    Raises
    ------
    RuntimeError
        If the initial API call fails completely (after retries).
    """
    return _run_single_audit(path, all_paths, model)


def audit_single_path_ensemble(
    path: ParsedCiscoConfigPath,
    all_paths: List[ParsedCiscoConfigPath],
) -> AuditResponse:
    """
    Analyze a configuration path using two different AI models and summarize
    their results with a third model.

    The workflow:

    1. Run the audit with **Model 1** (``OPENROUTER_MODEL``).
    2. Run the audit with **Model 2** (``OPENROUTER_MODEL_2``).
    3. Send both results to the **Summarizer** model
       (``OPENROUTER_MODEL_SUMMARIZER``), which reconciles any disagreements
       and produces a single final :class:`AuditResponse`.

    If either individual analysis fails, the ensemble falls back to the
    successful analysis (or to an error response if both fail).

    Parameters
    ----------
    path:
        The parsed configuration path to audit.
    all_paths:
        Every parsed configuration path from the same configuration file.

    Returns
    -------
    AuditResponse
        The consolidated analysis result.
    """
    load_dotenv()

    model_1 = os.environ.get("OPENROUTER_MODEL")
    model_2 = os.environ.get("OPENROUTER_MODEL_2")
    model_summarizer = os.environ.get("OPENROUTER_MODEL_SUMMARIZER")

    # ── 1. Analysis from Model 1 ────────────────────────────────────────────
    _logger.info(
        "Ensemble [model_1=%s] for path: %s", model_1, _path_summary(path)
    )
    analysis_1 = _run_single_audit_safe(path, all_paths, model_1)

    # ── 2. Analysis from Model 2 ────────────────────────────────────────────
    _logger.info(
        "Ensemble [model_2=%s] for path: %s", model_2, _path_summary(path)
    )
    analysis_2 = _run_single_audit_safe(path, all_paths, model_2)

    # ── 3. Fallback: if either analysis failed, use the other ────────────────
    if analysis_1 is None and analysis_2 is None:
        _logger.error(
            "Both models failed for path: %s. Returning error response.",
            _path_summary(path),
        )
        return AuditResponse(
            action="complete_analysis",
            hasIssue=None,
            parameter=[],
            reason=[
                "Both analysis models failed. No valid audit result could be produced."
            ],
        )

    if analysis_1 is None:
        _logger.warning(
            "Model 1 failed for path: %s. Using Model 2 result only.",
            _path_summary(path),
        )
        # Ensure hasIssue is not None for the fallback
        result = analysis_2
        if result.hasIssue is None:
            result.hasIssue = False
        return result

    if analysis_2 is None:
        _logger.warning(
            "Model 2 failed for path: %s. Using Model 1 result only.",
            _path_summary(path),
        )
        result = analysis_1
        if result.hasIssue is None:
            result.hasIssue = False
        return result

    # ── 4. Summarization ─────────────────────────────────────────────────────
    _logger.info(
        "Ensemble [summarizer=%s] for path: %s", model_summarizer, _path_summary(path)
    )

    summary_prompt = prepare_summarization_prompt(path, analysis_1, analysis_2)

    try:
        conv = OpenRouterConversation(model=model_summarizer)
        final_response = conv.send_prompt(summary_prompt)
    except RuntimeError as exc:
        _logger.exception(
            "Summarization failed for path: %s. "
            "Falling back to Model 1 result.",
            _path_summary(path),
        )
        # Fallback: return Model 1's result
        final_response = analysis_1
        if final_response.hasIssue is None:
            final_response.hasIssue = False

    # Ensure hasIssue is always True/False, never None
    if final_response.hasIssue is None:
        final_response.hasIssue = False

    # Force action to complete_analysis (summarizer should always produce this)
    if final_response.action != "complete_analysis":
        _logger.warning(
            "Summarizer returned action=%s for path: %s. Forcing to complete_analysis.",
            final_response.action,
            _path_summary(path),
        )
        final_response.action = "complete_analysis"

    return final_response


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_single_audit(
    path: ParsedCiscoConfigPath,
    all_paths: List[ParsedCiscoConfigPath],
    model: str | None = None,
) -> AuditResponse:
    """
    Internal: run a single analysis conversation for one configuration path.

    This is the core conversation loop extracted from the original
    :func:`audit_single_path`.  It creates a fresh conversation, sends the
    initial prompt, optionally sends one context message, and returns the
    final :class:`AuditResponse`.

    Parameters
    ----------
    path:
        The parsed configuration path to audit.
    all_paths:
        Every parsed configuration path from the same configuration file.
    model:
        Optional model identifier. If *None* the default from configuration
        is used.

    Returns
    -------
    AuditResponse
        The final analysis result from the LLM.

    Raises
    ------
    RuntimeError
        If the initial API call fails completely.
    """
    # ── 1. Create a fresh conversation ──────────────────────────────────────
    conv = OpenRouterConversation(model=model)

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
            # Mark it as 'complete_analysis' with hasIssue=False since we
            # couldn't finish the analysis.
            return AuditResponse(
                action="complete_analysis",
                hasIssue=False,
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
            hasIssue=False,
            parameter=[],
            reason=[
                "Additional context was requested but the maximum of one "
                "context message has already been provided. "
                "Analysis completed without confirmation."
            ],
        )

    return response


def _run_single_audit_safe(
    path: ParsedCiscoConfigPath,
    all_paths: List[ParsedCiscoConfigPath],
    model: str | None = None,
) -> AuditResponse | None:
    """
    Run :func:`_run_single_audit` and return *None* on failure instead of
    raising.

    Parameters
    ----------
    path:
        The parsed configuration path to audit.
    all_paths:
        Every parsed configuration path from the same configuration file.
    model:
        Optional model identifier.

    Returns
    -------
    AuditResponse or None
        The response on success, *None* if the analysis failed.
    """
    try:
        return _run_single_audit(path, all_paths, model)
    except RuntimeError:
        _logger.exception(
            "Analysis failed for path: %s (model=%s)",
            _path_summary(path),
            model,
        )
        return None


def _path_summary(path: ParsedCiscoConfigPath) -> str:
    """Return a short human-readable summary of a config path."""
    return " --> ".join(path.original_path.lines)