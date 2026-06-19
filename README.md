# 🐺 SilverAIWolf Learning

> **"Code with intent. Engineer with flow. Master the context."**

Hands-on, agent-guided tutorials for **scalable, end-to-end AI engineering** — across platforms (Databricks
and beyond) up to enterprise (B2B) and customer (B2C) applications. Each tutorial is a **Claude Code plugin**
you install and walk as ordered, interactive stages.

## 📚 Tutorial catalog

| Track | Tutorial | Plugin | What you build |
|---|---|---|---|
| Databricks | [end-to-end](./tutorials/databricks/end-to-end) | `silver-databricks-end-to-end` | A **$0 Free Edition** tour across the whole platform — Lakebase OLTP → medallion lakehouse → governed semantic layer → AI/BI + Genie + `ai_query` (12 stages). |

More tracks are added as their first tutorial lands — vendor-neutral `ai-engineering/` (agents / RAG / eval /
guardrails), `solutions/{b2b,b2c}/` (end-to-end products), and other platform tracks. See
[`docs/STRUCTURE.md`](./docs/STRUCTURE.md).

## 🚀 Install a tutorial

Claude can do this for you — just say **“install the tutorial”** (the `install-tutorial` skill). Or manually:

```bash
# from a local clone:
claude plugin marketplace add "$(git rev-parse --show-toplevel)"
claude plugin install silver-databricks-end-to-end@silveraiwolf

# or from GitHub (once pushed):
claude plugin marketplace add samlexrod/silveraiwolf-learning
claude plugin install silver-databricks-end-to-end@silveraiwolf
```

Then run `/silver-databricks-end-to-end:start` and walk the 12 stages.

## 🗂️ Repository structure

A monorepo of tutorials, each a Claude Code plugin listed in the repo-level `silveraiwolf` marketplace
(`.claude-plugin/marketplace.json`). See [`docs/STRUCTURE.md`](./docs/STRUCTURE.md) for the layout and
[`docs/AUTHORING.md`](./docs/AUTHORING.md) for authoring conventions; [`CLAUDE.md`](./CLAUDE.md) is the
repo-wide constitution.

## 📄 License

[MIT](./License)
