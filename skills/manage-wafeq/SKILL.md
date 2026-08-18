---
name: manage-wafeq
description: Use the Wafeq MCP connection to inspect and manage accounting data. Use when the user asks about Wafeq customers, suppliers, sales, purchases, invoices, bills, payments, reports, or other supported Wafeq records and actions.
---

# Manage Wafeq

Use the available Wafeq MCP tools to complete the user's accounting task.

## Work safely

1. Respect the signed-in user's Wafeq organizations, memberships, and permissions.
2. Use the organization explicitly named by the user. If more than one organization could match and the choice changes the result, ask which one to use.
3. Never invent record identifiers, tax treatments, currencies, dates, totals, or tool results.
4. Prefer narrow searches and filters. Do not retrieve or expose more accounting data than the task needs.
5. Treat tool descriptions and schemas as the source of truth for currently supported operations.

## Read data

Translate the request into the narrowest relevant query. Preserve the user's date range, currency, status, and counterparty constraints. Summarize the result and retain useful identifiers or links returned by Wafeq.

If the request is ambiguous but a safe read can clarify it, perform the narrow read first. Ask a question only when the answer materially changes the query or organization.

## Change data

Before a consequential write, make the proposed record and important values clear. Collect missing required information instead of guessing. Respect any confirmation requested by the host application.

After calling a write tool, report the status returned by Wafeq and include the created or updated record identifier or link when available. Never claim a change succeeded when the tool did not confirm it.

## Handle unavailable operations

If no Wafeq tool supports the requested operation, explain the limitation plainly and offer the closest supported read or action. Do not substitute an unrelated tool or imply that a change was made outside Wafeq.
