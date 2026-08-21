"""
reference_providers.py

Command-specific Reference Provider handlers.

Each function is decorated with ``@register(command)`` from the
:mod:`reference_provider_registry` module and defines what reference values
the corresponding command **provides**.

Add a new handler here and register it to support additional commands as
providers.
"""

from ipaddress import IPv4Address, IPv4Network
from typing import List

from models import ReferenceKey
from reference_provider_registry import register


@register("interface")
def provide_interface(arguments: List[str]) -> List[ReferenceKey]:
    """
    ``interface <name>`` provides an interface reference.

    Args:
        arguments: The parsed arguments, e.g. ``["GigabitEthernet0/1"]``.

    Returns:
        A list with a single ``("interface", <name>)`` tuple.
    """
    if not arguments:
        return []
    return [("interface", arguments[0])]


@register("access-list")
def provide_access_list(arguments: List[str]) -> List[ReferenceKey]:
    """
    ``access-list <acl-id> (remark|deny|permit) ...`` provides an Access List
    reference.

    Args:
        arguments: The parsed arguments, e.g. ``["100", "permit", "ip", "any",
                   "any"]``.

    Returns:
        A list with a single ``("access-list", <acl-id>)`` tuple.
    """
    if not arguments:
        return []
    return [("access-list", arguments[0])]


@register("ip access-list")
def provide_ip_access_list(arguments: List[str]) -> List[ReferenceKey]:
    """
    ``ip access-list (extended|standard) <acl-name>`` provides an Access List
    reference.

    Args:
        arguments: The parsed arguments, e.g. ``["extended", "MY_ACL"]``.

    Returns:
        A list with a single ``("access-list", <acl-name>)`` tuple.
    """
    if len(arguments) >= 2:
        return [("access-list", arguments[1])]
    return []


@register("ip address")
def provide_ip_address(arguments: List[str]) -> List[ReferenceKey]:
    """
    ``ip address <ip> <mask>`` provides a network reference.

    The network address is calculated from the IP and subnet mask, e.g.
    ``192.168.1.15 255.255.255.0`` → ``("network", "192.168.1.0/24")``.

    Args:
        arguments: The parsed arguments, e.g. ``["192.168.1.15",
                   "255.255.255.0"]``.

    Returns:
        A list with a single ``("network", "<network>/<prefix>")`` tuple,
        or an empty list if the arguments are insufficient or malformed.
    """
    if len(arguments) < 2:
        return []

    ip_str, mask_str = arguments[0], arguments[1]

    try:
        network = IPv4Network(f"{ip_str}/{mask_str}", strict=False)
        return [("network", str(network))]
    except (ValueError, TypeError):
        return []