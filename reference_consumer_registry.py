"""
reference_consumer_registry.py

A decorator-based registry for Reference Consumer command handlers.

Each handler is decorated with ``@register(command)`` and must accept a single
``arguments`` parameter (a list of strings) and return ``list[tuple[str, str]]``
representing the reference values consumed by the command.

Example::

    @register("ip access-group")
    def consume_ip_access_group(arguments: List[str]) -> List[Tuple[str, str]]:
        # arguments == ["100", "in"]
        return [("access-list", arguments[0])]
"""

from typing import Callable, List, Tuple

# Type alias for a consumer handler.
# Accepts the arguments from a ParsedLine, returns a list of (type, value) tuples.
ConsumerHandler = Callable[[List[str]], List[Tuple[str, str]]]

_REGISTRY: List[Tuple[str, ConsumerHandler]] = []


def register(command: str) -> Callable[[ConsumerHandler], ConsumerHandler]:
    """
    Decorator that registers a function as a Reference Consumer handler for the
    given *command*.

    The decorated function must accept a single ``arguments: List[str]``
    parameter and return ``list[tuple[str, str]]``.

    Args:
        command: The command string (e.g. ``"ip access-group"``) that this
                 handler should process.

    Returns:
        A decorator that appends the handler to the global registry.
    """

    def wrapper(fn: ConsumerHandler) -> ConsumerHandler:
        _REGISTRY.append((command, fn))
        return fn

    return wrapper


def get_consumer_handlers() -> List[Tuple[str, ConsumerHandler]]:
    """
    Return a copy of the registered consumer handlers.

    Returns:
        A list of ``(command, handler)`` tuples in registration order.
    """
    return list(_REGISTRY)