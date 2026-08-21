"""
neighbor_key_generator.py

Generates a "Neighbor Key" for a parsed Cisco IOS configuration path.

The Neighbor Key determines which configuration paths are considered "neighbors"
of each other.  Two paths are neighbors iff they share the same Neighbor Key.

General rule
────────────
- For paths with more than one element, the Neighbor Key is the first (root)
  element of the path.
- For single-element paths, the default Neighbor Key is ``None``.

Special cases (e.g. Access Lists)
─────────────────────────────────
Single-element paths that represent an Access List entry produce a Neighbor Key
of the form ``"access-list <id>"`` so that all entries belonging to the same
ACL are grouped together even though there is no parent interface/block.
"""

from typing import Optional

from models import NeighborKey, ParsedCiscoConfigPath


def generate_neighbor_key(path: ParsedCiscoConfigPath) -> Optional[NeighborKey]:
    """
    Produce the Neighbor Key for a parsed configuration path.

    Args:
        path: The parsed configuration path to generate a key for.

    Returns:
        The Neighbor Key string, or ``None`` if no key applies.
    """
    # ── Special case: single-line Access List entry ──────────────────────
    # Produce a key like "access-list <id>" so that all entries belonging to
    # the same numbered ACL are grouped together.
    if (
        len(path.parsed_lines) == 1
        and path.parsed_lines[0].command == "access-list"
    ):
        args = path.parsed_lines[0].arguments
        if args:
            return f"access-list {args[0]}"
        return None

    # ── General case: multi-element paths → use the root (first) line ────
    # The full original line (e.g. "interface GigabitEthernet0/0") is used
    # so that only sub-paths sharing the same parent block are neighbors.
    if len(path.parsed_lines) > 1:
        return path.original_path.lines[0].strip()

    # ── Default: single-element, no special case → no key ────────────────
    return None