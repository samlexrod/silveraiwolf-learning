-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Stage 12 — AI/BI + Genie over the semantic layer (the finale 🎉)
-- MAGIC
-- MAGIC Non-technical users at Silverline consume the governed metrics two ways — an **AI/BI dashboard** (charts)
-- MAGIC and **Genie** (plain-English Q&A) — **both reading the same `silverline.gold.portfolio_metrics` Metric
-- MAGIC View**, so a tile and a Genie answer for "total billed" can never disagree.
-- MAGIC
-- MAGIC > 🏗️ **Provisioned via CLI, not clicked.** Like every other stage, the dashboard + Genie space were
-- MAGIC > created from code — `databricks lakeview create`/`publish` and `databricks genie create-space` (see
-- MAGIC > `scripts/provision_ai_bi.sh` + the JSON in `dashboards/`). The UI is for *exploring* them, not building.
-- MAGIC
-- MAGIC This notebook runs the exact tile queries so you can see the data, then links the live surfaces. Run on
-- MAGIC the **SQL warehouse**.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 1 — The dashboard tiles (governed `MEASURE()` queries)
-- MAGIC These three queries are the dashboard's datasets — each reads `MEASURE()` over the metric view, never a
-- MAGIC hand-written `SUM()`. **Tile 1 — total billed by segment:**

-- COMMAND ----------

SELECT segment,
       MEASURE(total_billed)  AS total_billed,
       MEASURE(invoice_count) AS invoice_count
FROM silverline.gold.portfolio_metrics
GROUP BY segment ORDER BY total_billed DESC;

-- COMMAND ----------

-- MAGIC %md **Tile 2 — total billed by contract type:**

-- COMMAND ----------

SELECT contract_type, MEASURE(total_billed) AS total_billed
FROM silverline.gold.portfolio_metrics
GROUP BY contract_type ORDER BY total_billed DESC;

-- COMMAND ----------

-- MAGIC %md **Tile 3 — overdue ratio by region (collections risk):**

-- COMMAND ----------

SELECT region, MEASURE(overdue_ratio) AS overdue_ratio
FROM silverline.gold.portfolio_metrics
GROUP BY region ORDER BY overdue_ratio DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2 — Open the live AI/BI dashboard
-- MAGIC Already created + published for you (`lakeview create` → `publish --embed-credentials`). Open it:
-- MAGIC
-- MAGIC 👉 **[Silverline Capital — Portfolio (governed metrics)](/dashboardsv3/01f16a399b5116abb2d3293e9060a10d/published)**
-- MAGIC
-- MAGIC You'll see the three tiles above as charts. Edit one and you'll find each tile bound to the
-- MAGIC `portfolio_metrics` dataset — the governed definition, not a per-tile `SUM()` that could drift.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 3 — Open the Genie space + ask in natural language
-- MAGIC A Genie space scoped to the **metric view** was created for you (`genie create-space`). Open it:
-- MAGIC
-- MAGIC 👉 **[Silverline Capital — Portfolio Genie](/genie/rooms/01f16a39c0fa1592b293e173ace9d5ee)**
-- MAGIC
-- MAGIC Try the sample questions (or your own):
-- MAGIC - *"What is the total billed by segment?"*
-- MAGIC - *"Which region has the highest overdue ratio?"*
-- MAGIC - *"Billed amount by contract type"*
-- MAGIC
-- MAGIC Genie shows the **generated SQL** + the answer. Because the space is over the metric view, the SQL uses
-- MAGIC the governed measure — so the number matches the dashboard tile and gold exactly.
-- MAGIC
-- MAGIC > ✅ **Verified live when this was built.** Asking *"total billed by segment"* generated
-- MAGIC > `SELECT segment, MEASURE(total_billed) … GROUP BY ALL` and returned Manufacturing **$10,332,760.84** …
-- MAGIC > Construction **$3,617,348.95**. Asking *"highest overdue ratio"* generated `MEASURE(overdue_ratio)` and
-- MAGIC > returned **West 0.1461** — identical to Tile 3 above. Genie used `MEASURE()`, **not** a hand-rolled
-- MAGIC > ratio (which `11.2` showed drifts to 0.85). Same definition, same number, everywhere.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 4 — Why governed metrics make AI/BI trustworthy
-- MAGIC
-- MAGIC | Without a semantic layer | With the metric view (this tutorial) |
-- MAGIC |---|---|
-- MAGIC | Genie guesses `SUM()` / joins → can be wrong | Genie uses `MEASURE(total_billed)` → exact, governed |
-- MAGIC | Dashboard SQL + Genie SQL can drift | both reference the **same** measure definition |
-- MAGIC | "Billed" / "overdue ratio" differs per surface | one definition → **dashboard == Genie == gold** |

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 🎉 Tutorial complete
-- MAGIC You took Silverline Capital from a **Lakebase OLTP** source → **medallion** (bronze/silver/gold, three
-- MAGIC ways) → a **governed semantic layer** → **AI/BI + Genie** — all $0/quota on **Databricks Free Edition**,
-- MAGIC and all **provisioned via CLI/code**, the way production is built.
-- MAGIC
-- MAGIC - ✓ An **AI/BI dashboard** over `portfolio_metrics` — governed charts
-- MAGIC - ✓ A **Genie space** over the same metric view — natural-language Q&A via the governed measures
-- MAGIC - ✓ The payoff: **dashboard == Genie == gold**, because they share the semantic layer
