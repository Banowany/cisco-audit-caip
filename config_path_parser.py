"""
config_path_parser.py

Parses each line of a CiscoConfigPath into structured ParsedLine objects using
a decorator-based parser registration system.

Each parser is a function decorated with ``@register(regex_pattern)`` that
receives a regex match object and returns a ``ParsedLine``.

Only commands from COMMAND_WHITELIST are registered as parsers.
"""

import re
from typing import Callable, List, Match

from models import CiscoConfigPath, ParsedCiscoConfigPath, ParsedLine


# ── Parser infrastructure ────────────────────────────────────────────────────


class CommandParser:
    """Binds a compiled regex pattern to a handler function."""

    def __init__(self, pattern: str, handler: Callable[[Match[str]], ParsedLine]):
        self.pattern = re.compile(pattern)
        self.handler = handler


PARSERS: List[CommandParser] = []


def register(pattern: str) -> Callable:
    """
    Decorator that registers a function as a parser for the given regex pattern.

    The decorated function must accept a single ``re.Match`` argument and return
    a ``ParsedLine``.

    Args:
        pattern: A regular expression string to match against a config line
                 (after stripping the leading ``no `` prefix).

    Returns:
        A decorator that appends a ``CommandParser`` to the global ``PARSERS`` list.
    """

    def wrapper(fn: Callable[[Match[str]], ParsedLine]) -> Callable:
        PARSERS.append(CommandParser(pattern, fn))
        return fn

    return wrapper


# ── Individual parsers (whitelist commands only) ─────────────────────────────


@register(r"^interface (\S+)$")
def parse_interface(m: Match[str]) -> ParsedLine:
    return ParsedLine(command="interface", arguments=[m.group(1)], is_started_with_no=False)


@register(r"^ip address (\S+) (\S+)$")
def parse_ip_address(m: Match[str]) -> ParsedLine:
    return ParsedLine(command="ip address", arguments=[m.group(1), m.group(2)], is_started_with_no=False)


@register(r"^ip address$")
def parse_ip_address_no_args(m: Match[str]) -> ParsedLine:
    return ParsedLine(command="ip address", arguments=[], is_started_with_no=False)


@register(r"^ip nat (\S+)$")
def parse_ip_nat(m: Match[str]) -> ParsedLine:
    return ParsedLine(command="ip nat", arguments=[m.group(1)], is_started_with_no=False)


@register(r"^ip nat inside source list (\S+) interface (\S+) overload$")
def parse_ip_nat_inside_source(m: Match[str]) -> ParsedLine:
    return ParsedLine(
        command="ip nat",
        arguments=["inside", "source", "list", m.group(1), "interface", m.group(2), "overload"],
        is_started_with_no=False,
    )


@register(r"^ip access-group (\S+) (in|out)$")
def parse_ip_access_group(m: Match[str]) -> ParsedLine:
    return ParsedLine(command="ip access-group", arguments=[m.group(1), m.group(2)], is_started_with_no=False)


@register(r"^ip access-list extended (\S+)$")
def parse_ip_access_list_extended(m: Match[str]) -> ParsedLine:
    return ParsedLine(command="ip access-list", arguments=["extended", m.group(1)], is_started_with_no=False)


@register(r"^ip access-list standard (\S+)$")
def parse_ip_access_list_standard(m: Match[str]) -> ParsedLine:
    return ParsedLine(command="ip access-list", arguments=["standard", m.group(1)], is_started_with_no=False)


@register(r"^access-list (\S+) (remark|deny|permit) (.+)$")
def parse_access_list(m: Match[str]) -> ParsedLine:
    return ParsedLine(
        command="access-list",
        arguments=[m.group(1), m.group(2)] + m.group(3).split(),
        is_started_with_no=False,
    )


@register(r"^permit (\S+) (.+)$")
def parse_permit(m: Match[str]) -> ParsedLine:
    return ParsedLine(command="permit", arguments=[m.group(1)] + m.group(2).split(), is_started_with_no=False)


