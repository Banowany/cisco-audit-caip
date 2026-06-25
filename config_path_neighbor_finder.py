"""
config_path_neighbor_finder.py

Finds neighboring configuration paths within a list of parsed Cisco IOS
configuration paths.

Two paths are considered neighbors if they share the same Neighbor Key
(see :mod:`neighbor_key_generator`).
"""

from typing import List

from models import ParsedCiscoConfigPath
from neighbor_key_generator import generate_neighbor_key


def find_neighbors(
    current_parsed_config_path: ParsedCiscoConfigPath,
    all_parsed_config_paths: List[ParsedCiscoConfigPath],
) -> List[ParsedCiscoConfigPath]:
    """
    Return every parsed configuration path in *all_parsed_config_paths* that is
    a neighbor of *current_parsed_config_path*.

    The currently analyzed path itself is excluded from the result.

    Args:
        current_parsed_config_path: The currently analyzed configuration path.
        all_parsed_config_paths:  A list containing every parsed configuration
            path extracted from the Cisco IOS configuration.

    Returns:
        A list of neighboring parsed configuration paths.  If no neighbors
        exist, returns an empty list.
    """
    current_key = generate_neighbor_key(current_parsed_config_path)

    # If the current path has no Neighbor Key, it cannot have any neighbors.
    if current_key is None:
        return []

    neighbors: List[ParsedCiscoConfigPath] = []

    for candidate in all_parsed_config_paths:
        # Skip the currently analyzed path itself
        if candidate is current_parsed_config_path:
            continue

        candidate_key = generate_neighbor_key(candidate)
        if candidate_key is not None and candidate_key == current_key:
            neighbors.append(candidate)

    return neighbors


# ── Demo / smoke-test when run directly ──────────────────────────────────────

if __name__ == "__main__":
    from config_path_extractor import extract_config_paths
    from config_path_filter import filter_paths_by_whitelist
    from config_path_parser import parse_config_paths

    import sys

    if len(sys.argv) < 2:
        print("Usage: python config_path_neighbor_finder.py <path_to_cisco_config>")
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
        neighbors = find_neighbors(pp, parsed_paths)

        print(f"--- Parsed ConfigPath #{i} ---")
        print(f"  Path: {original}")
        print(f"  Neighbor Key: {generate_neighbor_key(pp)!r}")
        print(f"  Neighbors ({len(neighbors)}):")
        if neighbors:
            for n in neighbors:
                print(f"    - {' -> '.join(n.original_path.lines)}")
        else:
            print(f"    (none)")
        print()
