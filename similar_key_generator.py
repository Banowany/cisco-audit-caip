"""
similar_key_generator.py

Generates a "Similar Key" for a parsed Cisco IOS configuration path.

The Similar Key determines which configuration paths are considered "similar"
to each other.  Two paths are similar iff they share the same Similar Key.

Rule
────
- For paths with more than one element, the Similar Key is a tuple of
  (first_element_command, last_element_command), where each command is taken
  without arguments.
- For single-element paths, the Similar Key is a tuple of (command, command)
  (the command is duplicated).

Examples
────────
- ``["interface GigabitEthernet0/0", "ip address 192.168.1.1 255.255.255.0"]``
  → ``("interface", "ip address")``
- ``["access-list 101 permit ip any any"]`` → ``("access-list", "access-list")``
"""

from models import ParsedCiscoConfigPath, SimilarKey


def generate_similar_key(path: ParsedCiscoConfigPath) -> SimilarKey:
    """
    Produce the Similar Key for a parsed configuration path.

    Args:
        path: The parsed configuration path to generate a key for.

    Returns:
        A tuple ``(first_command, last_command)`` where each element is the
        command keyword (without arguments) of the first and last parsed line
        in the path respectively.

        For single-element paths the command is duplicated.
    """
    first_command = path.parsed_lines[0].command
    last_command = path.parsed_lines[-1].command

    return (first_command, last_command)