"""
prompt_generator.py

Prepares LLM prompts for Cisco IOS configuration auditing.

Two methods are provided:

- :func:`prepare_initial_prompt` — Builds the initial analysis prompt for a
  single configuration path.
- :func:`prepare_context_prompt` — Builds a follow-up context prompt based on
  the LLM's previous response, fetching only the context types requested.

Prompt texts are embedded directly in this module (no external template files).
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from config_path_neighbor_finder import find_neighbors
from config_path_reference_finder import find_reference_consumers, find_reference_related
from config_path_similar_finder import find_similar
from models import ParsedCiscoConfigPath


# ── LLM Response Model ────────────────────────────────────────────────────────


class AuditResponse(BaseModel):
    """
    Pydantic model representing the JSON response expected from the LLM.

    Attributes:
        action: Either ``"request_context"`` or ``"complete_analysis"``.
        requestedInfo: A list of integers ``[1, 2, 3, 4]`` indicating which
            context types are needed (only relevant when action is
            ``"request_context"``).
        hasIssue: ``True``, ``False``, or ``None`` (only relevant when action
            is ``"complete_analysis"``).
        parameter: List of problematic configuration parameters.
        reason: List of explanation strings.
    """
    action: str  # "request_context" | "complete_analysis"
    requestedInfo: List[int] = []
    hasIssue: Optional[bool] = None
    parameter: List[str] = []
    reason: List[str] = []


# ── Embedded Prompt Templates ─────────────────────────────────────────────────

_INITIAL_PROMPT_TEMPLATE = """\
I have a configuration path extracted from a Cisco IOS running configuration and need to determine whether it contains any configuration issues.

**Configuration Path Under Review:**

```text
{{CONFIG_PATH}}
```

Analyze the provided configuration path for potential issues strictly within the following four categories:

1. **Syntax & Lexical Errors**

   * Invalid Cisco IOS command syntax.
   * Typographical errors.
   * Use of commands or syntax not supported by Cisco IOS (e.g., CIDR notation `/24` instead of a dotted-decimal subnet mask where Cisco IOS expects one).

2. **Structural & Reference Errors**

   * References to undefined configuration objects (e.g., ACLs, prefix-lists, route-maps, policy objects).
   * Configuration objects that are defined but never referenced.

3. **Attribute & Local Conflict Errors**

   * Local hardware or logical conflicts within the device configuration.
   * Examples include overlapping IP subnets on different interfaces, routing protocols configured on administratively shut down interfaces, or other locally detectable configuration inconsistencies.

4. **Security Policy & Control Logic Errors**

   * Security weaknesses or logical policy errors.
   * Examples include weak credential mechanisms, unsecured management access, or ACL shadowing where a broader rule unintentionally overrides a more specific rule.

## Analysis Rules

* Always attempt to determine whether the configuration path contains a confirmed issue using only the provided information.
* Do **not** infer missing configuration or assume an issue without sufficient evidence.
* If the provided configuration path is sufficient to confidently determine whether an issue exists, do **not** request additional context.
* Request additional context **only if it is necessary to confidently confirm or reject a potential issue.**
* Request **only the minimum amount of contextual information required** to continue the analysis.
* If a potential issue cannot be confirmed or rejected using the current configuration path alone, request the appropriate contextual information instead of guessing.

## Additional Context Available

If additional context is required, you may request one or more of the following:

**(1) Neighboring Configuration Paths**

* Useful for verifying parent context, interface state, nearby configuration logic, and relationships between adjacent configuration commands.

**(2) Similar Configuration Paths**

* Useful for detecting inconsistencies between similar configuration objects, such as overlapping IP subnets or inconsistent interface configurations.

**(3) Referenced Configuration Paths**

* Useful for verifying whether referenced configuration objects (e.g., ACLs, prefix-lists, route-maps, policy objects) are actually defined.

**(4) Reference Consumer Paths**

