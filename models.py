from pydantic import BaseModel
from typing import List, Optional, Tuple


NeighborKey = str
SimilarKey = Tuple[str, str]
ReferenceKey = Tuple[str, str]


class CiscoConfigPath(BaseModel):
    """
    Represents a single root-to-leaf config path extracted from a Cisco
    configuration file.

    Attributes:
        lines: The ordered list of configuration lines from the root of the
               config tree down to a leaf node.  Each line is stored as a
               raw string exactly as it appears in the source file.
    """
    lines: List[str]


class ParsedLine(BaseModel):
    """
    Represents a single parsed configuration line.

    Attributes:
        command: The command keyword (as found in the whitelist) without any ``no`` prefix.
        arguments: The remaining tokens after the command, split by whitespace.
        is_started_with_no: Whether the original line started with ``no ``.
    """
    command: str
    arguments: List[str]
    is_started_with_no: bool


class ParsedCiscoConfigPath(BaseModel):
    """
    Represents a parsed version of a CiscoConfigPath.

    Attributes:
        parsed_lines: The list of ParsedLine objects corresponding to each
                      original, meaningful line in the config path.
        original_path: The original CiscoConfigPath that was parsed.
    """
    parsed_lines: List[ParsedLine]
    original_path: CiscoConfigPath