I have a configuration path extracted from a Cisco IOS running configuration and need to determine whether it contains any configuration issues.

**Configuration Path Under Review:**

```text
interface GigabitEthernet0/0 --> ip address 192.168.1.1 255.255.255.0
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
* Contains one or more values selected only from `[1, 2, 3]`.
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
