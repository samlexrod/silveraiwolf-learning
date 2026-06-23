# CLAUDE.md — silveraiwolf-learning

Repo-wide guidance for **SilverAIWolf Learning** — a catalog of hands-on, agent-guided tutorials that teach
**scalable, end-to-end AI engineering** across platforms (Databricks and beyond) up to enterprise (B2B) and
customer (B2C) applications. This file is the **constitution**: conventions every tutorial inherits. Each
tutorial may add its own `CLAUDE.md` that layers on top (and wins inside its own directory).

## What this repo is

A **monorepo of tutorials**, each packaged as a **Claude Code plugin** and listed in the repo-level
`silveraiwolf` marketplace (`.claude-plugin/marketplace.json`). A learner installs one plugin and walks it as
ordered, interactive **stages**. See `docs/STRUCTURE.md` for the full layout and `docs/AUTHORING.md` for how
to author a tutorial.

## Structure (platform-first)

```
tutorials/
  databricks/        # the Databricks platform — full breadth, many tutorials (all run on Free Edition, $0)
    end-to-end/      # the broad, all-features tour (start here); deep-dives are siblings
```

The repo currently ships the **Databricks** track. New tracks are added **as needed** (not pre-created as
empty dirs): vendor-neutral `ai-engineering/` (agents, RAG/context, eval, neurosymbolic guardrails),
`solutions/` for end-to-end B2B/B2C products, and future **platform tracks** (Snowflake, AWS, Azure, GCP,
open-source) as siblings of `databricks/`. See `docs/STRUCTURE.md`.

## Conventions every tutorial follows

1. **A tutorial = a Claude Code plugin** at `tutorials/<track>/<name>/.claude/plugins/<plugin>/`:
   `plugin.json` + a single `commands/start.md` orchestrator + `stages/NN-<name>.md` + optional pushable
   `notebooks/`. Author docs (`CLAUDE.md`, `ROADMAP.md`) live at the tutorial root and are **not shipped**.
2. **One command, ordered stages.** The orchestrator walks stages one at a time, advancing only on
   confirmation, and persists progress to a gitignored `PROGRESS.md` so a fresh chat can resume.
3. **Plugin naming:** `silver-<topic>-<name>` (e.g. `silver-databricks-end-to-end`).
4. **Cost framing matches the platform.** For Free Edition tutorials, cost = fair-use **quota**, never $.
   Any step that costs real money (e.g. a learner's own cloud account) is an explicit, opt-in callout.
5. **Provision via CLI/code, not the UI** — production is automation, not click-ops. Deliver data *workloads*
   as notebooks the learner runs; do the plumbing (auth, CLI, infra) for them.
6. **Verify before you claim.** A stage is done only after a live check passes; surface real output.
7. **Reuse across tutorials.** Keep dataset/asset names aligned across tutorials so lessons transfer; when a
   fixture is genuinely shared by more than one tutorial, introduce a top-level `shared/` for it (not before).

## Adding a tutorial

Three steps (see `docs/STRUCTURE.md`): create `tutorials/<track>/<name>/…` from the template, add one entry
to the repo-level `.claude-plugin/marketplace.json`, and add a catalog row to `README.md`.
