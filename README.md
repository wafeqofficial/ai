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

Team and Enterprise administrators may need to enable the connector or plugin for their organization.

## What is included

- .codex-plugin/plugin.json: ChatGPT and Codex package metadata.
- .claude-plugin/plugin.json: Claude package metadata.
- .claude-plugin/marketplace.json: shared ChatGPT, Codex, and Claude marketplace catalog.
- .mcp.json: the single remote Wafeq MCP connection.
- skills/manage-wafeq/SKILL.md: shared, provider-neutral workflow instructions.
- assets/: official Wafeq presentation assets.

Both manifests reference the same MCP configuration and skill directory. There are no client-specific copies of the skill.

## Authentication and safety

The plugin never stores Wafeq credentials. Each user signs in through Wafeq OAuth, and the hosted MCP server applies that user's organization membership and permissions.

Read operations should use narrow filters and return concise results. Write operations remain subject to the confirmation behavior of the host application and the permissions of the signed-in Wafeq user.

## Links

- [Wafeq](https://www.wafeq.com/)
- [Help center](https://help.wafeq.com/hc/en-ae)
- [Privacy policy](https://www.wafeq.com/en/privacy-policy)
- [Terms of service](https://www.wafeq.com/en/terms-of-service)

For support, contact help@wafeq.com.