@register(r"^deny (\S+) (.+)$")
def parse_deny(m: Match[str]) -> ParsedLine:
    return ParsedLine(command="deny", arguments=[m.group(1)] + m.group(2).split(), is_started_with_no=False)


@register(r"^shutdown$")
def parse_shutdown(m: Match[str]) -> ParsedLine:
    return ParsedLine(command="shutdown", arguments=[], is_started_with_no=False)


# ── Parsing logic ────────────────────────────────────────────────────────────


def parse_line(line: str) -> ParsedLine:
    """
    Parse a single configuration line into a ParsedLine.

    The function:
    1. Strips whitespace.
    2. Detects and removes a leading ``no `` prefix.
    3. Tries each registered parser in order.
    4. Returns the first matching result (with ``is_started_with_no`` set).
    5. Falls back to a generic first-token split if no parser matches.

    Args:
        line: A single configuration line (may contain leading/trailing whitespace).

    Returns:
        A ParsedLine with command, arguments, and is_started_with_no.
    """
    stripped = line.strip()

    # Detect and strip the leading "no "
    is_started_with_no = stripped.startswith("no ")
    if is_started_with_no:
        stripped = stripped[3:].strip()

    # Try each registered parser
    for parser in PARSERS:
        m = parser.pattern.match(stripped)
        if m:
            result = parser.handler(m)
            result.is_started_with_no = is_started_with_no
            return result

    # Fallback: use the first token as the command, rest as arguments
    tokens = stripped.split()
    if not tokens:
        return ParsedLine(command="", arguments=[], is_started_with_no=is_started_with_no)
    return ParsedLine(command=tokens[0], arguments=tokens[1:], is_started_with_no=is_started_with_no)


def parse_config_path(path: CiscoConfigPath) -> ParsedCiscoConfigPath:
    """
    Parse every line in a CiscoConfigPath into a ParsedCiscoConfigPath.

    Args:
        path: The original CiscoConfigPath to parse.

    Returns:
        A ParsedCiscoConfigPath containing the parsed lines and a reference
        to the original path.
    """
    parsed_lines = [parse_line(line) for line in path.lines]
    return ParsedCiscoConfigPath(
        parsed_lines=parsed_lines,
        original_path=path,
    )


def parse_config_paths(paths: List[CiscoConfigPath]) -> List[ParsedCiscoConfigPath]:
    """
    Parse a list of CiscoConfigPath objects into ParsedCiscoConfigPath objects.

    Args:
        paths: List of CiscoConfigPath objects.

    Returns:
        List of corresponding ParsedCiscoConfigPath objects.
    """
    return [parse_config_path(path) for path in paths]


# ── Demo / smoke-test when run directly ──────────────────────────────────────

if __name__ == "__main__":
    from config_path_extractor import extract_config_paths
    from config_path_filter import filter_paths_by_whitelist
    import sys

    if len(sys.argv) < 2:
        print("Usage: python config_path_parser.py <path_to_cisco_config>")
        sys.exit(1)

    filepath = sys.argv[1]
    all_paths = extract_config_paths(filepath)
    filtered_paths = filter_paths_by_whitelist(all_paths)

    print(f"Extracted {len(all_paths)} paths, filtered to {len(filtered_paths)} whitelist-matching paths from '{filepath}'\n")

    parsed_paths = parse_config_paths(filtered_paths)

    for i, pp in enumerate(parsed_paths, 1):
        print(f"--- Parsed ConfigPath #{i} ---")
        for j, pl in enumerate(pp.parsed_lines, 1):
            no_tag = "[no]" if pl.is_started_with_no else "   "
            args_str = " ".join(pl.arguments) if pl.arguments else ""
            print(f"  {j}. {no_tag} {pl.command} <{args_str}>")
        print(f"     (original: {' -> '.join(pp.original_path.lines)})\n")
