#!/usr/bin/env python3
"""Measure metadata-based routing decisions with an actual Codex or Claude CLI.

This is a selection-only evaluation, not an end-to-end host discovery or document
quality benchmark. It supplies a real MCP catalog and asks the model to choose;
it never calls document tools. Run fresh user prompts in each installed client
separately to measure native skill discovery, tool invocation, and result quality.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

PACKAGE = Path(__file__).resolve().parents[1]
OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"tools": {"type": "array", "items": {"type": "string"}},
                   "unavailable_capability": {"type": ["string", "null"]},
                   "reason": {"type": "string"}},
    "required": ["tools", "unavailable_capability", "reason"],
}


def load_cases(path: Path) -> list[dict]:
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate evaluation case IDs.")
    return cases


def grade(case: dict, decision: dict, available: set[str]) -> dict:
    chosen_list = decision.get("tools")
    if not isinstance(chosen_list, list) or not all(isinstance(name, str) for name in chosen_list):
        raise ValueError("Decision tools must be an array of names.")
    chosen = set(chosen_list)
    alternatives = [set(route) for route in case["expected_any"]]
    supported = any(route <= available for route in alternatives)
    invented = sorted(chosen - available)
    # Missing features are measured separately, not counted as successful routing.
    if not supported:
        return {"status": "capability_unavailable", "invented_tools": invented,
                "missing_reported": bool(decision.get("unavailable_capability"))}
    success = not invented and any((not chosen if not route else route <= chosen) for route in alternatives)
    return {"status": "pass" if success else "fail", "invented_tools": invented}


def prompt_for(case: dict, catalog: list[dict], include_skill: bool) -> str:
    skill = (PACKAGE / "skills/docspeed-documents/SKILL.md").read_text() if include_skill else "No companion skill supplied."
    return ("This is an offline routing evaluation. Do not execute tools, browse, read local files, or process documents. "
            "Given the user request and available Docspeed tool definitions below, return the tool names that should "
            "perform the substantive work, excluding upload/status preparation unless it is the request itself. "
            "Use exact bare tool names from the catalog. If Docspeed does not fit, return tools: []. "
            "If a needed capability is unavailable, state it. Do not invent a tool. "
            "Assume attached PDFs/images exist, the key is connected, and uploads are authorized unless the user restricts them. "
            "No actual file content is provided; this evaluates routing only. Return JSON matching the supplied schema.\n\n"
            + "Companion skill:\n" + skill + "\n\nTool catalog:\n" + json.dumps(catalog)
            + "\n\nUser request:\n" + case["prompt"])


def run_decision(client: str, model: str, prompt: str, timeout: int) -> dict:
    executable = shutil.which(client)
    if not executable:
        raise RuntimeError(f"Required {client} CLI is not installed.")
    with tempfile.TemporaryDirectory(prefix="docspeed-selection-") as temporary:
        root = Path(temporary)
        if client == "codex":
            schema = root / "schema.json"
            schema.write_text(json.dumps(OUTPUT_SCHEMA))
            output = root / "decision.json"
            command = [executable, "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
                       "--sandbox", "read-only", "--model", model, "--output-schema", str(schema),
                       "--output-last-message", str(output), "-"]
        else:
            command = [executable, "--print", "--model", model, "--output-format", "json",
                       "--json-schema", json.dumps(OUTPUT_SCHEMA), "--tools", "", "--strict-mcp-config",
                       "--mcp-config", '{"mcpServers":{}}', "--setting-sources", "", "--no-session-persistence"]
        result = subprocess.run(command, input=prompt, text=True, capture_output=True, cwd=root, timeout=timeout)
        if result.returncode:
            # CLI logs may contain account details. They are intentionally not echoed.
            raise RuntimeError(f"{client} exited {result.returncode}; check that CLI's authentication and model availability.")
        if client == "codex":
            if not output.is_file():
                raise RuntimeError("Codex produced no decision file.")
            decision = json.loads(output.read_text())
        else:
            envelope = json.loads(result.stdout)
            if envelope.get("is_error"):
                raise RuntimeError("Claude returned an evaluation error; inspect CLI account access.")
            decision = envelope.get("structured_output")
            if not isinstance(decision, dict):
                raise RuntimeError("Claude returned no structured decision.")
        if not isinstance(decision, dict):
            raise RuntimeError("Client returned a non-object decision.")
        return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", required=True, choices=["codex", "claude"])
    parser.add_argument("--model", required=True, help="Explicit model choice recorded with every result.")
    parser.add_argument("--catalog", type=Path, required=True, help="Catalog JSON written by setup.py check --catalog-out.")
    parser.add_argument("--cases", type=Path, default=PACKAGE / "evals/selection-cases.jsonl")
    parser.add_argument("--case", action="append", default=[], help="Select case IDs; repeat to run a subset.")
    parser.add_argument("--without-skill", action="store_true", help="Compare catalog-only decisions with skill-assisted decisions.")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text())
    tools = catalog["tools"]
    available = {tool["name"] for tool in tools}
    cases = load_cases(args.cases)
    unknown = set(args.case) - {case["id"] for case in cases}
    if unknown:
        parser.error("Unknown case IDs: " + ", ".join(sorted(unknown)))
    selected = [case for case in cases if not args.case or case["id"] in args.case]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    with args.output.open("x", encoding="utf-8") as stream:
        for case in selected:
            started = time.monotonic()
            record = {"case_id": case["id"], "kind": case["kind"], "client": args.client, "model": args.model,
                      "measurement": "metadata_selection_only", "skill_supplied": not args.without_skill,
                      "catalog_endpoint": catalog.get("endpoint"), "tool_count": len(tools)}
            try:
                decision = run_decision(args.client, args.model, prompt_for(case, tools, not args.without_skill), args.timeout)
                record.update({"decision": decision, **grade(case, decision, available)})
            except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired):
                record.update({"status": "error", "error": "CLI failed, timed out, or returned invalid output; no success is inferred."})
            record["elapsed_seconds"] = round(time.monotonic() - started, 2)
            failures += record["status"] != "pass"
            stream.write(json.dumps(record) + "\n")
            stream.flush()
            print(f"{case['id']}: {record['status']}", flush=True)
    print(f"Selection-only evaluation: {len(selected) - failures}/{len(selected)} passed. Results: {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
