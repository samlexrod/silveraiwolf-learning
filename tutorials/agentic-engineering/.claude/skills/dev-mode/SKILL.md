---
description: "STOP. You are now in **development mode**."
---

STOP. You are now in **development mode**.

## What this means

- **Do NOT run any skill or pipeline.** Ignore all prior skill instructions from this conversation.
- **Do NOT scaffold projects, generate data, deploy, spawn agent teams, or write to `.silveraiwolf/workspace/`.**
- You are here to **develop, debug, and improve** the skills, plugins, commands, and templates themselves.

## What you should do

1. **Read the user's request carefully.** They want to modify something — fix a bug, add a feature, improve instructions, refactor an agent profile, update a template, etc.
2. **Read the relevant files** before making changes. The plugin and skill source files live under:
   - `.claude/plugins/` — Plugin directories (silver-plan, silver-databricks, etc.)
   - `.claude/skills/` — Standalone skills (silver-wolf-setup, silver-wolf-cleanup, etc.)
   - `.claude/commands/` — Shared commands
3. **Edit the files** using the Edit tool. Make targeted, minimal changes.
4. **Explain what you changed and why** so the user can verify.
5. **Do NOT test changes by running the skill/pipeline.** If the user wants to test, they will invoke the skill themselves in a separate session.

## Reminders

- Skills and agent profiles are instruction-driven — agents are LLMs following markdown prompts, not code. Changes are prose edits, not code refactors.
- When editing skill files (`SKILL.md`), preserve phase/step numbering so cross-references remain valid.
- When editing agent profiles, preserve output format sections — downstream agents depend on consistent structure.
