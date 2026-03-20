---
description: Uninstall all silver-plan and silver-databricks plugin commands, clean workspace, and kill zombie agents
---

# Silver Wolf Cleanup

Remove all silver-plan and silver-databricks commands, clean workspace output, and kill zombie agents. This provides a clean state so `/silver-wolf-setup` can be re-run from scratch.

## Instructions

Run ALL steps automatically without asking. No prompts, no confirmations.

### 1. Remove installed commands

Remove the silver-plan command files from `~/.claude/commands/`:

```bash
rm -f ~/.claude/commands/silver-plan:prd-to-tdr.md
rm -f ~/.claude/commands/silver-plan:tdr-to-jira.md
rm -f ~/.claude/commands/silver-plan:okr-to-jira.md
rm -f ~/.claude/commands/silver-plan:dev-mode.md
rm -f ~/.claude/commands/silver-plan:clean-workspace.md
rm -f ~/.claude/commands/silver-plan:kill-zombies.md
rm -f ~/.claude/commands/silver-plan:help.md
rm -f ~/.claude/commands/silver-databricks:scaffold-setup.md
rm -f ~/.claude/commands/silver-databricks:setup.md
rm -f ~/.claude/commands/silver-databricks:create-scenario.md
rm -f ~/.claude/commands/silver-databricks:dev-mode.md
rm -f ~/.claude/commands/silver-databricks:start.md
```

Verify they were removed:

```bash
ls ~/.claude/commands/silver-plan:*.md ~/.claude/commands/silver-databricks:*.md 2>/dev/null || echo "All commands removed."
```

### 2. Clean workspace

Remove all pipeline output:

```bash
rm -rf .silveraiwolf/workspace/
```

### 3. Kill zombie agents

Find and kill any lingering agent processes:

```bash
ps aux | grep "agent-.*@silver-plan\|agent-.*@prd-to-tdr\|agent-.*@tdr-to-jira" | grep -v grep
```

If any exist, kill them all. Then clean up stale team directories:
- Remove all directories in `~/.claude/teams/` except `default`
- Remove matching task directories in `~/.claude/tasks/`

### 4. Report status

Display a summary of what was removed:
- Commands removed: list the files deleted
- Workspace cleaned: yes/no
- Zombie agents killed: count

Remind the user to **restart Claude Code** for changes to take effect.
