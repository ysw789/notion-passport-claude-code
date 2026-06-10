---
name: setup-notion-workspace
description: >-
  Bind the current project/directory to its OWN Notion workspace by adding a
  uniquely-named, local-scope Notion MCP server that authenticates via the
  /mcp OAuth redirect flow. Use this whenever the user wants per-project (or
  per-directory) Notion connections, a different Notion workspace for this repo
  than another repo, to stop projects from sharing one Notion workspace, or
  asks to "connect this project to Notion", "프로젝트별 노션 연결", "이 레포에 노션
  워크스페이스 붙이기", "노션 mcp 프로젝트별로 분리". Trigger even if they don't say "MCP"
  explicitly — any request to scope a Notion connection to a single project
  belongs here.
---

# Set up a per-project Notion workspace

## Why this exists

The hosted Notion MCP server (`https://mcp.notion.com/mcp`) authenticates per
*server entry*, and Claude Code stores each server's OAuth token keyed by the
**server name** (`{name}|{hash}` in `~/.claude/.credentials.json`). So the path
to per-project workspaces is simple:

- **Same server name across projects → same OAuth token → same workspace.**
- **Unique server name per project → independent Authenticate → each can pick a
  different workspace** in Notion's OAuth consent screen.

The common blocker is the user-scope `notion` plugin: it injects one shared
`notion` server into *every* project, forcing a single workspace everywhere.

## What the script does

`scripts/setup_notion_workspace.py` makes the current directory's connection
self-contained:

1. Derives a unique server name from the directory (`notion-<dir>`) unless one
   is given.
2. Picks a free, fixed OAuth **callback port** (from 8123 up), scanning ports
   already used by other `notion-*` servers so two projects never collide.
   A fixed port keeps the OAuth redirect URI stable across restarts.
3. Warns (without auto-removing) if the global `notion` plugin is present.
4. Removes any colliding local-scope server (the shared `notion`, or a prior
   run of this one).
5. Adds the server at **local scope** (`~/.claude.json`, this project only — not
   committed to git):
   `claude mcp add --transport http <name> https://mcp.notion.com/mcp --scope local --callback-port <port>`

## How to run it

From the target project's directory:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/setup-notion-workspace/scripts/setup_notion_workspace.py"
```

> `${CLAUDE_PLUGIN_ROOT}` is set automatically when this runs as an installed
> plugin. If you copied the skill into `~/.claude/skills/` instead, substitute
> that path: `python3 ~/.claude/skills/setup-notion-workspace/scripts/setup_notion_workspace.py`.

Pass overrides only if the user wants a specific name or port:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/setup-notion-workspace/scripts/setup_notion_workspace.py" notion-myrepo 8130
```

## After running — tell the user the manual steps

These are interactive and the user must do them:

1. **Restart Claude Code** if the global plugin was just uninstalled.
2. Run `/mcp` → select the new server → **Authenticate**.
3. In the browser, **choose the Notion workspace** for this project.
4. In Notion, the pages/DBs to access must have this integration added under
   `•••` → **Connections**, or fetches will 404.

## One-time cleanup the script will not do for you

If the user agrees to fully drop the shared global plugin (recommended for clean
per-project management), run it explicitly — it is a global change and also
removes that plugin's skills:

```bash
claude plugin uninstall notion@claude-plugins-official
```

A leftover orphaned token may remain in `~/.claude/.credentials.json` under
`mcpOAuth` (key starting `plugin:Notion:`). It is harmless; remove the single
key if the user wants a clean credentials file.