* Useful for verifying whether configuration objects defined by the currently analyzed path are actually used (consumed) elsewhere in the configuration.

## Response Format

Respond **only** with a valid JSON object having the following structure:

```json
{
  "action": "request_context" | "complete_analysis",
  "requestedInfo": [],
  "hasIssue": null,
  "parameter": [],
  "reason": []
}
```

### Field Definitions

#### `action`

* `"complete_analysis"` — Use when the provided information is sufficient to complete the analysis.
* `"request_context"` — Use when additional contextual information is required before reaching a reliable conclusion.

#### `requestedInfo`

* Used only when `action` is `"request_context"`.
* Contains one or more values selected only from `[1, 2, 3, 4]`.
* Leave empty when `action` is `"complete_analysis"`.

#### `hasIssue`

* Used only when `action` is `"complete_analysis"`.
* `true` if one or more configuration issues are confirmed.
* `false` if no configuration issues are found.
* `null` when `action` is `"request_context"`.

#### `parameter`

* Used only when `action` is `"complete_analysis"`.
* Contains only configuration parameters that are confirmed to be problematic.
* Leave empty if no issues are detected or when requesting additional context.

#### `reason`

* When `action` is `"complete_analysis"`, explain each confirmed issue.
* When `action` is `"request_context"`, explain:

  * what additional information is required,
  * why it is required,
  * which misconfiguration category it is intended to verify.

## Output Requirements

* Produce **only** the JSON object.
* Do not output Markdown.
* Do not output explanatory text outside the JSON object.
* Do not invent missing configuration.
* Do not assume a configuration issue without sufficient evidence.
* Request additional context only when it is strictly necessary to reach a reliable conclusion.
* Populate only the fields relevant to the selected `action`; unused fields should remain empty or `null` as specified above.

## Examples

The following examples illustrate the expected reasoning process and JSON output format. They are examples only and **must not influence the analysis of the provided configuration path**.

### Example 1 – Confirmed Local Syntax Error

**Configuration Path**

```text
interface GigabitEthernet0/0 --> ip address 192.168.1.1/24
```

**Output**

```json
{
  "action": "complete_analysis",
  "requestedInfo": [],
  "hasIssue": true,
  "parameter": [
    "ip address"
  ],
  "reason": [
    "CIDR notation is not valid Cisco IOS syntax for the ip address command."
  ]
}
```

---

### Example 2 – Referenced Object Must Be Verified

**Configuration Path**

```text
interface GigabitEthernet0/0 --> ip access-group 100 in
```

**Output**

```json
{
  "action": "request_context",
  "requestedInfo": [
    3
  ],
  "hasIssue": null,
  "parameter": [],
  "reason": [
    "The referenced ACL must be verified to determine whether it is defined. This is required to evaluate a potential Structural & Reference Error."
  ]
}
```

---

### Example 3 – Neighboring Context Required

**Configuration Path**

```text
interface GigabitEthernet0/0 --> ip ospf 1 area 0
```

**Output**

```json
{
  "action": "request_context",
  "requestedInfo": [
    1
  ],
  "hasIssue": null,
  "parameter": [],
  "reason": [
    "Neighboring configuration paths are required to determine whether the interface is administratively shut down. This is necessary to evaluate a potential Attribute & Local Conflict Error."
  ]
}
```

---

### Example 4 – No Issues Detected

**Configuration Path**

```text
interface GigabitEthernet0/0 --> duplex auto
```

**Output**

```json
{
  "action": "complete_analysis",
  "requestedInfo": [],
  "hasIssue": false,
  "parameter": [],
  "reason": []
}
```

---

### Example 5 – Reference Consumer Context Required

**Configuration Path**

```text
access-list 100 permit ip any any
```

**Output**

