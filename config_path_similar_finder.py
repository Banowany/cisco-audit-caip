"""
config_path_similar_finder.py

Finds similar configuration paths within a list of parsed Cisco IOS
configuration paths.

Two paths are considered similar if they share the same Similar Key
(see :mod:`similar_key_generator`).
"""

from typing import List

from models import ParsedCiscoConfigPath
from similar_key_generator import generate_similar_key


def find_similar(
    current_parsed_config_path: ParsedCiscoConfigPath,
    all_parsed_config_paths: List[ParsedCiscoConfigPath],
) -> List[ParsedCiscoConfigPath]:
    """
    Return every parsed configuration path in *all_parsed_config_paths* that is
    similar to *current_parsed_config_path*.

    The currently analyzed path itself is excluded from the result.

    Args:
        current_parsed_config_path: The currently analyzed configuration path.
        all_parsed_config_paths:  A list containing every parsed configuration
            path extracted from the Cisco IOS configuration.

    Returns:
        A list of similar parsed configuration paths.  If no similar paths
        exist, returns an empty list.
    """
    current_key = generate_similar_key(current_parsed_config_path)

    similar_paths: List[ParsedCiscoConfigPath] = []

    for candidate in all_parsed_config_paths:
        # Skip the currently analyzed path itself
        if candidate is current_parsed_config_path:
            continue

        candidate_key = generate_similar_key(candidate)
        if candidate_key == current_key:
            similar_paths.append(candidate)

    return similar_paths


# ── Demo / smoke-test when run directly ──────────────────────────────────────

if __name__ == "__main__":
    from config_path_extractor import extract_config_paths
    from config_path_filter import filter_paths_by_whitelist
    from config_path_parser import parse_config_paths

    import sys

    if len(sys.argv) < 2:
        print("Usage: python config_path_similar_finder.py <path_to_cisco_config>")
        sys.exit(1)

    filepath = sys.argv[1]
    all_paths = extract_config_paths(filepath)
    filtered_paths = filter_paths_by_whitelist(all_paths)
    parsed_paths = parse_config_paths(filtered_paths)

    print(
        f"Extracted {len(all_paths)} paths, "
        f"filtered to {len(filtered_paths)} whitelist-matching paths "
        f"from '{filepath}'\n"
    )

    for i, pp in enumerate(parsed_paths, 1):
        original = " -> ".join(pp.original_path.lines)
        similar = find_similar(pp, parsed_paths)

        print(f"--- Parsed ConfigPath #{i} ---")
        print(f"  Path: {original}")
        print(f"  Similar Key: {generate_similar_key(pp)!r}")
        print(f"  Similar ({len(similar)}):")
        if similar:
            for n in similar:
                print(f"    - {' -> '.join(n.original_path.lines)}")
        else:
            print(f"    (none)")
        print()