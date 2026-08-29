"""
reference_consumers.py

Command-specific Reference Consumer handlers.

Each function is decorated with ``@register(command)`` from the
:mod:`reference_consumer_registry` module and defines what reference values
the corresponding command **consumes**.

Add a new handler here and register it to support additional commands as
consumers.
"""

import ipaddress
from typing import List

from models import ReferenceKey
from reference_consumer_registry import register


@register("ip access-group")
def consume_ip_access_group(arguments: List[str]) -> List[ReferenceKey]:
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
def consume_ip_nat(arguments: List[str]) -> List[ReferenceKey]:
    """
    Consume references from ``ip nat`` commands.

    - ``ip nat inside source list <acl-name> interface <intf> overload``
      consumes an Access List reference via ``<acl-name>`` and an Interface
      reference via ``<intf>``.
    - ``ip nat inside`` / ``ip nat outside`` (interface marking) consumes
      nothing.

    Args:
        arguments: The parsed arguments.

    Returns:
        A list containing the Access List and Interface references if the
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
        return [
            ("access-list", arguments[3]),
            ("interface", arguments[5]),
        ]

    return []


@register("access-class")
def consume_access_class(arguments: List[str]) -> List[ReferenceKey]:
    """
    ``access-class <acl-id-or-name> (in|out)`` consumes an Access List reference.

    Args:
        arguments: The parsed arguments, e.g. ``["110", "in"]``.

    Returns:
        A list with a single ``("access-list", <acl-id-or-name>)`` tuple.
    """
    if not arguments:
        return []
    return [("access-list", arguments[0])]


@register("network")
def consume_network(arguments: List[str]) -> List[ReferenceKey]:
    """
    Consume references from OSPF-style network statements.

    Pattern handled by parser:
    ``network <ip> <wildcard> area <area-id>``

    The statement consumes a network object represented as CIDR.
    """
    if len(arguments) < 4:
        return []
    if arguments[2] != "area":
        return []

    ip_str = arguments[0]
    wildcard_str = arguments[1]
    try:
        wildcard_octets = wildcard_str.split(".")
        if len(wildcard_octets) != 4:
            return []
        netmask = ".".join(str(255 - int(octet)) for octet in wildcard_octets)
        network = ipaddress.IPv4Network(f"{ip_str}/{netmask}", strict=False)
        return [("network", str(network))]
    except (ValueError, TypeError):
        return []


@register("ip route")
def consume_ip_route(arguments: List[str]) -> List[ReferenceKey]:
    """
    Consume references from static routes.

    Pattern handled by parser:
    ``ip route <destination> <mask> <next-hop-or-interface>``

    If the third argument is an interface name, return an interface reference.
    If it is an IP next-hop address, no reference is emitted.
    """
    if len(arguments) < 3:
        return []

    next_hop_or_interface = arguments[2]
    try:
        ipaddress.IPv4Address(next_hop_or_interface)
        return []
    except (ValueError, TypeError):
        return [("interface", next_hop_or_interface)]