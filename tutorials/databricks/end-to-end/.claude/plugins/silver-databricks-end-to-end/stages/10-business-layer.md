<!-- gate:explain-then-start -->
> **On invocation — explain first, then gate.** Before running anything, give the learner a
> plain-language overview of *what this stage does and provisions, and how* — the key resources, the
> mechanism, and the **cost**. Then render an **`AskUserQuestion`**: **"Start the stage, or keep
> asking questions first?"** — **Start** proceeds to the first section; **Keep asking** stays in Q&A
> and provisions nothing. Only advance past this gate on **Start**.

# Business layer — govern + document the gold

The medallion already produced `silverline.gold.gold_segment_portfolio` and `gold_contract_aging` for
Silverline Capital. This stage makes them a proper **business layer**: documented (table + column
**COMMENTs**) so **Genie and AI assistants understand the schema**, plus a curated cross-table view.
(Comments are the lakehouse equivalent of dbt's `persist_docs` — they drive Genie disambiguation + the
semantic layer next.)

**Cost:** Free — counts against your fair-use quota. `COMMENT ON` / a view are metadata-only ops.

**Precondition:** `medallion` done — `silverline.gold.*` exist.

This is an **interactive walkthrough** — pause after each section.

---

## Section 1 — Document the gold (COMMENTs for Genie/AI)

Run in the SQL editor (or `mise run sql` per statement):

```sql
COMMENT ON TABLE silverline.gold.gold_segment_portfolio IS 'Financing portfolio rolled up per customer segment — contract counts, principal, APR, residual.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN segment          COMMENT 'Customer business segment.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN contract_count   COMMENT 'Total lease/loan contracts in the segment.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN active_contracts COMMENT 'Contracts currently in active status.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN total_principal  COMMENT 'Sum of contract principal financed for the segment.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN avg_apr          COMMENT 'Average annual percentage rate across the segment''s contracts.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN total_residual   COMMENT 'Sum of residual (end-of-term) value across the segment''s contracts.';

COMMENT ON TABLE silverline.gold.gold_contract_aging IS 'Billing/collections aging per contract — overdue / open / paid / total billed.';
ALTER TABLE silverline.gold.gold_contract_aging ALTER COLUMN contract_id    COMMENT 'Lease/loan contract identifier.';
ALTER TABLE silverline.gold.gold_contract_aging ALTER COLUMN overdue_amount COMMENT 'Sum of overdue invoice amounts for the contract.';
ALTER TABLE silverline.gold.gold_contract_aging ALTER COLUMN open_amount    COMMENT 'Sum of open (billed, not yet paid or overdue) invoice amounts.';
ALTER TABLE silverline.gold.gold_contract_aging ALTER COLUMN paid_amount    COMMENT 'Sum of paid invoice amounts.';
ALTER TABLE silverline.gold.gold_contract_aging ALTER COLUMN total_billed   COMMENT 'Sum of all invoice amounts billed against the contract.';
```

> 🧠 **Why comments matter here:** Genie (next phase) generates SQL from natural language — column COMMENTs
> are what it reads to map "billed" → `total_billed` and "overdue" → `overdue_amount`. Undocumented gold =
> worse Genie answers.

| Undocumented gold | Documented gold (this section) |
|---|---|
| Genie sees only column *names* → guesses meaning | Genie reads COMMENTs → maps "overdue" → `overdue_amount` |
| Analysts re-ask "what is `total_residual`?" | Definition lives in the catalog, once |
| Semantic layer authored blind | Comments seed the Metric View dimensions/measures next |

**Pause.** Confirm the gold tables + key columns now carry comments (`DESCRIBE TABLE EXTENDED silverline.gold.gold_segment_portfolio`) (render as `AskUserQuestion`).

---

## Section 2 — A curated business view

A thin, business-named view joining contract aging to the customer profile for a "customer 360" collections
surface:

```sql
CREATE OR REPLACE VIEW silverline.gold.customer_360 (
  customer_id    COMMENT 'Customer id',
  legal_name     COMMENT 'Customer legal name',
  segment        COMMENT 'Business segment',
  region         COMMENT 'Region',
  credit_rating  COMMENT 'Credit rating',
  overdue_amount COMMENT 'Overdue billed amount across the customer''s contracts',
  total_billed   COMMENT 'Total billed amount across the customer''s contracts'
) COMMENT 'Per-customer collections view: profile + contract aging — the curated business surface.'
AS
SELECT c.customer_id, c.legal_name, c.segment, c.region, c.credit_rating,
       sum(a.overdue_amount) AS overdue_amount,
       sum(a.total_billed)   AS total_billed
FROM silverline.gold.gold_contract_aging a
JOIN silverline.silver.silver_contracts ct ON ct.contract_id = a.contract_id
JOIN silverline.silver.silver_customers c  ON c.customer_id  = ct.customer_id
GROUP BY c.customer_id, c.legal_name, c.segment, c.region, c.credit_rating;
```

> 🧠 `gold_contract_aging` is keyed by `contract_id`; a customer can hold several contracts. The view rolls
> aging up to the customer via `silver_contracts` (which carries `customer_id`), so collections can see one
> row per customer — exactly the grain Genie and the dashboards want.

**Pause.** Confirm `silverline.gold.customer_360` resolves + returns rows (render as `AskUserQuestion`).

---

## Recap

- ✓ Gold **documented** (table + column COMMENTs) — the business layer Genie/AI can understand
- ✓ A curated **`customer_360`** view (customer profile + contract aging, rolled to the customer grain)
- ✓ Comments = the lakehouse `persist_docs` — they power Genie + the semantic layer next

**Cost now:** quota only.
