#!/usr/bin/env python3
"""Bind the current project/directory to its own Notion MCP server.

Each project gets a uniquely-named HTTP MCP server pointing at the hosted
Notion MCP (https://mcp.notion.com/mcp) with a fixed OAuth callback port.
Because Claude Code stores MCP OAuth tokens keyed by SERVER NAME, a unique
name per project means each project authenticates independently and can be
bound to a different Notion workspace via the /mcp -> Authenticate flow.

Usage:
    setup_notion_workspace.py [server_name] [callback_port]

Both args are optional:
    server_name    defaults to "notion-<current-dir>" (sanitized)
    callback_port  defaults to the lowest free port from 8123 upward,
                   computed by scanning callback ports already used by
                   notion-* servers across all projects in ~/.claude.json
"""
import json
import os
import pathlib
import subprocess
import sys

BASE_PORT = 8123
URL = "https://mcp.notion.com/mcp"
CLAUDE_JSON = pathlib.Path.home() / ".claude.json"
PLUGINS_JSON = pathlib.Path.home() / ".claude" / "plugins" / "installed_plugins.json"


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def collect_used_callback_ports(cfg):
    ports = set()
    scopes = list((cfg.get("projects") or {}).values()) + [cfg]
    for scope in scopes:
        for server in (scope.get("mcpServers") or {}).values():
            port = (server.get("oauth") or {}).get("callbackPort")
            if isinstance(port, int):
                ports.add(port)
    return ports


def pick_free_port(used):
    port = BASE_PORT
    while port in used:
        port += 1
    return port


def sanitize(name):
    cleaned = "".join(c if (c.isalnum() or c in "-_") else "-" for c in name)
    return cleaned.strip("-").lower() or "project"


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main():
    cwd = os.getcwd()
    cfg = load_json(CLAUDE_JSON)

    name = sys.argv[1] if len(sys.argv) > 1 else f"notion-{sanitize(os.path.basename(cwd))}"
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    else:
        port = pick_free_port(collect_used_callback_ports(cfg))

    # Warn (do NOT auto-remove) if the global notion plugin is installed: it
    # injects a single shared `notion` server into every project, which is the
    # usual reason workspaces end up shared. Removing it is a global action, so
    # leave that decision to the user.
    plugins = load_json(PLUGINS_JSON).get("plugins", {})
    if any(k.startswith("notion@") for k in plugins):
        print("! Global 'notion' plugin detected — it adds a shared 'notion' server to ALL projects.")
        print("  For true per-project isolation, remove it once:")
        print("    claude plugin uninstall notion@claude-plugins-official")
        print()

    # Drop any local-scope server that would collide on name (the shared
    # default `notion`, or a previous run of this same server).
    for victim in {"notion", name}:
        run(["claude", "mcp", "remove", victim], cwd)

    add = run(
        ["claude", "mcp", "add", "--transport", "http", name, URL,
         "--scope", "local", "--callback-port", str(port)],
        cwd,
    )
    if add.returncode != 0:
        print(add.stdout.strip())
        print(add.stderr.strip(), file=sys.stderr)
        sys.exit(1)

    print(add.stdout.strip())
    print()
    print(f"Done. Server '{name}' bound to this project (callback port {port}).")
    print("Next steps (manual, interactive):")
    print("  1. Restart Claude Code if the global plugin was just removed.")
    print(f"  2. Run /mcp -> select '{name}' -> Authenticate")
    print("  3. In the browser, pick THIS project's Notion workspace.")
    print("     (Ensure target pages have this integration added under ••• -> Connections.)")


if __name__ == "__main__":
    main()
