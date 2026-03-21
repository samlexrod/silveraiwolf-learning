---
description: "[Stage 0] Install the SilverAIWolf Agentic Engineering environment — tmux, agent teams, and all plugins"
---

# Agentic Engineering Setup

Install tmux, configure Claude Code agent teams, and install all plugins (silver-plan, silver-databricks, silver-databricks-streaming) globally so all skills and commands are available across sessions.

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
- `"permissions": { "allow": [ "Read", "Write", "Edit", "Glob", "Grep", "Bash", "ToolSearch", "TaskUpdate", "TaskList", "TaskGet", "TaskCreate", "SendMessage" ], "deny": [ "Edit .env", "Write .env", "Edit **/.env", "Write **/.env" ] }`

These permissions let teammates read/write files, run commands, track tasks, and communicate without blocking on permission prompts. The `deny` rules prevent accidentally writing secrets to `.env` files — credentials should only be added manually by the user.

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

### 5. Locate all plugins

The plugins live at `.claude/plugins/` relative to this project root. Verify each exists:

```bash
# silver-plan
ls .claude/plugins/silver-plan/.claude-plugin/plugin.json
ls .claude/plugins/silver-plan/skills/
ls .claude/plugins/silver-plan/shared/agents/
ls .claude/plugins/silver-plan/commands/

# silver-databricks
ls .claude/plugins/silver-databricks/.claude-plugin/plugin.json
ls .claude/plugins/silver-databricks/skills/
ls .claude/plugins/silver-databricks/commands/

# silver-databricks-streaming
ls .claude/plugins/silver-databricks-streaming/.claude-plugin/plugin.json
ls .claude/plugins/silver-databricks-streaming/skills/
ls .claude/plugins/silver-databricks-streaming/commands/
```

