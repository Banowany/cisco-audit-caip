"""
reference_extractor.py

Extracts reference values from parsed Cisco IOS configuration paths using
the consumer and provider registries.

Two functions are provided:

- :func:`extract_consumer_refs` — extracts references consumed by a path.
- :func:`extract_provider_refs` — extracts references provided by a path.

Each function iterates every :class:`ParsedLine` in the path, looks up the
command in the appropriate registry, and collects all returned reference
tuples.
"""

from typing import List, Tuple

from models import ParsedCiscoConfigPath
from reference_consumer_registry import get_consumer_handlers
from reference_provider_registry import get_provider_handlers


def extract_consumer_refs(
    path: ParsedCiscoConfigPath,
) -> List[Tuple[str, str]]:
    """
    Extract all reference values that the given *path* **consumes**.

    Every parsed line in the path is checked against the consumer registry.
    If a matching handler exists, its returned reference tuples are collected.

    Args:
        path: The parsed configuration path to analyze.

    Returns:
        A list of ``(type, value)`` tuples representing the references
        consumed by this path.  Returns an empty list if no references are
        consumed.
    """
    handlers = dict(get_consumer_handlers())
    references: List[Tuple[str, str]] = []

    for parsed_line in path.parsed_lines:
        handler = handlers.get(parsed_line.command)
        if handler is not None:
            references.extend(handler(parsed_line.arguments))

    return references


def extract_provider_refs(
    path: ParsedCiscoConfigPath,
) -> List[Tuple[str, str]]:
    """
    Extract all reference values that the given *path* **provides**.

    Every parsed line in the path is checked against the provider registry.
    If a matching handler exists, its returned reference tuples are collected.

    Args:
        path: The parsed configuration path to analyze.

    Returns:
        A list of ``(type, value)`` tuples representing the references
        provided by this path.  Returns an empty list if no references are
        provided.
    """
    handlers = dict(get_provider_handlers())
    references: List[Tuple[str, str]] = []

    for parsed_line in path.parsed_lines:
        handler = handlers.get(parsed_line.command)
        if handler is not None:
            references.extend(handler(parsed_line.arguments))

    return references