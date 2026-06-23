<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# AI/BI + Genie over the semantic layer

Let non-technical users at Silverline Capital consume the governed metrics two ways — **AI/BI dashboards**
(charts) and **Genie** (plain-English Q&A) — both reading the **same** `portfolio_metrics` Metric View, so a
tile and a Genie answer for "total billed" can never disagree.

**Cost:** Free — counts against your fair-use quota. Dashboards + Genie spaces are free objects; a tile
refresh or a Genie answer uses a sliver of serverless compute.

**Precondition:** `semantic` done — `silverline.gold.portfolio_metrics` exists; the Starter Warehouse
runs.

This is an **interactive walkthrough** — pause after each section.

> 🏗️ **Provisioned via CLI, not clicked** — like every other stage. Both the dashboard and the Genie space
> are **AI/BI objects the Databricks CLI can create** (verified live on Free Edition): `databricks lakeview
> create`/`publish` and `databricks genie create-space`. Claude builds them from code (`scripts/provision_ai_bi.sh`
> + the JSON specs in `dashboards/`); the learner **opens them in the UI to explore**. The notebook
> `12-ai-bi/12.1_ai_bi` runs the tile queries + links the live surfaces.

---

## Section 1 — AI/BI dashboard over the metric view (created via CLI)

Claude creates a Lakeview dashboard from `dashboards/portfolio_dashboard.lvdash.json` — three tiles, each a
**`MEASURE()` query over the metric view**:

```bash
databricks lakeview create \
  --display-name "Silverline Capital — Portfolio (governed metrics)" \
  --warehouse-id "$DATABRICKS_WAREHOUSE_ID" \
  --serialized-dashboard "$(cat dashboards/portfolio_dashboard.lvdash.json)"
# then publish so it renders for viewers:
databricks lakeview publish <dashboard_id> --warehouse-id "$DATABRICKS_WAREHOUSE_ID" --embed-credentials
```

The three datasets: **billed by segment**, **billed by contract type**, **overdue ratio by region** — all
`SELECT … MEASURE(…) FROM silverline.gold.portfolio_metrics GROUP BY …`.

> 🧠 Because the tiles use `MEASURE(...)` over the metric view, they inherit the **governed definition** —
> not a hand-written `SUM()` that could drift between tiles.

**Pause.** Open the published dashboard and confirm it renders billed-by-segment + by-contract-type + overdue-ratio-by-region (render as `AskUserQuestion`).

---

## Section 2 — A Genie space over the metric view (created via CLI)

Claude creates a Genie space scoped to **`silverline.gold.portfolio_metrics`** from `dashboards/genie_space.json`:

```bash
databricks genie create-space "$DATABRICKS_WAREHOUSE_ID" "$(cat dashboards/genie_space.json)" \
  --title "Silverline Capital — Portfolio Genie"
```

