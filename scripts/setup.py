#!/usr/bin/env python3
"""Install project-scoped Docspeed integration or verify a real MCP handshake.

Python 3.10+; Python 3.10 requires the tomli TOML parser. Credentials are read from the environment;
they are never written to configuration, passed in CLI arguments, or printed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
from urllib import error, parse, request

PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_URL = "https://api.docspeed.ai/mcp/"
CORE_TOOLS = {"files_upload", "parse", "extract", "ask"}
DOCSTER_TOOLS = {"docster_build", "docster_status", "docster_revise", "docster_invoke"}
PROTOCOL_VERSION = "2025-03-26"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class SetupError(RuntimeError):
    """An actionable error whose message contains no remote data or credentials."""


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SetupError("MCP redirected the request. Use its canonical URL; credentials were not forwarded.")


def validate_url(url: str, *, allow_local_http: bool = False) -> str:
    parsed = parse.urlsplit(url)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    secure = parsed.scheme == "https" or (allow_local_http and local and parsed.scheme == "http")
    if not secure or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SetupError("Use an HTTPS MCP URL without embedded credentials, query, or fragment.")
    return url


def _rpc_result(payload: dict, expected_id: int) -> dict:
    if payload.get("id") != expected_id or payload.get("jsonrpc") != "2.0":
        raise SetupError("MCP returned an invalid JSON-RPC response.")
    if "error" in payload:
        raise SetupError("MCP returned a protocol error. Check server logs using the request time; remote error text is redacted.")
    if not isinstance(payload.get("result"), dict):
        raise SetupError("MCP returned no result object.")
    return payload["result"]


def _decode_response(body: bytes, content_type: str, expected_id: int) -> dict:
    try:
        if "text/event-stream" in content_type:
            # Ignore progress/keepalive events; return only this request's response.
            data_lines: list[str] = []
            for line in (body.decode("utf-8").replace("\r\n", "\n") + "\n\n").splitlines():
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
                elif not line and data_lines:
                    payload = json.loads("\n".join(data_lines))
                    data_lines = []
                    if isinstance(payload, dict) and payload.get("id") == expected_id:
                        return _rpc_result(payload, expected_id)
            raise SetupError("MCP stream ended without the expected response.")
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise SetupError("MCP returned a non-object response.")
        return _rpc_result(payload, expected_id)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SetupError("MCP returned malformed JSON; response body is redacted.") from exc


def check_connection(url: str, api_key: str, *, require_docster: bool = False,
                     allow_local_http: bool = False, timeout: float = 30) -> dict:
    validate_url(url, allow_local_http=allow_local_http)
    if not api_key or any(character.isspace() for character in api_key):
        raise SetupError("Set a nonempty DOCSPEED_API_KEY in the process environment.")
    opener = request.build_opener(NoRedirect())
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream",
               "User-Agent": "docspeed-agent-tools/0.1.0"}

    def send(method: str, params: dict | None, rpc_id: int | None) -> dict:
        message: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        if rpc_id is not None:
            message["id"] = rpc_id
        req = request.Request(url, data=json.dumps(message).encode(), headers=headers, method="POST")
        try:
            with opener.open(req, timeout=timeout) as response:
                session_id = response.headers.get("Mcp-Session-Id")
                if session_id:
                    headers["Mcp-Session-Id"] = session_id
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise SetupError("MCP response exceeds the checker's size limit.")
                return {} if rpc_id is None else _decode_response(body, response.headers.get("Content-Type", ""), rpc_id)
        except error.HTTPError as exc:
            raise SetupError(f"MCP returned HTTP {exc.code}; check URL, API key, and account access. Response body is redacted.") from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            raise SetupError("MCP connection failed or timed out; check network access and the endpoint.") from exc

    initialized = send("initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                                      "clientInfo": {"name": "docspeed-connection-check", "version": "0.1.0"}}, 1)
    version = initialized.get("protocolVersion")
    if version not in {"2024-11-05", "2025-03-26", "2025-06-18"}:
        raise SetupError("MCP negotiated an unsupported protocol version; update the connection checker.")
    capabilities = initialized.get("capabilities")
    if not isinstance(capabilities, dict) or "tools" not in capabilities:
        raise SetupError("MCP initialized without tool support.")
    headers["MCP-Protocol-Version"] = version
    send("notifications/initialized", None, None)
    tools: list[dict] = []
    cursor = None
    seen_cursors: set[str] = set()
    for page in range(20):
        result = send("tools/list", {"cursor": cursor} if cursor else {}, page + 2)
        entries = result.get("tools")
        if not isinstance(entries, list):
            raise SetupError("MCP tools/list returned no tools array.")
        for tool in entries:
            if not isinstance(tool, dict) or not isinstance(tool.get("name"), str) or not tool["name"]:
                raise SetupError("MCP returned a tool without a valid name.")
            if not isinstance(tool.get("description"), str) or not tool["description"].strip():
                raise SetupError("MCP returned a tool without a description.")
            if not isinstance(tool.get("inputSchema"), dict):
                raise SetupError("MCP returned a tool without an input schema.")
            tools.append(tool)
        cursor = result.get("nextCursor")
        if not cursor:
            break
        if not isinstance(cursor, str) or cursor in seen_cursors:
            raise SetupError("MCP tools/list returned an invalid or repeated page cursor.")
        seen_cursors.add(cursor)
    else:
        raise SetupError("MCP tools/list exceeded 20 pages.")
    names = {tool["name"] for tool in tools}
    if len(names) != len(tools):
        raise SetupError("MCP returned duplicate tool names.")
    required = CORE_TOOLS | (DOCSTER_TOOLS if require_docster else set())
    missing = required - names
    if missing:
        raise SetupError("MCP is missing required tools: " + ", ".join(sorted(missing)))
    return {"ok": True, "endpoint": url, "protocol_version": version, "tool_count": len(tools),
            "docster_available": DOCSTER_TOOLS <= names, "tools": tools}


def _assert_regular(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise SetupError(f"Refusing to replace a symlink or non-file: {path}")


def _atomic_write(path: Path, data: str) -> None:
    _assert_regular(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".docspeed-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(data)
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _codex_direct_mcp_config(content: str) -> str:
    """Opt in to the documented direct namespace setting without rewriting custom TOML."""
    parsed = tomllib.loads(content)
    features = parsed.get("features", {})
    if not isinstance(features, dict):
        raise SetupError("Existing Codex features must be a table; no files were changed.")
    if features.get("code_mode_host") is False:
        raise SetupError("Codex Code Mode host is explicitly disabled. Review that setting before enabling direct MCP; no files were changed.")
    mode = features.get("code_mode")
    if mode is not None:
        if (isinstance(mode, dict) and mode.get("enabled") is True
                and isinstance(mode.get("direct_only_tool_namespaces"), list)
                and "mcp__docspeed" in mode["direct_only_tool_namespaces"]):
            return content
        raise SetupError("Existing Code Mode settings differ. Preserve your other namespaces and add mcp__docspeed manually using config/codex-direct-mcp.toml; no files were changed.")
    after = content.rstrip() + '\n\n[features.code_mode]\nenabled = true\ndirect_only_tool_namespaces = ["mcp__docspeed"]\n'
    tomllib.loads(after)
    return after


def install(client: str, project: Path, url: str, *, codex_direct_mcp: bool = False) -> dict:
    """Add project configuration without overwriting existing server/skill choices."""
    validate_url(url)
    if client not in {"codex", "claude"}:
        raise SetupError("Choose the codex or claude client.")
    if codex_direct_mcp and client != "codex":
        raise SetupError("--codex-direct-mcp applies only to Codex; no files were changed.")
    project = project.resolve(strict=True)
    if not project.is_dir():
        raise SetupError("The project must be an existing directory.")
    source_skill = PACKAGE / "skills" / "docspeed-documents"
    skill_root = ".agents" if client == "codex" else ".claude"
    skill_destination = project / skill_root / "skills" / "docspeed-documents"
    config = project / (".codex/config.toml" if client == "codex" else ".mcp.json")
    _assert_regular(config)
    before = config.read_text() if config.exists() else ""
    if client == "codex":
        desired = {"url": url, "bearer_token_env_var": "DOCSPEED_API_KEY",
                   "startup_timeout_sec": 30, "tool_timeout_sec": 1200}
        current = tomllib.loads(before).get("mcp_servers", {}).get("docspeed")
        if current is not None and current != desired:
            raise SetupError("An existing Codex Docspeed server differs. Review it manually; no files were changed.")
        block = "\n[mcp_servers.docspeed]\n" + "\n".join(f"{key} = {json.dumps(value)}" for key, value in desired.items()) + "\n"
        after = before if current is not None else before.rstrip() + "\n" + block
        tomllib.loads(after)
        if codex_direct_mcp:
            after = _codex_direct_mcp_config(after)
    else:
        desired = {"type": "http", "url": url, "headers": {"Authorization": "Bearer ${DOCSPEED_API_KEY}"}, "timeout": 1200000}
        content = json.loads(before) if before else {}
        if not isinstance(content, dict) or not isinstance(content.get("mcpServers", {}), dict):
            raise SetupError("Existing Claude MCP config must contain an mcpServers object.")
        servers = content.setdefault("mcpServers", {})
        if "docspeed" in servers and servers["docspeed"] != desired:
            raise SetupError("An existing Claude Docspeed server differs. Review it manually; no files were changed.")
        servers["docspeed"] = desired
        after = json.dumps(content, indent=2) + "\n"
    # Validate all skill targets before making the first mutation.
    skill_files = sorted(source_skill.rglob("*"))
    for source in skill_files:
        if source.is_file():
            destination = skill_destination / source.relative_to(source_skill)
            _assert_regular(destination)
            if destination.exists() and destination.read_bytes() != source.read_bytes():
                raise SetupError(f"Existing skill differs: {destination}. Review it manually; no files were changed.")
    for source in skill_files:
        if source.is_file():
            destination = skill_destination / source.relative_to(source_skill)
            if not destination.exists():
                _atomic_write(destination, source.read_text())
    if after != before:
        _atomic_write(config, after)
    return {"ok": True, "client": client, "config": str(config), "skill": str(skill_destination),
            "codex_direct_mcp": codex_direct_mcp,
            "credential_stored": False, "next_step": "Start a new agent session with DOCSPEED_API_KEY in its environment; verify /mcp."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    installer = subparsers.add_parser("install", help="Install into an existing project; does not change account or approval settings.")
    installer.add_argument("--client", required=True, choices=["codex", "claude"])
    installer.add_argument("--project", required=True, type=Path)
    installer.add_argument("--url", default=DEFAULT_URL)
    installer.add_argument("--codex-direct-mcp", action="store_true", help="Opt in to Codex's documented direct MCP namespace setting; preserves custom settings or stops for review.")
    checker = subparsers.add_parser("check", help="Authenticate, initialize, and list tools; does not upload or process documents.")
    checker.add_argument("--url", default=DEFAULT_URL)
    checker.add_argument("--require-docster", action="store_true")
    checker.add_argument("--catalog-out", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "install":
            result = install(args.client, args.project, args.url, codex_direct_mcp=args.codex_direct_mcp)
        else:
            result = check_connection(args.url, os.environ.get("DOCSPEED_API_KEY", ""), require_docster=args.require_docster)
            if args.catalog_out:
                _atomic_write(args.catalog_out, json.dumps(result, indent=2) + "\n")
            result = {key: value for key, value in result.items() if key != "tools"}
        print(json.dumps(result, indent=2))
        return 0
    except (SetupError, ValueError, OSError) as exc:
        # Only our explicitly sanitized diagnostics may be printed.
        message = str(exc) if isinstance(exc, SetupError) else "Configuration or filesystem operation failed; no credential values are printed."
        print(f"Error: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