```json
{
  "action": "request_context",
  "requestedInfo": [
    4
  ],
  "hasIssue": null,
  "parameter": [],
  "reason": [
    "The ACL defined by this path must be verified to determine whether it is actually referenced by any other configuration path. This is required to evaluate a potential Structural & Reference Error (defined but never referenced)."
  ]
}
```"""

_CONTEXT_PROMPT_INTRO = """\
The following configuration paths provide the additional context you requested for the current analysis.

Use this information together with the original configuration path to refine your analysis. Treat these paths as supplementary context only. Do not analyze them independently unless they help explain or validate the currently analyzed configuration path."""

_CONTEXT_PROMPT_CLOSING = """\
Update your previous reasoning using this additional context. If the new context changes your conclusions, explain why. Otherwise, preserve your previous conclusions and continue the analysis based on the additional information.

**Important:** If you requested **Reference Provider Context** (type 3) and the section shows **"Nothing found"**, this means the referenced configuration object(s) are confirmed **not defined** anywhere in the configuration. This is a definitive absence.

**Important:** If you requested **Reference Consumer Context** (type 4) and the section shows **"Nothing found"**, this means the configuration object(s) defined by the currently analyzed path are **not consumed** by any other path in the configuration. This may indicate unused (orphan) configuration objects."""

# Section definitions: (title, description)
_SECTION_DEFINITIONS: dict[int, tuple[str, str]] = {
    1: (
        "Neighbor Context",
        "These paths belong to the same local configuration context as the "
        "currently analyzed path.",
    ),
    2: (
        "Similar Context",
        "These paths are structurally or semantically similar to the currently "
        "analyzed path. Use them to identify configuration inconsistencies, "
        "deviations, or unusual patterns.",
    ),
    3: (
        "Reference Provider Context",
        "These paths define configuration objects that may be referenced by "
        "the currently analyzed configuration path.",
    ),
    4: (
        "Reference Consumer Context",
        "These paths reference (consume) configuration objects defined by "
        "the currently analyzed configuration path.",
    ),
}

_FETCH_FUNCTIONS: dict[int, callable] = {
    1: find_neighbors,
    2: find_similar,
    3: find_reference_related,
    4: find_reference_consumers,
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _path_to_display(path: ParsedCiscoConfigPath) -> str:
    """Convert a ParsedCiscoConfigPath to its human-readable string form."""
    return " --> ".join(path.original_path.lines)


def _format_path_list(paths: List[ParsedCiscoConfigPath]) -> str:
    """
    Format a list of parsed config paths as a bulleted code-block body.

    Returns:
        A string with one ``- path --> subcommand`` per line, or
        ``"Nothing found."`` if the list is empty.
    """
    if not paths:
        return "Nothing found."
    lines = []
    for p in paths:
        lines.append(f"- {_path_to_display(p)}")
    return "\n".join(lines)


# ── Summarization Prompt ──────────────────────────────────────────────────────


_SUMMARIZATION_PROMPT_TEMPLATE = """\
You are a senior Cisco IOS auditor. Below is a configuration path and two prior analysis results. Review them, then produce your own final consolidated analysis.

**Configuration Path Under Review:**

```text
{{CONFIG_PATH}}
```

**Prior Analysis Results:**

```json
{{ANALYSIS_1}}
```

```json
{{ANALYSIS_2}}
```

## Instructions

1. Review both prior analyses as input data.
2. Perform your own complete analysis of the configuration path itself.
3. Produce a single final result in the JSON format specified below.

## Response Format

Respond **only** with a valid JSON object having the following structure:

```json
{
  "action": "complete_analysis",
  "requestedInfo": [],
  "hasIssue": true,
  "parameter": [],
  "reason": []
}
```

### Field Definitions

#### `action`
* Must be `"complete_analysis"` — you have all the information needed to produce the final result.

#### `hasIssue`
* `true` if one or more configuration issues are confirmed.
* `false` if no configuration issues are found.

#### `parameter`
* Contains only configuration parameters that are confirmed to be problematic.

#### `reason`
* Explain the final conclusion in your own words, addressing the specific issues found.

