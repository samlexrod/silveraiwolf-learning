# Repository structure

SilverAIWolf Learning is a **monorepo of tutorials**, each packaged as a **Claude Code plugin** and listed in
one repo-level marketplace. The taxonomy is **platform-first**: a platform (or capability) track holds many
tutorials of varying depth.

```
silveraiwolf-learning/
├── README.md                      # mission + tutorial catalog + install instructions
├── CLAUDE.md                      # repo-wide authoring constitution (conventions all tutorials follow)
├── License
├── .gitignore
├── .claude-plugin/
│   └── marketplace.json           # repo-level "silveraiwolf" marketplace — one entry per tutorial plugin
├── .claude/
│   └── skills/install-tutorial/   # installer skill (lists the catalog, installs the chosen plugin)
├── docs/
│   ├── STRUCTURE.md               # this file
│   └── AUTHORING.md               # how to author a tutorial (stage-doc conventions)
└── tutorials/
    └── databricks/                # Databricks platform track — every tutorial runs on Free Edition ($0)
        └── end-to-end/            # the broad, all-features tour (the first tutorial)
            └── .claude/plugins/silver-databricks-end-to-end/
                ├── .claude-plugin/plugin.json
                ├── commands/start.md          # /silver-databricks-end-to-end:start
                ├── stages/NN-<name>.md
                └── notebooks/NN-<stage>/...
```

> The repo currently ships only the **Databricks** track. Other tracks are **added as needed** (not
> pre-created as empty dirs) — see "Adding a new track" below.

## How tutorials are packaged

A tutorial is a self-contained Claude Code plugin:

```
tutorials/<track>/<name>/
├── .claude/
│   ├── .claude-plugin/marketplace.json   # self-contained marketplace for isolated local dev
│   └── plugins/<plugin>/
│       ├── .claude-plugin/plugin.json    # name, version, description
│       ├── commands/start.md             # the single orchestrator command
│       ├── stages/NN-<name>.md           # ordered stage docs (plain markdown, not skills)
│       └── notebooks/                     # optional: workspace content the learner runs
├── CLAUDE.md                              # author guide (not shipped to the learner)
├── ROADMAP.md                             # author build tracker (not shipped)
└── (PROGRESS.md is created at runtime and gitignored)
```

## Adding a new tutorial

1. **Scaffold** `tutorials/<track>/<name>/` from an existing tutorial (copy the `.claude/` plugin skeleton +
   author docs). Name the plugin `silver-<topic>-<name>`.
2. **Register** it: add one object to `plugins[]` in the repo-level `.claude-plugin/marketplace.json`
   (`name`, `source` = `./tutorials/<track>/<name>/.claude/plugins/<plugin>`, `description`).
3. **Catalog** it: add a row to the table in `README.md`.

## Adding a new track

Tracks are created **only when their first tutorial lands** — no empty placeholder dirs. Planned tracks
(add as siblings of `databricks/` under `tutorials/` when needed):
- `ai-engineering/` — vendor-neutral: agents, RAG/context, eval, neurosymbolic guardrails
- `solutions/{b2b,b2c}/` — end-to-end AI products (may span platforms)
- other **platform tracks** — `snowflake/`, `aws/`, `azure/`, `gcp/`, `open-source/`

When a fixture is shared by more than one tutorial, introduce a top-level `shared/` for it at that point.

## Install mechanics

Both local and GitHub installs use the repo-level `silveraiwolf` marketplace → `<plugin>@silveraiwolf`.
The `.claude/skills/install-tutorial` skill performs the install. (Today it installs the single tutorial;
**near-term follow-up:** generalize it to list every plugin in the marketplace and install the learner's pick.)
