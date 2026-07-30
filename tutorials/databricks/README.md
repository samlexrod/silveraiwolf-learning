# Databricks track

Tutorials for the **Databricks** platform — its full breadth, not just data/lakehouse: Lakebase (serverless
OLTP Postgres), the medallion lakehouse, Unity Catalog governance, dbt, Metric Views, AI/BI dashboards,
Genie, `ai_query`/Model Serving, Mosaic AI agents, and more.

> 💸 **Every tutorial in this track runs on Databricks Free Edition — $0, serverless, no cloud account.**
> Cost is framed as fair-use **quota**, never dollars. Any step that would cost real money (e.g. an external
> location in the learner's own cloud account) is an explicit, opt-in callout.

## Tutorials

| Tutorial | Plugin | What it covers |
|---|---|---|
| [`end-to-end/`](./end-to-end) | `silver-databricks-end-to-end` | The **broad, all-features tour** — 13 stages from Lakebase OLTP → medallion → governed semantic layer → AI/BI + Genie → Vector Search retrieval. **Start here.** |

### Planned deep-dives (siblings of `end-to-end/`)

Where `end-to-end` is one wide pass over everything, these go **deep** on one area:

- `streaming/` — CDC + Auto Loader + DLT/SDP streaming pipelines
- `ml-serving/` — MLflow tracking + Model Serving endpoints
- `mosaic-agents/` — Mosaic AI Agent Framework + evaluation
- `governance/` — Unity Catalog lineage, masking, access control

Add one by following `docs/STRUCTURE.md` (new tutorial dir + a marketplace entry + a catalog row).
