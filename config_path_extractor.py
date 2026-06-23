"""
config_path_extractor.py

Extracts all possible config paths (root-to-leaf) from a Cisco router configuration file
using ciscoconfparse2.

A config path is defined as the sequence of lines from the root of the config tree
down to a leaf node (a line with no children). Comments ('!'), blank lines, and
non-configuration metadata lines are excluded.
"""

from pathlib import Path
from typing import List

from ciscoconfparse2 import CiscoConfParse

from models import CiscoConfigPath


def extract_config_paths(filepath: str | Path, syntax: str = "ios") -> List[CiscoConfigPath]:
    """
    Parse a Cisco router configuration file and extract all root-to-leaf config paths.

    Args:
        filepath: Path to the Cisco configuration file.
        syntax: Configuration syntax type (default: 'ios').

    Returns:
        A list of CiscoConfigPath objects, each containing the ordered lines
        from the root of the config tree to a leaf node.
    """
    parse = CiscoConfParse(str(filepath), syntax=syntax)

    config_paths: List[CiscoConfigPath] = []

    for line in parse.find_objects(r".*"):
        # Skip comments, blank lines, and non-configuration metadata
        if line.is_comment:
            continue

        text = line.text.strip()
        if not text:
            continue
        if text in ("end", "Building configuration...") or text.startswith("Current configuration"):
            continue

        # A leaf is a line with no children
        if not line.has_children:
            # Use geneology_text to get the full path from root to this leaf
            path_lines = line.geneology_text
            config_paths.append(CiscoConfigPath(lines=path_lines))

    return config_paths


def print_config_paths(paths: List[CiscoConfigPath]) -> None:
    """Pretty-print extracted config paths."""
    for i, path in enumerate(paths, 1):
        print(f"ConfigPath #{i}: {'->'.join(path.lines)}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python config_path_extractor.py <path_to_cisco_config>")
        sys.exit(1)

    filepath = sys.argv[1]
    paths = extract_config_paths(filepath)

    print(f"Found {len(paths)} config paths in '{filepath}':\n")
    print_config_paths(paths)