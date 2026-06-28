"""
main.py

CLI entry point for the Cisco IOS configuration audit tool.

Parses a configuration file, runs the audit engine on every extracted path,
and writes the results as JSON to a file.

Usage
-----
    python main.py <config_file> [-o <output_file>]

Examples
--------
    # Default output → example-router.audit.json
    python main.py example-router.conf

    # Custom output path
    python main.py example-router.conf -o results/my-audit.json

    # Pretty-print the result file with jq
    jq . example-router.audit.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

from config_path_extractor import extract_config_paths
from config_path_filter import filter_paths_by_whitelist
from config_path_parser import parse_config_paths
import reference_consumers  # noqa: F401 — registers reference consumers
import reference_providers  # noqa: F401 — registers reference providers

from audit_engine import audit_single_path
from prompt_generator import AuditResponse

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    # ── Logging setup ───────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(name)s | %(message)s",
    )

    # ── Parse arguments ─────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="Audit Cisco IOS configuration for issues using an LLM."
    )
    parser.add_argument(
        "config_file",
        help="Path to the Cisco IOS configuration file to audit.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help=(
            "Path to write the JSON results. "
            "Defaults to <config_file>.audit.json in the same directory "
            "as the config file."
        ),
    )
    args = parser.parse_args()

    config_file = args.config_file
    output_file = args.output

    # ── Pipeline: extract → filter → parse ──────────────────────────────────
    _logger.info("Extracting paths from %s ...", config_file)
    all_paths = extract_config_paths(config_file)
    _logger.info("Extracted %d paths.", len(all_paths))

    filtered_paths = filter_paths_by_whitelist(all_paths)
    _logger.info("Filtered to %d paths (whitelist match).", len(filtered_paths))

    parsed_paths = parse_config_paths(filtered_paths)
    _logger.info("Parsed %d paths.", len(parsed_paths))

    if not parsed_paths:
        _logger.warning("No paths to audit. Exiting.")
        sys.exit(0)

    # ── Run audit on every path ─────────────────────────────────────────────
    results: list[dict] = []
    total = len(parsed_paths)
    errors = 0

    _logger.info("Starting audit of %d path(s) ...", total)

    for idx, path in enumerate(parsed_paths, start=1):
        path_summary = " --> ".join(path.original_path.lines)
        _logger.info("[%d/%d] Auditing: %s", idx, total, path_summary)

        start_time = time.monotonic()

        try:
            response: AuditResponse = audit_single_path(path, parsed_paths)
        except RuntimeError as exc:
            _logger.error("[%d/%d] Audit failed for: %s — %s", idx, total, path_summary, exc)
            response = AuditResponse(
                action="complete_analysis",
                hasIssue=None,
                parameter=[],
                reason=[f"Audit failed with error: {exc}"],
            )
            errors += 1

        elapsed = time.monotonic() - start_time
        _logger.info(
            "[%d/%d] Done in %.1fs — action=%s hasIssue=%s",
            idx, total, elapsed, response.action, response.hasIssue,
        )

        results.append(
            {
                "path": path_summary,
                "elapsed_seconds": round(elapsed, 1),
                "response": response.model_dump(mode="json"),
            }
        )

    # ── Output results ──────────────────────────────────────────────────────
    output = {
        "config_file": config_file,
        "total_paths": total,
        "errors": errors,
        "results": results,
    }

    # Determine output file path
    if output_file is None:
        base, _ = os.path.splitext(config_file)
        output_file = f"{base}.audit.json"

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    _logger.info(
        "Audit complete: %d total, %d errors. Results written to %s",
        total,
        errors,
        output_file,
    )


if __name__ == "__main__":
    main()