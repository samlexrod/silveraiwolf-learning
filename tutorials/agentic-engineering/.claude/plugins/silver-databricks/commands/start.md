[Stage 0] Show all available silver-databricks commands and skills. Do NOT run any of them. Display ALL content below VERBATIM — do not summarize, condense, or reformat. Output every section exactly as written.

---

# SilverAIWolf's Databricks Tutorial

### Medallion Architecture

> **The Scenario:** You just joined the data engineering team at a mid-size investment firm.
> The risk department needs a pipeline that ingests counterparty data, transaction feeds,
> and market prices — then transforms them into clean, validated datasets and finally
> produces financial ratios, risk exposure tiers, and portfolio summaries that traders
> and compliance officers can act on. Good news: the platform team already has a workflow
> that fetches data from the counterparty API and lands it as raw files — it's ready to
> be ingested. Your job: build the pipeline from scratch on Databricks, layer by layer,
> using the medallion architecture.

---

### Prerequisites

Before running any stage, make sure you have:

1. **Databricks account** — Free Edition works for the entire tutorial. Sign up at [https://www.databricks.com/learn/free-edition](https://www.databricks.com/learn/free-edition)
2. **Personal Access Token (PAT)** — Generate one from your Databricks workspace: User Settings → Developer → Access Tokens
3. **Databricks CLI** — `pip install databricks-cli` or `brew install databricks/tap/databricks`, then configure with `databricks configure --token`
4. **Python 3.10+** and **uv** — for local development and testing

Store your PAT and workspace URL in a `.env` file (gitignored) — the scaffold creates the template for you.

---

### Where Does the Data Come From?

**The core tension:** **OLTP** (Online Transaction Processing) databases are optimized for small, fast operations — insert a trade, update a record, look up an account. They serve the applications the business runs on in real time. But analysts need answers that require scanning millions of rows, joining large tables, and computing aggregates — these are analytical (**OLAP** — Online Analytical Processing) workloads. Running them directly against the OLTP database would compete for the same CPU, memory, and I/O that traders and operational apps depend on. The medallion architecture solves this by extracting data into a separate OLAP pipeline, so analytical workloads never touch the production systems:

```
  OLTP Sources              Medallion Pipeline (OLAP)
 ┌──────────────┐
 │ Trading App  │──┐
 │ (PostgreSQL) │  │       ┌────────┐    ┌────────┐    ┌────────┐
 ├──────────────┤  ├──-->  │ BRONZE │--->│ SILVER │--->│  GOLD  │
 │ Counterparty │  │       │  (raw) │    │(clean) │    │(metrics│
 │ API          │──┤       └────────┘    └────────┘    └────────┘
 ├──────────────┤  │
 │ Market Data  │──┘
 │ Feed         │
 └──────────────┘
```

### Medallion Architecture — EDW Mapping

If you come from traditional data warehousing, the medallion layers map directly to familiar EDW concepts:

```
  EDW              Medallion        Stage
 STAGING    --->   BRONZE     --->  Stage 3
 ODS / DWH  --->   SILVER     --->  Stage 4
 DATA MARTS --->   GOLD       --->  Stage 5
```

- **Bronze = Staging Area**
  - Raw data landed as-is from source systems
  - No transformations, just append-only ingestion
  - Think of it as your landing zone or raw vault

- **Silver = ODS (Operational Data Store) / DWH (Data Warehouse)**
  - **ODS** — Integrates multiple OLTP sources into a single, near-real-time, subject-oriented store. Lightly transformed but still granular
  - **DWH** — Adds historical depth and conformed dimensions. Traditional EDWs use star/snowflake schemas — these still work in Spark when dimension tables are small enough to broadcast join, but large dimensions that can't be broadcast will trigger expensive shuffles across the cluster. Favor **flat, denormalized tables** at scale and denormalize early in Silver so downstream Gold queries stay shuffle-free. Pair denormalization with a **partition strategy** (e.g., by date, region, or entity type) so Spark can prune irrelevant data at read time instead of scanning entire tables
  - This is where you apply business rules, deduplication, type casting, and referential integrity
  - Your single source of truth — whether you need current-state granularity (ODS) or historical analysis (DWH)

- **Gold = Data Marts / Semantic Layer**
  - Purpose-built aggregations shaped for specific consumers
  - Financial ratios for risk analysts, exposure tiers for compliance, portfolio summaries for traders
  - This is your **semantic layer** — business concepts expressed as reusable, governed metrics with shared definitions
  - Instead of every analyst writing their own "net exposure" calculation, Gold tables encode it once

---

### Tutorial Stages

```
  Stage 1            Stage 2          Stage 3         Stage 4          Stage 5          Stage 6
  SCAFFOLD &   -->   LANDING    -->   BRONZE    -->   SILVER    -->    GOLD      -->    CI/CD
  SETUP              ZONE            (Staging)    (ODS / DWH)     (Data Marts)      (act + GitHub)
```

**Stage 1 — Scaffold & Setup** `/silver-databricks:scaffold-setup`
Project scaffold, synthetic data, tests, CI/CD, Asset Bundles config, Databricks credentials, and connectivity verification.

**Stage 2 — Prepare the Landing Zone** `/silver-databricks:deploy-dev`
Create Unity Catalog schema and volume, upload seed CSVs, and preview what Bronze will do. Sets up the infrastructure the pipeline needs.

**Stage 3 — Bronze (Staging)** `/silver-databricks:run-bronze`
Deploy the Bronze-only pipeline, run it on Databricks, verify raw data landed in Delta tables. Teaches batch vs Auto Loader ingestion and establishes the dev loop.

**Stage 4 — Silver (ODS / DWH)** `/silver-databricks:run-silver`
Cleaned, validated, and enriched — expectations, deduplication, type casting, net positions. Includes dirty data injection to demonstrate expectations, then cleanup. Your single source of truth.

**Stage 5 — Gold (Data Marts)** `/silver-databricks:run-gold`
Business metrics — financial ratios, risk exposure tiers, portfolio summary. Shaped for traders, risk analysts, and compliance. Completes the medallion architecture.

**Stage 6 — CI/CD with `act`** `/silver-databricks:run-cicd`
Local-first CI/CD — run the same GitHub Actions workflows in Docker containers on your machine with `act`. Validate CI (lint + test + bundle), dry-run CD, then deploy to production. Faster feedback loops, fewer broken builds.

---

### Commands

| Order | Command | Description |
|---|---|---|
| Stage 0 | `/silver-databricks:start` | Show this help |
| Stage 1 | `/silver-databricks:scaffold-setup` | Scaffold project + configure Databricks credentials |
| Stage 2 | `/silver-databricks:deploy-dev` | Create landing zone, upload seed data, preview Bronze |
| Stage 3 | `/silver-databricks:run-bronze` | Deploy Bronze pipeline, run it, verify raw tables |
| Stage 4 | `/silver-databricks:run-silver` | Deploy Silver pipeline, validate with dirty data, cleanup |
| Stage 5 | `/silver-databricks:run-gold` | Deploy Gold pipeline, verify business metrics |
| Stage 6 | `/silver-databricks:run-cicd` | Run CI/CD locally with act, deploy to production |
| — | `/silver-databricks:dev-mode` | Edit the tutorial itself — contributions welcome! |

---

### Tech Stack

`Spark Declarative Pipelines` · `Databricks Asset Bundles` · `pytest + chispa` · `ruff` · `GitHub Actions + act` · `Databricks Free Edition`

---

### Contributing

Found a bug? Have an idea? Want to improve a stage?
Open an issue, submit a PR, or share feedback — all contributions are welcome.

---

### Quick Start

1. Run `/silver-databricks:scaffold-setup` to scaffold your project and configure Databricks credentials
2. Run `/silver-databricks:deploy-dev` to create the landing zone and upload seed data
3. Build up each pipeline layer: Bronze → Silver → Gold
4. Run `/silver-databricks:run-cicd` to validate CI/CD locally and deploy to production
