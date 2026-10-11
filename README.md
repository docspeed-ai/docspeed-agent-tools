# Docspeed for coding agents

Connect Codex or Claude Code to Docspeed's hosted document tools and install the companion `docspeed-documents` skill. Use your existing agent to extract fields, read documents, answer cited questions, compare document values, or build a reusable Docster workflow.

This source-available repository contains client integration assets, not the Docspeed server or a local/offline document engine. [Public setup guide](https://api.docspeed.ai/agent-tools/) · [API documentation](https://api.docspeed.ai/docs) · [Recorded examples](https://api.docspeed.ai/agent-tools/#example)

## Install into your project

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

Production inputs are PDF and PNG/JPEG/TIFF/WebP/BMP/GIF images. Native DOCX/XLSX processing has a separate beta API path. The remote MCP cannot read a local filesystem path: an agent must read authorized file bytes and use `files_upload` with `filename` and `content_base64`. URL ingestion is not supported.

**Synthesize is API-only:** it is not exposed in the current MCP catalog. Its separate public API is documented in the [Synthesize guide](https://api.docspeed.ai/docs/compare-synthesize). Reference fidelity remains under validation. Do not substitute a workflow build or claim generated content is evidence about a real source.

## Other installation choices

- Manual Codex configuration: merge `config/codex.toml` into your chosen configuration and copy `skills/docspeed-documents/` into the chosen skill directory. Preserve other settings.
- Optional Codex direct namespace mode: use `--codex-direct-mcp` with the project installer, or review `config/codex-direct-mcp.toml`. This is opt-in, preserves approval policy, and does not establish support or selection for every Codex version.
- Local Claude Code plugin: with your key in the environment, start `claude --plugin-dir /absolute/path/to/this/repository`. Use this **or** the project installer to avoid duplicate registrations.
- The existing [Claude Code catalog](https://api.docspeed.ai/agent-tools/marketplace.json) installs the checksum-pinned public ZIP; it does not depend on this repository. See the public guide for supported client versions and commands.

`plugin.json`/`mcp.json` also provide portable Agent Plugins metadata. Compatible host support and directory submission are separate. The [official MCP Registry record](https://registry.modelcontextprotocol.io/v0.1/servers/ai.docspeed%2Fdocspeed/versions/0.1.0) describes the hosted server; a listing does not install or enable it in your agent.

## Privacy, cost, and result boundaries

Uploading sends the selected document to Docspeed. Respect local-only requirements and the user's chosen provider. Do not upload private documents without authorization. Normal Docspeed charges apply to processing and workflow calls; use your account's available balance. Paid top-ups are currently unavailable. Client/model subscription or entitlement is separate from Docspeed access.

Inspect returned citations, page geometry, absent values and errors against the source. A successful tool response is not an accuracy guarantee. Preserve explicit failures rather than silently changing OCR engines or providers. Recorded examples are bounded synthetic evaluations, not customer outcomes or universal quality claims.

Read [How to check document answers for completeness](docs/document-answer-completeness.md) for a source-backed review of the three recorded examples and their limits.

## Package contents and provenance

- `docs/document-answer-completeness.md`: reviewed write-up of historical synthetic evaluations.
- `skills/docspeed-documents/`: portable skill and Codex metadata.
- `config/`, `.mcp.json`, `mcp.json`: environment-based or host-managed key configuration.
- `scripts/setup.py`: project installer and bounded MCP connection check.
- `.claude-plugin/plugin.json`, `plugin.json`: plugin manifests.
- `evals/`, `scripts/eval_selection.py`: optional metadata-selection evaluation. Running it invokes your installed model client and can consume its usage; it does not measure live document quality or automatic skill discovery.

The runtime/configuration/skill assets are exact copies of the published ZIP identified in `PROVENANCE.json`. This standalone README replaces the ZIP's monorepo-oriented maintenance instructions. `MANIFEST.json` records the intended public file set and hashes. No server code, account credentials, customer documents or private execution records are included.

## License status

This source-available repository does not declare an open-source license. The source package contains no LICENSE file or manifest license field. Do not infer an open-source license from visibility or from third-party dependencies; see `LICENSE_STATUS.md`. A maintainer must select a license before describing the package as open source. Public availability does not imply a license grant.
