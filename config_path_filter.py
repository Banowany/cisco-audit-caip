"""
config_path_filter.py

Filters a list of CiscoConfigPath objects, returning only those paths where all
lines (after stripping a leading "no " if present) match at least one command
from COMMAND_WHITELIST.
"""

from typing import List

from models import CiscoConfigPath


COMMAND_WHITELIST: List[str] = [
    "interface",
    "router ospf",
    "network",
    "ip route",
    "service password-encryption",
    "enable password",
    "enable secret",
    "line",
    "password",
    "login",
    "transport input",
    "access-class",
    "ip address",
    "ip access-group",
    "access-list",
    "ip access-list",
    "shutdown",
    "ip nat",
    "permit",
    "deny",
]


def _strip_no_prefix(line: str) -> str:
    """
    If *line* starts with ``"no "``, remove that prefix and return the rest.

    Args:
        line: A single configuration line (trimmed).

    Returns:
        The line without the leading ``"no "`` (or the original line if there
        is no such prefix).
    """
    if line.startswith("no "):
        return line[3:]
    return line


def _line_matches_whitelist(line: str, whitelist: List[str]) -> bool:
    """
    Check whether *line* starts with any of the entries in *whitelist*.

    Args:
        line: A single configuration line (trimmed).
        whitelist: List of command prefixes to match against.

    Returns:
        True if the line starts with at least one whitelist entry, else False.
    """
    for cmd in whitelist:
        if line.startswith(cmd):
            return True
    return False


def _check_line(line: str, whitelist: List[str]) -> bool:
    """
    Determine whether *line* is compliant with the whitelist.

    1. Strip the leading ``"no "`` if present.
    2. Check the resulting string against the whitelist.

    Args:
        line: A single configuration line (may have surrounding whitespace).
        whitelist: List of command prefixes to match against.

    Returns:
        True if the (possibly de-no'd) line matches the whitelist, else False.
    """
    stripped = line.strip()
    stripped = _strip_no_prefix(stripped)
    return _line_matches_whitelist(stripped, whitelist)


def filter_paths_by_whitelist(
    paths: List[CiscoConfigPath],
    whitelist: List[str] | None = None,
) -> List[CiscoConfigPath]:
    """
    Return only those *paths* where every line (after removing a leading ``"no "``)
    matches at least one entry in the whitelist.

    Args:
        paths: List of CiscoConfigPath objects to filter.
        whitelist: Optional custom whitelist.  Falls back to COMMAND_WHITELIST
                   if not provided.

    Returns:
        Filtered list of CiscoConfigPath objects.
    """
    if whitelist is None:
        whitelist = COMMAND_WHITELIST

    result: List[CiscoConfigPath] = []

    for path in paths:
        if all(_check_line(line, whitelist) for line in path.lines):
            result.append(path)

    return result


# ── Demo / smoke-test when run directly ──────────────────────────────────────

if __name__ == "__main__":
    from config_path_extractor import extract_config_paths

    import sys

    if len(sys.argv) < 2:
        print("Usage: python config_path_filter.py <path_to_cisco_config>")
        sys.exit(1)

    filepath = sys.argv[1]
    all_paths = extract_config_paths(filepath)

    print(f"Extracted {len(all_paths)} paths from '{filepath}'\n")

    filtered = filter_paths_by_whitelist(all_paths)
    print(f"Paths matching COMMAND_WHITELIST: {len(filtered)} / {len(all_paths)}\n")

    for i, path in enumerate(filtered, 1):
        print(f"  #{i}: {' -> '.join(path.lines)}")