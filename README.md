# Cursor Context KB (Scripts)

This repository contains helper scripts used with Cursor for BI/Analytics workflows (Confluence sync/cleanup, monitoring jobs, one-off utilities, and local quick-setup scripts).

## Contents

- `scripts/`
  - PowerShell utilities (`*.ps1`)
  - Python utilities (`*.py`)

## Prerequisites

- Windows + PowerShell
- Git
- Python 3.x (for the `*.py` scripts)

## Credentials / environment variables

Many scripts expect credentials (Confluence/Jira/Azure/Snowflake/etc.) to be present in the environment.

Recommended workflow:

1. Open PowerShell
2. Load required secrets into the environment (team-standard method)
3. Run scripts from `scripts/`

Example:

```powershell
cd C:\cursor_repo\cursor_context_kb
python .\scripts\cleanup_old_confluence_pages.py
```

## Common scripts

- Confluence
  - `scripts\sync_to_confluence.py`
  - `scripts\cleanup_old_confluence_pages.py`
  - `scripts\cleanup_renamed_pages.py`

- MCP / Cursor setup
  - `scripts\quick-setup-mcp.ps1`
  - `scripts\start-cursor-with-secrets.ps1`

- Monitoring / utilities
  - `scripts\monitor_dw2sf_sync.py`

## Notes

- If a script fails with missing credentials, ensure your environment variables are loaded for that shell session before re-running.
- Treat generated outputs (logs, extracts, temp files) as local artifacts and avoid committing them.


