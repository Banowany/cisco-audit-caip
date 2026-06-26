"""
reference_provider_registry.py

A decorator-based registry for Reference Provider command handlers.

Each handler is decorated with ``@register(command)`` and must accept a single
``arguments`` parameter (a list of strings) and return ``list[tuple[str, str]]``
representing the reference values provided by the command.

Example::

    @register("access-list")
    def provide_access_list(arguments: List[str]) -> List[Tuple[str, str]]:
        # arguments == ["100", "permit", "ip", "any", "any"]
        return [("access-list", arguments[0])]
"""

from typing import Callable, List, Tuple

# Type alias for a provider handler.
# Accepts the arguments from a ParsedLine, returns a list of (type, value) tuples.
ProviderHandler = Callable[[List[str]], List[Tuple[str, str]]]

_REGISTRY: List[Tuple[str, ProviderHandler]] = []


def register(command: str) -> Callable[[ProviderHandler], ProviderHandler]:
    """
    Decorator that registers a function as a Reference Provider handler for the
    given *command*.

    The decorated function must accept a single ``arguments: List[str]``
    parameter and return ``list[tuple[str, str]]``.

    Args:
        command: The command string (e.g. ``"access-list"``) that this handler
                 should process.

    Returns:
        A decorator that appends the handler to the global registry.
    """

    def wrapper(fn: ProviderHandler) -> ProviderHandler:
        _REGISTRY.append((command, fn))
        return fn

    return wrapper


def get_provider_handlers() -> List[Tuple[str, ProviderHandler]]:
    """
    Return a copy of the registered provider handlers.

    Returns:
        A list of ``(command, handler)`` tuples in registration order.
    """
    return list(_REGISTRY)