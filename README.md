# 🐺 SilverAIWolf Learning

> **"Code with intent. Engineer with flow. Master the context."**

Hands-on, agent-guided tutorials for **scalable, end-to-end AI engineering** — across platforms (Databricks
and beyond) up to enterprise (B2B) and customer (B2C) applications. Each tutorial is a **Claude Code plugin**
you install and walk as ordered, interactive stages.

## 📚 Tutorial catalog

| Track | Tutorial | Plugin | What you build |
|---|---|---|---|
| Databricks | [end-to-end](./tutorials/databricks/end-to-end) | `silver-databricks-end-to-end` | A **$0 Free Edition** tour across the whole platform — Lakebase OLTP → medallion lakehouse → governed semantic layer → AI/BI + Genie + `ai_query` → **Mosaic AI Vector Search** + **pgvector-in-Lakebase** over the contract docs — 14 stages. |

More tracks are added as their first tutorial lands — vendor-neutral `ai-engineering/` (agents / RAG / eval /
guardrails), `solutions/{b2b,b2c}/` (end-to-end products), and other platform tracks. See
[`docs/STRUCTURE.md`](./docs/STRUCTURE.md).

## 🚀 Install a tutorial

**1. Clone the repo and start Claude from inside it — this is required.** The tutorial isn't self-contained
in the installed plugin: several stages read repo-root assets that the plugin install doesn't ship
(`scripts/*.py`, the dbt project, `mise` tasks, `.env`). So you must run the whole thing from the clone.

```bash
git clone https://github.com/samlexrod/silveraiwolf-learning.git
cd silveraiwolf-learning          # launch Claude Code from here (the repo root)
```

**2. Install the plugin.** Claude can do this for you — just say **“install the tutorial”** (the
`install-tutorial` skill). Or manually:

```bash
# from your local clone (recommended):
claude plugin marketplace add "$(git rev-parse --show-toplevel)"
claude plugin install silver-databricks-end-to-end@silveraiwolf

# or straight from GitHub:
claude plugin marketplace add samlexrod/silveraiwolf-learning
claude plugin install silver-databricks-end-to-end@silveraiwolf
```

After installing, **restart Claude Code** so the plugin's slash commands register. (`/reload-skills`
refreshes *skills* in the current session, but newly installed *commands* generally need a full restart —
if `/silver-databricks-end-to-end:start` reports "Unknown command", restart and try again.) Then run
`/silver-databricks-end-to-end:start` and walk the 14 stages.

> 🪟 **Windows:** the `claude` CLI ships inside the desktop app and may not be on your `PATH`. If `claude`
> isn't found, invoke it by full path, e.g.
> `& "$env:APPDATA\Claude\claude-code\<version>\claude.exe" plugin install silver-databricks-end-to-end@silveraiwolf`.

## 🗂️ Repository structure

A monorepo of tutorials, each a Claude Code plugin listed in the repo-level `silveraiwolf` marketplace
(`.claude-plugin/marketplace.json`). See [`docs/STRUCTURE.md`](./docs/STRUCTURE.md) for the layout and
[`docs/AUTHORING.md`](./docs/AUTHORING.md) for authoring conventions; [`CLAUDE.md`](./CLAUDE.md) is the
repo-wide constitution.

## 📄 License

[MIT](./License)
