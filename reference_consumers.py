"""
reference_consumers.py

Command-specific Reference Consumer handlers.

Each function is decorated with ``@register(command)`` from the
:mod:`reference_consumer_registry` module and defines what reference values
the corresponding command **consumes**.

Add a new handler here and register it to support additional commands as
consumers.
"""

from typing import List, Tuple

from reference_consumer_registry import register


@register("ip access-group")
def consume_ip_access_group(arguments: List[str]) -> List[Tuple[str, str]]:
    """
    ``ip access-group <acl-id> (in|out)`` consumes an Access List reference.

    Args:
        arguments: The parsed arguments, e.g. ``["100", "in"]``.

    Returns:
        A list with a single ``("access-list", <acl-id>)`` tuple.
    """
    if not arguments:
        return []
    return [("access-list", arguments[0])]


@register("ip nat")
def consume_ip_nat(arguments: List[str]) -> List[Tuple[str, str]]:
    """
    Consume references from ``ip nat`` commands.

    - ``ip nat inside source list <acl-name> interface <intf> overload``
      consumes an Access List reference via ``<acl-name>``.
    - ``ip nat inside`` / ``ip nat outside`` (interface marking) consumes
      nothing.

    Args:
        arguments: The parsed arguments.

    Returns:
        A list with a single ``("access-list", <acl-name>)`` tuple if the
        pattern matches, otherwise an empty list.
    """
    # Pattern: inside source list <acl-name> interface <interface> overload
    if (
        len(arguments) >= 7
        and arguments[0] == "inside"
        and arguments[1] == "source"
        and arguments[2] == "list"
        and arguments[4] == "interface"
    ):
        return [("access-list", arguments[3])]

    return []