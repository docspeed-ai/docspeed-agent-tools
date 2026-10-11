# Docspeed routing evaluation

Measurement: metadata-based selection only. The runner supplied an MCP tool catalog and optionally the companion skill, then asked the selected model for a routing decision. It did not upload documents or invoke document-processing tools. This is not a document-accuracy benchmark or proof of automatic discovery in a normal client session.

- Run date and operator: not recorded
- Client and version: not recorded
- Exact model: not recorded
- Package version/commit: not recorded
- Catalog endpoint, capture time, and file hash: not recorded
- Skill supplied: not recorded
- Case set and selected IDs: not recorded
- Output JSONL path and hash: not recorded

| Result | Count |
| --- | --- |
| Passed routing decisions | Not run |
| Failed routing decisions | Not run |
| Capability unavailable | Not run |
| CLI error or timeout | Not run |
| Direct / indirect / negative totals | Not run |

For each failed case, record the exact request, selected tools, expected operation, and inspected cause. Report unavailable capabilities and client errors separately; they are not successful routes. If comparing catalog-only with skill-assisted runs, use the same catalog, cases, model, and client version and report run-to-run variation.

Native host discovery, actual tool invocation, evidence completeness, absent-value behavior, latency, cost, and workflow completion: **not measured by this runner**. Record separate end-to-end evidence before making claims about those outcomes.
