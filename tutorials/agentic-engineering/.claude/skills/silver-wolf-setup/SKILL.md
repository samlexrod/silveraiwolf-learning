---
description: Install the SilverAIWolf Agentic Engineering environment — tmux, agent teams, and silver-plan plugin
---

# Agentic Engineering Setup

Install tmux, configure Claude Code agent teams, and install the silver-plan plugin globally so all skills and commands are available across sessions.

## Instructions

Follow these steps in order:

### 1. Check prerequisites

Run these checks and report any missing tools:

```bash
which git && git --version
brew --version
claude --version
```

- If `brew` is missing, tell the user to install it from https://brew.sh and stop.
- If `claude` is missing, tell the user to run `npm install -g @anthropic-ai/claude-code` and stop.

### 2. Install tmux

Run `tmux -V`. If not installed, run `brew install tmux`. Confirm it installed successfully.

### 3. Configure Claude Code settings

Read `~/.claude/settings.json` if it exists. Ensure it contains:

- `"env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" }`
- `"permissions": { "allow": [ "Read", "Write", "Edit", "Glob", "Grep", "Bash", "ToolSearch", "TaskUpdate", "TaskList", "TaskGet", "TaskCreate", "SendMessage" ] }`

These permissions let teammates read/write files, run commands, track tasks, and communicate without blocking on permission prompts.

If the file doesn't exist, create it with those settings. If it exists, merge the required keys without removing existing settings. For `permissions.allow`, append entries to any existing allow list without duplicating.

### 4. Configure teammate display mode

Ask the user which `teammateMode` they prefer:

**`"tmux"` — Split panes** (recommended for learning):
- Each agent opens in a visible tmux split pane so you can watch agents work side by side
- Great for understanding how agent teams coordinate

**`"in-process"` — Inline mode**:
- All teammates run inside your main terminal
- Use Shift+Down to cycle through teammates and type to message them directly
- Works in any terminal, including VS Code and Cursor

**`"auto"` — Automatic** (default):
- Uses split panes if already inside a tmux session, otherwise falls back to in-process

Set `"teammateMode"` in `~/.claude/settings.json`. If `"auto"`, skip since it's the default.

**Note**: `teammateMode` is an experimental field that may not be in the settings schema yet. If the Edit tool rejects it due to schema validation, use the Bash tool to write the file with `jq` or `python3 -c`, bypassing schema validation.

If the user selected `"tmux"` mode:

1. Show tmux navigation:

   | Action | Shortcut |
   |--------|----------|
   | Move to next pane | `Ctrl-b` then `o` |
   | Move by direction | `Ctrl-b` then arrow key |
   | Show pane numbers | `Ctrl-b` then `q` |
   | Zoom pane fullscreen | `Ctrl-b` then `z` |
   | Enter scroll/copy mode | `Ctrl-b` then `[` (press `q` to exit) |

2. Enable mouse support — check if `~/.tmux.conf` contains `set -g mouse on`. If not, append it. If tmux is running, reload with `tmux source-file ~/.tmux.conf`.

### 5. Locate the silver-plan plugin

The plugin directory is at `.claude/plugins/silver-plan/` relative to this project root. Verify it exists:

```bash
ls .claude/plugins/silver-plan/.claude-plugin/plugin.json
ls .claude/plugins/silver-plan/skills/
ls .claude/plugins/silver-plan/shared/agents/
ls .claude/plugins/silver-plan/commands/
```

If not found, inform the user the plugin is missing.

### 6. Install silver-plan commands globally

Claude Code discovers custom slash commands from `~/.claude/commands/`. Copy each skill and command file from the plugin into that directory with the `silver-plan:` namespace prefix.

1. Ensure `~/.claude/commands/` exists:
   ```bash
   mkdir -p ~/.claude/commands
   ```

2. Copy the skill files (these are the pipeline entry points):
   ```bash
   cp .claude/plugins/silver-plan/skills/prd-to-tdr/SKILL.md ~/.claude/commands/silver-plan:prd-to-tdr.md
   cp .claude/plugins/silver-plan/skills/tdr-to-jira/SKILL.md ~/.claude/commands/silver-plan:tdr-to-jira.md
   cp .claude/plugins/silver-plan/skills/okr-to-jira/SKILL.md ~/.claude/commands/silver-plan:okr-to-jira.md
   ```

3. Copy the plugin commands:
   ```bash
   cp .claude/plugins/silver-plan/commands/dev-mode.md ~/.claude/commands/silver-plan:dev-mode.md
cp .claude/plugins/silver-plan/commands/clean-workspace.md ~/.claude/commands/silver-plan:clean-workspace.md
   cp .claude/plugins/silver-plan/commands/kill-zombies.md ~/.claude/commands/silver-plan:kill-zombies.md
   cp .claude/plugins/silver-plan/commands/help.md ~/.claude/commands/silver-plan:help.md
   ```

4. Verify all files were copied:
   ```bash
   ls ~/.claude/commands/silver-plan:*.md
   ```

### 7. Install silver-databricks commands globally

1. Verify the plugin exists:
   ```bash
   ls .claude/plugins/silver-databricks/.claude-plugin/plugin.json
   ls .claude/plugins/silver-databricks/skills/
   ```

2. Copy the skill and command files:
   ```bash
   cp .claude/plugins/silver-databricks/skills/create-scenario/SKILL.md ~/.claude/commands/silver-databricks:create-scenario.md
   cp .claude/plugins/silver-databricks/commands/dev-mode.md ~/.claude/commands/silver-databricks:dev-mode.md
   cp .claude/plugins/silver-databricks/commands/start.md ~/.claude/commands/silver-databricks:start.md
   ```

3. Verify:
   ```bash
   ls ~/.claude/commands/silver-databricks:*.md
   ```

### 8. Report status

Display a summary:

- **tmux**: installed version
- **Agent teams**: enabled with permissions
- **Teammate mode**: user's choice
- **Plugin source**: resolved absolute path to `.claude/plugins/silver-plan/`
- **Installed to**: `~/.claude/commands/`
- **Available skills** (after restart):
  - `/silver-plan:prd-to-tdr` — Generate a TDR from a PRD
  - `/silver-plan:tdr-to-jira` — Generate JIRA tickets from a TDR
  - `/silver-plan:okr-to-jira` — Run the full end-to-end pipeline
- **Available commands** (after restart):
  - `/silver-plan:dev-mode` — Edit the plugin itself
- `/silver-plan:clean-workspace` — Clean pipeline output
  - `/silver-plan:kill-zombies` — Kill stale agent processes
- **silver-databricks** (after restart):
  - `/silver-databricks:create-scenario` — Scaffold a financial risk pipeline project
  - `/silver-databricks:dev-mode` — Edit the tutorial itself

Remind the user to **restart Claude Code** for the new commands to appear in autocomplete.

**IMPORTANT**: Skills reference files via project-relative paths. They must be invoked from this project's root directory for paths to resolve correctly.
