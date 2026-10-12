# Docspeed for coding agents

Connect Codex or Claude Code to Docspeed's hosted document tools and install the companion `docspeed-documents` skill. Use your existing agent to extract fields, read documents, answer cited questions, compare document values, or build a reusable Docster workflow.

This source-available repository contains client integration assets, not the Docspeed server or a local/offline document engine. [Public setup guide](https://api.docspeed.ai/agent-tools/) · [API documentation](https://api.docspeed.ai/docs) · [Recorded examples](https://api.docspeed.ai/agent-tools/#example)

## Connect with an installed client

The [public guide](https://api.docspeed.ai/agent-tools/) now provides direct setup without downloading this repository or installing Python. Use a macOS or Linux terminal with Bash or zsh, in your document project. Choose this route **or** the repository installer below. If you already customized the companion skill, use the repository installer's conflict checks instead of overwriting it with these download commands.

With your account API key ready, read it at the hidden prompt in the same terminal that will install and launch the client:

```sh
printf 'Docspeed API key (input hidden): '
read -r -s DOCSPEED_API_KEY
printf '\n'
export DOCSPEED_API_KEY
```

The key stays in the terminal environment; it is not saved in command history or client configuration. A separately launched desktop app does not inherit it automatically.

For **Codex**, add the native connection and download the companion skill and upload helper:

```sh
codex mcp add docspeed --url https://api.docspeed.ai/mcp/ --bearer-token-env-var DOCSPEED_API_KEY && \
mkdir -p .agents/skills/docspeed-documents/agents .agents/skills/docspeed-documents/scripts && \
curl --fail --silent --show-error https://api.docspeed.ai/agent-tools/skills/docspeed-documents/SKILL.md -o .agents/skills/docspeed-documents/SKILL.md && \
curl --fail --silent --show-error https://api.docspeed.ai/agent-tools/skills/docspeed-documents/agents/openai.yaml -o .agents/skills/docspeed-documents/agents/openai.yaml && \
curl --fail --silent --show-error https://api.docspeed.ai/agent-tools/skills/docspeed-documents/scripts/upload.py -o .agents/skills/docspeed-documents/scripts/upload.py
```

This registers the server in your user configuration and the skill in the current project. Start a fresh session from the same terminal:

```sh
codex -c mcp_servers.docspeed.tool_timeout_sec=1200
```

For **Claude Code**, register the connection and skill in the current project:

```sh
claude mcp add --transport http --scope project docspeed https://api.docspeed.ai/mcp/ --header 'Authorization: Bearer ${DOCSPEED_API_KEY}' && \
mkdir -p .claude/skills/docspeed-documents/scripts && \
curl --fail --silent --show-error https://api.docspeed.ai/agent-tools/skills/docspeed-documents/SKILL.md -o .claude/skills/docspeed-documents/SKILL.md && \
curl --fail --silent --show-error https://api.docspeed.ai/agent-tools/skills/docspeed-documents/scripts/upload.py -o .claude/skills/docspeed-documents/scripts/upload.py
```

Keep the single quotes around the header so the configuration stores the environment variable name, not its value. Launch from the same terminal:

```sh
MCP_TOOL_TIMEOUT=1200000 claude
```

Follow the client's normal project trust and MCP approval prompts, then inspect `/mcp` inside the session. These commands configure the connection; they do not bypass permission prompts, upload a document, prove model entitlement, or guarantee tool selection. Python is only needed for the optional direct-upload helper and repository installer described below.

## Install from this repository

You need Python 3.10 or later, an installed Codex or Claude Code client, and a Docspeed API key from your account dashboard. Make `DOCSPEED_API_KEY` available to the process that launches your client. Do not paste the key into chat, commit it, or pass it as a command argument. A desktop client must receive the environment variable too.

Download or clone this repository, then open a terminal in its root directory. Python 3.11+ needs no additional package. On Python 3.10 only:

```sh
python3 -m pip install -r requirements.txt
```

Install the connection and skill into an **existing** project, replacing the example path:

```sh
python3 scripts/setup.py install --client codex --project /absolute/path/to/your/project
```

For Claude Code, use `--client claude`. This local install does not upload or process documents. It preserves other configured servers and client approval settings; conflicting Docspeed configuration or a modified skill stops the install for manual review.

Start a new agent session in that project, complete the client's normal project/MCP trust prompts, and inspect `/mcp`. Installation alone does not inject tools into an already-running conversation or guarantee tool selection.

With your key set, check the real connection:

```sh
python3 scripts/setup.py check
```

The check initializes MCP and lists its tools; it makes no document-processing or model call. Success proves connection and discovery of the checker's required core tools, not every operation, sufficient balance, output quality, or completed workflows. For the four Docster tools specifically:

```sh
python3 scripts/setup.py check --require-docster
```

The canonical MCP endpoint is `https://api.docspeed.ai/mcp/`, including the trailing slash. The checker rejects redirects rather than forwarding credentials to another origin. It reports errors explicitly and does not switch providers.

## Try a document task

Use a document you are authorized to send to Docspeed:

> Extract the supplier, invoice number, taxes, and all line items from this PDF. Include source evidence and identify missing values.

Or ask:

> Which cancellation terms apply across these contract PDFs? Cite the supporting pages.

Choose the smallest applicable operation from the actual connected tool catalog. The skill covers OCR, Parse, Layout, extraction, document questions, tables, charts, equations, classification, splitting, comparison, and reusable workflows when their tools are exposed. `schema_auto` can propose a schema when it is available; never invent a missing capability.

For reusable work, ask for a Docster workflow. Builds are available through the authenticated interface and require the normal quota, billing, and validation controls. Begin with clarification, retain the returned attempt ID, and report completion only when the workflow is ready.

Production inputs are PDF and PNG/JPEG/TIFF/WebP/BMP/GIF images. Native DOCX/XLSX processing has a separate beta API path. The remote MCP cannot read a local filesystem path or ingest a URL.

For an authorized local file, use the shipped Python 3.10+ helper from the installed skill directory. It needs no extra package:

```sh
# Codex project:
python3 .agents/skills/docspeed-documents/scripts/upload.py "/absolute/path/to/document.pdf"

# Claude Code project:
python3 .claude/skills/docspeed-documents/scripts/upload.py "/absolute/path/to/document.pdf"
```

It streams one supported, nonempty PDF/image of at most 50 MiB directly to the hosted upload endpoint using `DOCSPEED_API_KEY` from the environment. It prints only the reusable `file_id` and submitted `filename`. Keep the upload and MCP calls on the same account. Uploading does not run extraction. The helper verifies HTTPS and follows no redirects or automatic retries; an interrupted upload can have an unknown outcome.

Keep document bytes out of the agent conversation. `files_upload` remains an option for tiny inputs of at most 4 KiB; use direct upload for larger files. Reuse the returned file reference for subsequent operations. The [skill](skills/docspeed-documents/SKILL.md) contains the exact supported workflow and failure rules.

**Synthesize is API-only:** it is not exposed in the current MCP catalog. Its separate public API is documented in the [Synthesize guide](https://api.docspeed.ai/docs/compare-synthesize). Reference fidelity remains under validation. Do not substitute a workflow build or claim generated content is evidence about a real source.

## Other installation choices

- Manual Codex configuration: merge `config/codex.toml` into your chosen configuration and copy `skills/docspeed-documents/` into the chosen skill directory. Preserve other settings.
- Optional Codex direct namespace mode: use `--codex-direct-mcp` with the project installer, or review `config/codex-direct-mcp.toml`. This is opt-in, preserves approval policy, and does not establish support or selection for every Codex version.
- Local Claude Code plugin: with your key in the environment, start `claude --plugin-dir /absolute/path/to/this/repository`. Use this **or** the project installer to avoid duplicate registrations.
- **Claude catalog checksum issue observed 12 October 2026:** the public catalog still pins the preceding ZIP checksum while the download URL serves the updated package. Catalog installation is not a validated route for this package until the checksum is reconciled. This repository and the direct setup commands above do not use that catalog.

`plugin.json`/`mcp.json` also provide portable Agent Plugins metadata. Compatible host support and directory submission are separate. The [official MCP Registry record](https://registry.modelcontextprotocol.io/v0.1/servers/ai.docspeed%2Fdocspeed/versions/0.1.0) describes the hosted server; a listing does not install or enable it in your agent.

## Privacy, cost, and result boundaries

Uploading sends the selected document to Docspeed. Respect local-only requirements and the user's chosen provider. Do not upload private documents without authorization. Normal Docspeed charges apply to processing and workflow calls; use your account's available balance. Paid top-ups are currently unavailable. Client/model subscription or entitlement is separate from Docspeed access.

Inspect returned citations, page geometry, absent values and errors against the source. A successful tool response is not an accuracy guarantee. Preserve explicit failures rather than silently changing OCR engines or providers. Recorded examples are bounded synthetic evaluations, not customer outcomes or universal quality claims.

Read [How to check document answers for completeness](docs/document-answer-completeness.md) for a source-backed review of the three recorded examples and their limits.

## Package contents and provenance

- `docs/document-answer-completeness.md`: reviewed write-up of historical synthetic evaluations.
- `skills/docspeed-documents/`: portable skill, Codex metadata and direct-upload helper.
- `config/`, `.mcp.json`, `mcp.json`: environment-based or host-managed key configuration.
- `scripts/setup.py`: project installer and bounded MCP connection check.
- `.claude-plugin/plugin.json`, `plugin.json`: plugin manifests.
- `evals/`, `scripts/eval_selection.py`: optional metadata-selection evaluation. Running it invokes your installed model client and can consume its usage; it does not measure live document quality or automatic skill discovery.

The runtime/configuration/skill assets are exact copies of the published ZIP identified in `PROVENANCE.json`. This standalone README replaces the ZIP's monorepo-oriented maintenance instructions. `MANIFEST.json` records the intended public file set and hashes. No server code, account credentials, customer documents or private execution records are included.

## License status

This source-available repository does not declare an open-source license. The source package contains no LICENSE file or manifest license field. Do not infer an open-source license from visibility or from third-party dependencies; see `LICENSE_STATUS.md`. A maintainer must select a license before describing the package as open source. Public availability does not imply a license grant.