Report any missing plugins to the user.

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
   cp .claude/plugins/silver-plan/commands/clean-workspace.md ~/.claude/commands/silver-plan:clean-workspace.md
   cp .claude/plugins/silver-plan/commands/kill-zombies.md ~/.claude/commands/silver-plan:kill-zombies.md
   cp .claude/plugins/silver-plan/commands/help.md ~/.claude/commands/silver-plan:help.md
   ```

4. Verify all files were copied:
   ```bash
   ls ~/.claude/commands/silver-plan:*.md
   ```

### 7. Install silver-databricks commands globally

1. Copy all skill and command files:
   ```bash
   cp .claude/plugins/silver-databricks/skills/scaffold-setup/SKILL.md ~/.claude/commands/silver-databricks:scaffold-setup.md
   cp .claude/plugins/silver-databricks/skills/deploy-dev/SKILL.md ~/.claude/commands/silver-databricks:deploy-dev.md
   cp .claude/plugins/silver-databricks/skills/run-bronze/SKILL.md ~/.claude/commands/silver-databricks:run-bronze.md
   cp .claude/plugins/silver-databricks/skills/run-silver/SKILL.md ~/.claude/commands/silver-databricks:run-silver.md
   cp .claude/plugins/silver-databricks/skills/run-gold/SKILL.md ~/.claude/commands/silver-databricks:run-gold.md
   cp .claude/plugins/silver-databricks/skills/run-cicd/SKILL.md ~/.claude/commands/silver-databricks:run-cicd.md
   cp .claude/plugins/silver-databricks/skills/cleanup/SKILL.md ~/.claude/commands/silver-databricks:cleanup.md
   cp .claude/plugins/silver-databricks/commands/start.md ~/.claude/commands/silver-databricks:start.md
   ```

2. Verify:
   ```bash
   ls ~/.claude/commands/silver-databricks:*.md
   ```

### 8. Install silver-databricks-streaming commands globally

1. Copy all skill and command files:
   ```bash
   cp .claude/plugins/silver-databricks-streaming/skills/infra-setup/SKILL.md ~/.claude/commands/silver-databricks-streaming:infra-setup.md
   cp .claude/plugins/silver-databricks-streaming/skills/seed-postgres/SKILL.md ~/.claude/commands/silver-databricks-streaming:seed-postgres.md
   cp .claude/plugins/silver-databricks-streaming/skills/stream-bronze/SKILL.md ~/.claude/commands/silver-databricks-streaming:stream-bronze.md
   cp .claude/plugins/silver-databricks-streaming/skills/stream-silver/SKILL.md ~/.claude/commands/silver-databricks-streaming:stream-silver.md
   cp .claude/plugins/silver-databricks-streaming/skills/stream-gold/SKILL.md ~/.claude/commands/silver-databricks-streaming:stream-gold.md
   cp .claude/plugins/silver-databricks-streaming/skills/run-jobs/SKILL.md ~/.claude/commands/silver-databricks-streaming:run-jobs.md
   cp .claude/plugins/silver-databricks-streaming/skills/simulate-changes/SKILL.md ~/.claude/commands/silver-databricks-streaming:simulate-changes.md
   cp .claude/plugins/silver-databricks-streaming/skills/verify-cdc/SKILL.md ~/.claude/commands/silver-databricks-streaming:verify-cdc.md
   cp .claude/plugins/silver-databricks-streaming/skills/production-notes/SKILL.md ~/.claude/commands/silver-databricks-streaming:production-notes.md
   cp .claude/plugins/silver-databricks-streaming/skills/cleanup/SKILL.md ~/.claude/commands/silver-databricks-streaming:cleanup.md
   cp .claude/plugins/silver-databricks-streaming/commands/start.md ~/.claude/commands/silver-databricks-streaming:start.md
   ```

2. Verify:
   ```bash
   ls ~/.claude/commands/silver-databricks-streaming:*.md
   ```

### 9. Report status

Display a summary:

- **tmux**: installed version
- **Agent teams**: enabled with permissions
- **Teammate mode**: user's choice
- **Plugin sources**: resolved absolute paths to `.claude/plugins/`
- **Installed to**: `~/.claude/commands/`
- **silver-plan** (after restart):
  - `/silver-plan:prd-to-tdr` — Generate a TDR from a PRD
  - `/silver-plan:tdr-to-jira` — Generate JIRA tickets from a TDR
  - `/silver-plan:okr-to-jira` — Run the full end-to-end pipeline
  - `/silver-plan:clean-workspace` — Clean pipeline output
  - `/silver-plan:kill-zombies` — Kill stale agent processes
  - `/silver-plan:help` — Show all silver-plan commands
- **silver-databricks** (after restart):
  - `/silver-databricks:scaffold-setup` — Scaffold project + configure Databricks credentials
  - `/silver-databricks:deploy-dev` — Create Unity Catalog landing zone + upload seed data
  - `/silver-databricks:run-bronze` — Deploy and run Bronze pipeline
  - `/silver-databricks:run-silver` — Deploy and run Silver pipeline
  - `/silver-databricks:run-gold` — Deploy and run Gold pipeline
  - `/silver-databricks:run-cicd` — Run CI/CD locally then deploy to production
  - `/silver-databricks:cleanup` — Delete all Databricks artifacts
  - `/silver-databricks:start` — Show the tutorial overview
- **silver-databricks-streaming** (after restart):
  - `/silver-databricks-streaming:infra-setup` — Set up streaming infrastructure
  - `/silver-databricks-streaming:seed-postgres` — Seed PostgreSQL source data
  - `/silver-databricks-streaming:stream-bronze` — Stream raw data to Bronze
  - `/silver-databricks-streaming:stream-silver` — Stream cleaned data to Silver
  - `/silver-databricks-streaming:stream-gold` — Stream business metrics to Gold
  - `/silver-databricks-streaming:run-jobs` — Run streaming jobs
  - `/silver-databricks-streaming:simulate-changes` — Simulate CDC changes
  - `/silver-databricks-streaming:verify-cdc` — Verify CDC propagation
  - `/silver-databricks-streaming:production-notes` — Production deployment notes
  - `/silver-databricks-streaming:cleanup` — Clean up streaming resources
  - `/silver-databricks-streaming:start` — Show the tutorial overview
- **General commands** (after restart):
  - `/dev-mode` — Switch to development mode (works for any plugin)

Remind the user to **restart Claude Code** for the new commands to appear in autocomplete.

**IMPORTANT**: Skills reference files via project-relative paths. They must be invoked from this project's root directory for paths to resolve correctly.
