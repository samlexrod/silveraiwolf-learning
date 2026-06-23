<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Semantic layer — a governed Metric View

`gold_segment_portfolio` answers exactly one question (portfolio *by segment*). A **Metric View** answers
*every* slice of the same governed billing measures — by region, credit rating, contract type, status,
month — from one definition, so "billed" and "overdue ratio" can't drift between a dashboard, a notebook,
and Genie at Silverline Capital.

**Cost:** Free — counts against your fair-use quota. A Metric View is a UC object; querying it is a sliver
of serverless compute on the Starter Warehouse.

**Precondition:** `business-layer` done — `silverline.silver.{silver_invoices, silver_customers}` exist
and the gold is documented.

> ⚠️ **Metric View DDL is a newer UC feature** — verify the `WITH METRICS` / YAML keys against your
> workspace; the *shape* (source · joins · dimensions · measures · `MEASURE()`) is stable.

This is an **interactive walkthrough** — pause after each section.

---

## Section 1 — Review + create the metric view

The definition is `sql/portfolio_metrics.sql` — measures + dimensions over the silver billing fact. Open
it; then **paste it into the SQL editor and Run** (the `WITH METRICS` YAML is finicky over the CLI):

- **measures:** `total_billed` (SUM amount), `invoice_count`, `overdue_amount`, `overdue_ratio`
- **dimensions:** `segment`, `region`, `credit_rating`, `contract_type`, `status`, `invoice_date`
- **source:** `silver_invoices` (already conformed with `customer_id` + `contract_type`) joined to `silver_customers`

Measures are **definitions, not stored values** — resolved at whatever grain you query.

| One gold rollup per question | One Metric View, every question |
|---|---|
| `gold_segment_portfolio` = billed-by-segment only | `MEASURE(total_billed)` sliced by any dimension |
| New slice (by region, by contract type) = new SQL/table | Same measure, new `GROUP BY` |
| "Overdue ratio" reimplemented per query → drift | One `overdue_ratio` definition, reused everywhere |

**Pause.** Confirm `silverline.gold.portfolio_metrics` was created (render as `AskUserQuestion`).

---

## Section 2 — Query it: one definition, any slice

```bash
# Billed + invoice count by segment — the governed equivalent of the segment rollup:
mise run sql "SELECT segment, MEASURE(total_billed) AS total_billed, MEASURE(invoice_count) AS invoice_count
              FROM silverline.gold.portfolio_metrics GROUP BY segment ORDER BY total_billed DESC"

# The SAME measures, re-sliced — no new table, no new SQL logic:
mise run sql "SELECT region, contract_type, MEASURE(overdue_ratio) AS overdue_ratio
              FROM silverline.gold.portfolio_metrics GROUP BY region, contract_type ORDER BY overdue_ratio DESC"
mise run sql "SELECT date_trunc('quarter', invoice_date) AS qtr, MEASURE(total_billed) AS total_billed
              FROM silverline.gold.portfolio_metrics GROUP BY qtr ORDER BY qtr"
```

**Pause.** Confirm the by-segment query returns billed totals, and you can re-slice by region/contract_type and quarter (render as `AskUserQuestion`).

---

## Section 3 — Verify it matches gold

`gold_contract_aging` rolls billing up per contract; the metric view rolls the *same* `silver_invoices`
fact up by any dimension. Their grand total of billed amount must agree — same fact, same SUM, governed
once:

```bash
mise run sql "
WITH m AS (SELECT MEASURE(total_billed) tb FROM silverline.gold.portfolio_metrics),
     g AS (SELECT sum(total_billed) tb FROM silverline.gold.gold_contract_aging)
SELECT (SELECT tb FROM m) AS metric_view_billed,
       (SELECT tb FROM g) AS gold_billed,
       CASE WHEN (SELECT tb FROM m) <=> (SELECT tb FROM g) THEN 'MATCH' ELSE 'DRIFT' END AS result"
# expect MATCH — the metric view's total billed == the physical gold aging total
```

**Pause.** Confirm the result is `MATCH` — metric view == gold (render as `AskUserQuestion`).

---

## Section 4 — Why a Metric View, not just gold? (`11.2_why_metrics`)

A learner reasonably asks: the gold is already governed and documented — why add a metric view? The
`11.2_why_metrics` notebook **proves** the gap with three runnable demos (read-only, creates nothing):

1. **The "average of averages" trap.** `overdue_ratio` is non-additive. If gold *stored* the ratio per
   segment, rolling those rows up averages the ratios → **wrong** company number (verified live: **13.57%**
   averaged vs **11.29%** true — a ~20% overstatement). The metric view stores the *formula*, recomputing
   `SUM(overdue)/SUM(billed)` at your grain → always right.
2. **One grain vs any grain.** `gold_segment_portfolio` has no `region` column — "billed by region" is
   *impossible* from it without rewriting against silver. The metric view slices by region (or any of 6
   dimensions) in one `GROUP BY`. Pre-aggregating every combination is a table explosion.
3. **No drift across consumers.** A hand-rolled `overdue_ratio` with the wrong denominator returns **0.8494**
   vs the governed **0.1129** — the same KPI off by 7.5×. Defining it once means SQL, Genie, and the
   dashboard all agree.

It's **both, not either/or**: gold is the fast materialized slice; the metric view is the source-of-truth
definition (they `MATCH` by construction, Section 3).

**Pause.** Confirm the wrong-vs-right numbers diverge as described (render as `AskUserQuestion`).

---

## Recap

- ✓ A governed **Metric View** `portfolio_metrics` over the silver billing fact
- ✓ **Measures** + **dimensions** defined once, sliceable any way via `MEASURE()`
- ✓ Verified it **matches** the physical gold (gold = a materialized slice; the metric view = the definition)

**Cost now:** quota only.
