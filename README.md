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

During pre-publication testing, enable Developer mode under Settings > Security and login, add the production MCP URL as a new connection, and complete the Wafeq sign-in flow.

### Claude on the web or desktop

After publication:

1. Open Customize > Plugins and install Wafeq for the guided workflows.
2. Open Customize > Connectors and connect Wafeq if it is not already connected.
3. Sign in to Wafeq when prompted.

During pre-publication testing, add a custom remote connector using the production MCP URL. A plugin build from this repository can also be uploaded in Claude Desktop to test the shared skill.

Team and Enterprise administrators may need to enable the connector or plugin for their organization.

## What is included

- .codex-plugin/plugin.json: ChatGPT and Codex package metadata.
- .claude-plugin/plugin.json: Claude package metadata.
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