## Output Requirements

* Produce **only** the JSON object.
* Do not output Markdown.
* Do not output explanatory text outside the JSON object.
* Populate only the fields relevant to the selected `action`; unused fields should remain empty as specified above."""


# ── Public Methods ────────────────────────────────────────────────────────────


def prepare_initial_prompt(path: ParsedCiscoConfigPath) -> str:
    """
    Build the initial LLM prompt for analyzing a single configuration path.

    Args:
        path: The parsed configuration path to analyze.

    Returns:
        A fully formatted prompt string with ``{{CONFIG_PATH}}`` replaced
        by the path's human-readable representation.
    """
    display_path = _path_to_display(path)
    return _INITIAL_PROMPT_TEMPLATE.replace("{{CONFIG_PATH}}", display_path)


def prepare_context_prompt(
    response: AuditResponse,
    current_path: ParsedCiscoConfigPath,
    all_paths: List[ParsedCiscoConfigPath],
) -> str:
    """
    Build a follow-up context prompt based on the LLM's previous response.

    Only the context types listed in ``response.requestedInfo`` are fetched
    and included in the output.  The method internally calls the appropriate
    finder functions (e.g. :func:`~config_path_neighbor_finder.find_neighbors`)
    for each requested type, so the caller does not need to pre-compute them.

    Args:
        response: The parsed ``AuditResponse`` from the LLM.  Its
            ``requestedInfo`` field determines which context sections to
            include.
        current_path: The current configuration path being analyzed.
        all_paths: Every parsed configuration path extracted from the Cisco
            IOS configuration file.

    Returns:
        A fully formatted context prompt string containing only the
        requested context sections.
    """
    # Build the requested sections
    sections: List[str] = []

    for info_code in sorted(response.requestedInfo):
        if info_code not in _SECTION_DEFINITIONS:
            continue

        title, description = _SECTION_DEFINITIONS[info_code]
        fetch_fn = _FETCH_FUNCTIONS[info_code]

        # Fetch the relevant paths
        found_paths = fetch_fn(current_path, all_paths)
        # Remove the current path from the results if it appears
        found_paths = [p for p in found_paths if p is not current_path]

        formatted = _format_path_list(found_paths)

        section = (
            f"## {title}\n\n"
            f"{description}\n\n"
            f"```text\n{formatted}\n```"
        )
        sections.append(section)

    # Assemble the final prompt
    parts: List[str] = [_CONTEXT_PROMPT_INTRO]
    parts.extend(sections)
    parts.append(_CONTEXT_PROMPT_CLOSING)

    return "\n\n".join(parts)


def prepare_summarization_prompt(
    path: ParsedCiscoConfigPath,
    analysis_1: AuditResponse,
    analysis_2: AuditResponse,
) -> str:
    """
    Build a prompt for the summarizer model that reconciles two independent
    audit results into a single consolidated :class:`AuditResponse`.

    Args:
        path:
            The parsed configuration path that was audited.
        analysis_1:
            The :class:`AuditResponse` from the first analysis model.
        analysis_2:
            The :class:`AuditResponse` from the second analysis model.

    Returns:
        A fully formatted summarization prompt string with placeholders
        replaced by the actual config path and the two JSON responses.
    """
    display_path = _path_to_display(path)
    prompt = _SUMMARIZATION_PROMPT_TEMPLATE.replace("{{CONFIG_PATH}}", display_path)
    prompt = prompt.replace(
        "{{ANALYSIS_1}}",
        analysis_1.model_dump_json(indent=2),
    )
    prompt = prompt.replace(
        "{{ANALYSIS_2}}",
        analysis_2.model_dump_json(indent=2),
    )
    return prompt


# ── Smoke Demo ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 72)
    print("  CISCO AUDIT — Prompt Generator Smoke Demo")
    print("=" * 72)

    # ── 1. Extract, filter, parse ─────────────────────────────────────────────
    import os
    import sys

    # Ensure project root is on sys.path
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    if _script_dir not in sys.path:
        sys.path.insert(0, _script_dir)

    # Import references needed only for the demo/CLI entry point
    from config_path_extractor import extract_config_paths  # noqa: F811
    from config_path_filter import filter_paths_by_whitelist  # noqa: F811
    from config_path_parser import parse_config_paths  # noqa: F811
    import reference_consumers  # noqa: F401
    import reference_providers  # noqa: F401

    config_file = os.path.join(_script_dir, "example-router.conf")

    print(f"\n[1] Parsing {os.path.relpath(config_file, _script_dir)}...")
    all_paths = extract_config_paths(config_file)
    filtered_paths = filter_paths_by_whitelist(all_paths)
    parsed = parse_config_paths(filtered_paths)
    print(f"    Extracted: {len(all_paths)} paths")
    print(f"    Filtered:  {len(filtered_paths)} paths (whitelist match)")
    print(f"    Parsed:    {len(parsed)} paths")
    print()

    if not parsed:
        print("No parsed paths to demo. Exiting.")
        sys.exit(0)

    first = parsed[0]
    display = _path_to_display(first)
    print(f"[2] Initial prompt for path #{1}: {display}")

    initial = prepare_initial_prompt(first)
    print(f"    → Prompt length: {len(initial)} characters")
    print(f"    → Preview:\n{'-' * 60}")
    print(initial[:400] + "\n...\n")

    # ── 3. Context: requestedInfo=[1, 3] ──────────────────────────────────────
    print(f"[3] Simulated LLM response: requestedInfo=[1, 3] (neighbor + reference)")
    r1 = AuditResponse(action="request_context", requestedInfo=[1, 3])
    cp1 = prepare_context_prompt(r1, first, parsed)
    print(f"    → Prompt length: {len(cp1)} characters")
    print(f"    → Full output:\n{'-' * 60}")
    print(cp1)
    print()

    # ── 4. Context: requestedInfo=[1, 2, 3] ──────────────────────────────────
    print(f"[4] Simulated LLM response: requestedInfo=[1, 2, 3] (all types)")
    r2 = AuditResponse(action="request_context", requestedInfo=[1, 2, 3])
    cp2 = prepare_context_prompt(r2, first, parsed)
    print(f"    → Prompt length: {len(cp2)} characters")
    print(f"    → Preview:\n{'-' * 60}")
    print(cp2[:600] + "\n...\n")

    # ── 5. Context: requestedInfo=[4] ────────────────────────────────────────
    print(f"[5] Simulated LLM response: requestedInfo=[4] (reference consumers only)")
    r5 = AuditResponse(action="request_context", requestedInfo=[4])
    cp5 = prepare_context_prompt(r5, first, parsed)
    print(f"    → Prompt length: {len(cp5)} characters")
    print(f"    → Full output:\n{'-' * 60}")
    print(cp5)
    print()

    # ── 6. Context: requestedInfo=[2] ────────────────────────────────────────
    print(f"[6] Simulated LLM response: requestedInfo=[2] (similar only)")
    r3 = AuditResponse(action="request_context", requestedInfo=[2])
    cp3 = prepare_context_prompt(r3, first, parsed)
    print(f"    → Prompt length: {len(cp3)} characters")
    print(f"    → Full output:\n{'-' * 60}")
    print(cp3)
    print()

    # ── 7. Parse a complete_analysis response ─────────────────────────────────
    print(f"[7] Simulated LLM response: complete_analysis")
    r6 = AuditResponse(
        action="complete_analysis",
        hasIssue=True,
        parameter=["ip address"],
        reason=["CIDR notation is not valid Cisco IOS syntax."],
    )
    print(f"    → Parsed AuditResponse: {r6.model_dump_json(indent=2)}")

    print(f"\n{'=' * 72}")
    print("  All smoke tests passed successfully!")
    print(f"{'=' * 72}")