The serialized space pins the data source to the metric view + adds instructions ("read measures with
`MEASURE()`; don't recompute `overdue_ratio` by hand") + sample questions. Genie also reads the COMMENTs from
the `business-layer` stage.

> 🧠 **Why Genie over a metric view beats Genie over raw tables:** over raw tables Genie *guesses* the
> `SUM()`/join (and can guess wrong); over the metric view it uses the **governed `MEASURE(total_billed)`** →
> exact, consistent.

**Pause.** Open the Genie space and confirm its data asset is the metric view (render as `AskUserQuestion`).

---

## Section 3 — Ask in natural language

In the Genie space, ask:
- *"What is the total billed by segment?"* → expect `MEASURE(total_billed) GROUP BY segment`
- *"Which region has the highest overdue ratio?"* → expect `MEASURE(overdue_ratio) GROUP BY region`
- *"Billed amount by contract type"* → expect `MEASURE(total_billed) GROUP BY contract_type`

Genie shows the **generated SQL** + the answer. Because the space is over the metric view, the SQL uses the
governed measure — so the number matches the dashboard tile and `gold_segment_portfolio` exactly.

> ✅ **Verified live (CLI, via `genie start-conversation`):** "total billed by segment" generated
> `SELECT segment, MEASURE(total_billed) … GROUP BY ALL` → Manufacturing **$10,332,760.84** … Construction
> **$3,617,348.95**; "highest overdue ratio" generated `MEASURE(overdue_ratio)` → **West 0.1461** — identical
> to the dashboard tile, and *not* the hand-rolled 0.85 from `11.2`.

**Pause.** Confirm a natural-language question returns a sensible answer + measure-based SQL (render as `AskUserQuestion`).

---

## Section 3b — The many ways to use Genie (`12.2_genie_programmatic`)

Genie isn't only a chat box — it's a **programmatic NL→SQL service**. Each answer returns the **generated
SQL** (governed `MEASURE()`) *and* the result rows, so you can drive it from a notebook, a script, an app, or
an agent. The `12.2_genie_programmatic` notebook shows five ways:

- **Notebook / SDK** — `w.genie.start_conversation_and_wait(space, q)` → `attachments[].query.query` (SQL) +
  `.text.content` (answer); `get_message_attachment_query_result(...)` → the rows as a DataFrame.
- **Reuse the SQL** — run Genie's generated SQL yourself (`spark.sql(...)`) to promote a good answer into a
  query/tile/table — same governed number.
- **Multi-turn** — `create_message_and_wait(space, conversation_id, follow_up)` keeps context for drill-downs
  ("now just the top 3 by overdue amount").
- **CLI / REST** — `databricks genie start-conversation <space> "<q>" -o json` (language-agnostic; scripts/CI).
- **Chat (UI)** — Section 3 above.

> ✅ **Verified live (SDK):** asked "total billed by segment" → governed `MEASURE(total_billed) … GROUP BY ALL`
> + the six segment rows as a DataFrame; a follow-up "top 3 by overdue amount" kept context and emitted a
> windowed `MEASURE(overdue_amount)` query. Same governed measures everywhere.

The notebook also draws the line **Genie vs `ai_query()`**: Genie = governed NL→SQL (exact `MEASURE()` numbers);
`ai_query('<serving-endpoint>', prompt)` = LLM/ML inference in SQL (generative — can hallucinate, *not* for
"what's the total billed"). They're complementary — the notebook runs `ai_query()` over a **credit memo** (the
`seed`-stage unstructured docs) to summarize + risk-rate it, the job Genie is *not* for. Both verified live on
Free Edition (13 serving endpoints incl. `databricks-claude-opus-4-8`; no Genie serving endpoint — Genie is
the Conversation API). Bridge: wrap a Genie-backed agent as a serving endpoint → call via `ai_query()` (advanced).

`12.2` also packages this as a reusable **UC SQL function** — `silverline.gold.assess_credit_memo(memo)` wraps
`ai_query()` so any analyst risk-rates a memo from plain SQL (verified single + batch over the memos volume).
But **Genie can't be wrapped into a SQL-callable UC function** (verified live: UC Python UDFs are network-sandboxed
— `Network is unreachable`; `http_request()` isn't available here; and Genie's stateful async flow needs 3+ calls,
not one `SELECT`). Genie-as-a-function belongs in the **agent-tool** lane (`databricks_langchain.genie`).

**Pause.** Confirm you can ask Genie from the notebook and get back the SQL + result rows (render as `AskUserQuestion`).

---

## Section 4 — Why governed metrics make AI/BI trustworthy

| Without a semantic layer | With the metric view (this track) |
|---|---|
| Genie guesses `SUM()`/joins → can be wrong | Genie uses `MEASURE(total_billed)` → exact, governed |
| Dashboard SQL + Genie SQL can drift | both reference the **same** measure definition |
| "Billed" / "overdue ratio" differs per surface | one definition → dashboard == Genie == gold |

**Pause.** Confirm you can explain why Genie-over-a-metric-view beats Genie-over-raw-tables (render as `AskUserQuestion`).

---

## Recap

- ✓ An **AI/BI dashboard** over `portfolio_metrics` — governed charts (billed by segment / by contract type / overdue ratio by region)
- ✓ A **Genie space** over the same metric view — natural-language Q&A via the governed measures
- ✓ The payoff: **dashboard == Genie == gold**, because they share the semantic layer

**Cost now:** quota only. **Phase D (Analytics) complete** — stages 10–12 of 12 done. 🎉 **Tutorial complete.**
