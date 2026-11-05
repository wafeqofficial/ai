# Wafeq for AI assistants

Use Wafeq from ChatGPT, Codex, and Claude through one secure, hosted MCP connection.

This repository contains the public plugin package and shared skill instructions. Authentication, authorization, MCP tools, and accounting business logic remain hosted by Wafeq at:

    https://mcp.wafeq.com/mcp

## Install

### ChatGPT on the web or desktop

After publication:

1. Open the Plugins directory in ChatGPT.
2. Find Wafeq and select Install.
3. Sign in to Wafeq when prompted.

The same public plugin listing is also available to supported Codex clients.

For pre-publication testing in the desktop app, add this repository as a plugin marketplace:

1. Open the Plugins directory and select Add plugin marketplace.
2. Set Source to `wafeqofficial/ai` (or `https://github.com/wafeqofficial/ai.git`).
3. Keep Git ref as `main` and leave Sparse paths empty.
4. Add the marketplace, install Wafeq, and complete the Wafeq sign-in flow.

On the web, enable Developer mode under Settings > Security and login, add `https://mcp.wafeq.com/mcp` as a custom connection, and complete the Wafeq sign-in flow.

### Claude on the web or desktop

After publication:

1. Open Customize > Plugins and install Wafeq for the guided workflows.
2. Open Customize > Connectors and connect Wafeq if it is not already connected.
3. Sign in to Wafeq when prompted.

During pre-publication testing, add `wafeqofficial/ai` as a marketplace in Claude Desktop and install the Wafeq plugin. On the web, add a custom remote connector using `https://mcp.wafeq.com/mcp`.

### Claude Code

Add the marketplace and install the plugin in one step:

    /plugin install wafeq --marketplace wafeqofficial/ai

Team and Enterprise administrators may need to enable the connector or plugin for their organization.

## What is included

- plugin.json: portable package metadata, OpenAI listing, and publication settings.
- mcp.json: portable remote Wafeq MCP connection with OAuth authentication.
- .codex-plugin/plugin.json: compatibility metadata for older ChatGPT and Codex clients.
- .claude-plugin/plugin.json: Claude package metadata.
- .claude-plugin/marketplace.json: shared ChatGPT, Codex, and Claude marketplace catalog.
- .mcp.json: the single remote Wafeq MCP connection.
- skills/manage-wafeq/SKILL.md: shared, provider-neutral workflow instructions.
- assets/logo.png: official Wafeq logo used by the plugin listing.
- LICENSE: Apache License 2.0.

The compatibility manifests share `.mcp.json`; the portable package uses
`mcp.json`. Both configurations connect to the same Wafeq server, and all clients
share one skill directory.

## Prepare an OpenAI Platform upload

The portable package discovers `skills/` and `mcp.json` at the repository root.
Keep the identity, version, and listing in `.codex-plugin/plugin.json` synchronized
with `plugin.json`, and keep both MCP configurations pointed at the same server.
The publication settings target all available countries. The commerce declaration
reflects the publisher's statement that purchases and payments are not enabled;
recording an accounting payment is distinct from moving money.

Create a separate upload ZIP from this directory using an explicit file list:

```sh
zip /tmp/wafeq-0.1.5-draft.zip \
  plugin.json mcp.json \
  .codex-plugin/plugin.json .claude-plugin/plugin.json .mcp.json \
  skills/manage-wafeq/SKILL.md assets/logo.png LICENSE README.md
```

Use a new output path if the archive already exists: `zip` updates existing
archives and could retain unwanted files. Do not upload a whole-repository ZIP:
the upload must exclude the marketplace catalog, Git history, credentials, and
unrelated files. Public uploads must also exclude `.app.json` and non-null
`apps` declarations in every manifest.

This draft is **not ready for submission** until these items are complete:

- Inspect authenticated tool schemas and their boolean `readOnlyHint`,
  `openWorldHint`, and `destructiveHint` annotations. The server source is hosted
  separately; this repository cannot validate or fix its tools.
- Prepare five distinct positive and three negative MCP review cases with exact
  tool names, important arguments, sample data, and observable results. Run them
  in a signed-in development connection and record the actual outcomes. The
  manifest's review prompts are suggestions, not executed review cases.
- Record a real demo against that development connection. In a dedicated sample
  organization, show “Summarize my recent invoices, bills, and expenses,” then
  “Help me create a draft invoice in Wafeq.” Show required clarifications,
  confirmation, and the returned result. Include an unsupported request such as
  “Buy a laptop for me.” Rehearse first, keep credentials off screen, verify
  playback, host it for reviewers, and add the verified recording URL to
  `extensions.com.openai.review.demo_recording_url`.
- Confirm that the published privacy policy covers this integration's actual
  data collection, sharing, retention, and deletion practices. Confirm that the
  terms apply to the plugin and verify the commerce declaration against the
  authenticated tools.

Before submitting, complete publisher/domain verification, reviewer access,
OAuth connection checks, required scans, and legal attestations in the portal.
Reviewer credentials belong only in secure portal fields. See OpenAI's
[submission guide](https://developers.openai.com/plugins/deploy/submission).

## Authentication and safety

The plugin never stores Wafeq credentials. Each user signs in through Wafeq OAuth, and the hosted MCP server applies that user's organization membership and permissions.

Read operations should use narrow filters and return concise results. Write operations remain subject to the confirmation behavior of the host application and the permissions of the signed-in Wafeq user.

## Links

- [Wafeq](https://www.wafeq.com/)
- [Help center](https://help.wafeq.com/hc/en-ae)
- [Privacy policy](https://www.wafeq.com/en/privacy-policy)
- [Terms of service](https://www.wafeq.com/en/terms-of-service)

For support, contact help@wafeq.com.

## License

Licensed under the [Apache License 2.0](LICENSE). The license does not grant rights to the Wafeq name or logo.
