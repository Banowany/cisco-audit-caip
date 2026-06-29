"""
config_path_reference_finder.py

Finds reference-related configuration paths within a list of parsed Cisco IOS
configuration paths.

Two paths are considered reference-related if the currently analyzed path
**consumes** one or more references that a candidate path **provides**.

The algorithm extracts consumer references from the current path, then scans
all other paths for matching provider references.
"""

from typing import List

from models import ParsedCiscoConfigPath
from reference_extractor import extract_consumer_refs, extract_provider_refs


def find_reference_related(
    current_parsed_config_path: ParsedCiscoConfigPath,
    all_parsed_config_paths: List[ParsedCiscoConfigPath],
) -> List[ParsedCiscoConfigPath]:
    """
    Return every parsed configuration path in *all_parsed_config_paths* that is
    reference-related to *current_parsed_config_path*.

    The algorithm:

    1. Extract all reference values consumed by the current path.
    2. Iterate through every candidate path.
    3. Skip the currently analyzed path.
    4. Extract all reference values provided by the candidate path.
    5. If at least one identical ``(type, value)`` tuple exists in both
       collections, the candidate is considered reference-related.
    6. Return the list of all matching paths.

    Args:
        current_parsed_config_path: The currently analyzed configuration path
            (treated as the Reference Consumer).
        all_parsed_config_paths: A list containing every parsed configuration
            path extracted from the Cisco IOS configuration.

    Returns:
        A list of reference-related parsed configuration paths.  If no related
        paths exist, returns an empty list.
    """
    consumer_refs = extract_consumer_refs(current_parsed_config_path)

    # If the current path consumes no references, it cannot have any
    # reference-related paths.
    if not consumer_refs:
        return []

    consumer_refs_set = set(consumer_refs)

    related: List[ParsedCiscoConfigPath] = []

    for candidate in all_parsed_config_paths:
        # Skip the currently analyzed path itself
        if candidate is current_parsed_config_path:
            continue

        provider_refs = extract_provider_refs(candidate)
        if not provider_refs:
            continue

        provider_refs_set = set(provider_refs)

        # If at least one reference matches, consider the candidate related
        if consumer_refs_set & provider_refs_set:
            related.append(candidate)

    return related


def find_reference_consumers(
    current_parsed_config_path: ParsedCiscoConfigPath,
    all_parsed_config_paths: List[ParsedCiscoConfigPath],
) -> List[ParsedCiscoConfigPath]:
    """
    Return every parsed configuration path in *all_parsed_config_paths* that
    **consumes** references **provided** by *current_parsed_config_path*.

    This is the reverse of :func:`find_reference_related`: given a path that
    **defines** configuration objects, find all paths that **use** those
    objects.

    The algorithm:

    1. Extract all reference values provided (defined) by the current path.
    2. Iterate through every candidate path.
    3. Skip the currently analyzed path.
    4. Extract all reference values consumed by the candidate path.
    5. If at least one identical ``(type, value)`` tuple exists in both
       collections, the candidate is considered a consumer of the current path.
    6. Return the list of all matching paths.

    Args:
        current_parsed_config_path: The currently analyzed configuration path
            (treated as the Reference Provider).
        all_parsed_config_paths: A list containing every parsed configuration
            path extracted from the Cisco IOS configuration.

    Returns:
        A list of consumer parsed configuration paths.  If no consumers exist,
        returns an empty list.
    """
    provider_refs = extract_provider_refs(current_parsed_config_path)

    # If the current path provides no references, it cannot have any consumers.
    if not provider_refs:
        return []

    provider_refs_set = set(provider_refs)

    consumers: List[ParsedCiscoConfigPath] = []

    for candidate in all_parsed_config_paths:
        # Skip the currently analyzed path itself
        if candidate is current_parsed_config_path:
            continue

        consumer_refs = extract_consumer_refs(candidate)
        if not consumer_refs:
            continue

        consumer_refs_set = set(consumer_refs)

        # If at least one reference matches, the candidate consumes what we define
        if provider_refs_set & consumer_refs_set:
            consumers.append(candidate)

    return consumers


# ── Demo / smoke-test when run directly ──────────────────────────────────────

if __name__ == "__main__":
    from config_path_extractor import extract_config_paths
    from config_path_filter import filter_paths_by_whitelist
    from config_path_parser import parse_config_paths

    import sys

    if len(sys.argv) < 2:
        print("Usage: python config_path_reference_finder.py <path_to_cisco_config>")
        sys.exit(1)

    filepath = sys.argv[1]
    all_paths = extract_config_paths(filepath)
    filtered_paths = filter_paths_by_whitelist(all_paths)
    parsed_paths = parse_config_paths(filtered_paths)

    # Import consumer and provider handlers so they get registered
    # (importing the modules triggers the @register decorators)
    import reference_consumers  # noqa: F401
    import reference_providers  # noqa: F401

    print(
        f"Extracted {len(all_paths)} paths, "
        f"filtered to {len(filtered_paths)} whitelist-matching paths "
        f"from '{filepath}'\n"
    )

    for i, pp in enumerate(parsed_paths, 1):
        original = " -> ".join(pp.original_path.lines)
        related = find_reference_related(pp, parsed_paths)
        consumers = find_reference_consumers(pp, parsed_paths)

        print(f"--- Parsed ConfigPath #{i} ---")
        print(f"  Path: {original}")
        consumer_refs = extract_consumer_refs(pp)
        print(f"  Consumer Refs: {consumer_refs!r}")
        print(f"  Provider Refs: {extract_provider_refs(pp)!r}")
        print(f"  Reference-Related (who defines what I consume) ({len(related)}):")
        if related:
            for n in related:
                provider_refs = extract_provider_refs(n)
                print(f"    - {' -> '.join(n.original_path.lines)}")
                print(f"      (provides: {provider_refs!r})")
        else:
            print(f"    (none)")
        print(f"  Reference-Consumers (who uses what I define) ({len(consumers)}):")
        if consumers:
            for n in consumers:
                consumer_refs_n = extract_consumer_refs(n)
                print(f"    - {' -> '.join(n.original_path.lines)}")
                print(f"      (consumes: {consumer_refs_n!r})")
        else:
            print(f"    (none)")
        print()
