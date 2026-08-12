# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 15 · 15.1 — Feature engineering (the **offline** feature store)
# MAGIC
# MAGIC You've built the lakehouse (medallion), served it through analytics + Genie, and stood up two retrievers
# MAGIC over the contract docs. Now the ML phase: **predict which contracts will go bad** so collections can act
# MAGIC early. This stage is the **data-prep** step of that — turn the governed gold/silver into a **feature
# MAGIC store**, the shared, reusable inputs a model trains on. Stage 16 trains + scores; here we prepare.
# MAGIC
# MAGIC **What a feature store buys you:** one **governed, versioned** definition of each feature, computed once and
# MAGIC reused for **training and inference** — so the numbers a model learns from are the *same* numbers it scores
# MAGIC against later (no train/serve skew). On Databricks, a feature table is just a **Unity Catalog Delta table
# MAGIC with a primary key** — governed and lineage-tracked like everything else you've built.
# MAGIC
# MAGIC > 🗄️ **Preconditions:** the `medallion` gold/silver exist — `silverline.silver.silver_contracts`,
# MAGIC > `silverline.silver.silver_customers`, `silverline.gold.gold_contract_aging`. (All built in Stages 7–10.)

# COMMAND ----------

# MAGIC %pip install databricks-feature-engineering -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## CRISP-DM — the ML lifecycle we follow
# MAGIC **This notebook is the first three phases** — Business Understanding → Data Understanding → Data
# MAGIC Preparation; Stage 16 continues (Modeling → Evaluation → Deployment). It's **iterative** — findings loop
# MAGIC back around the cycle. CRISP-DM is the *frame*, not a Databricks feature.
# MAGIC
# MAGIC ![CRISP-DM lifecycle](./crispdm.png)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Business & Data Understanding (CRISP-DM phases 1–2)
# MAGIC **Business question:** *which booked contracts are at risk of going delinquent or being charged off?* If we
# MAGIC can flag them early, collections prioritizes the right accounts and the portfolio loses less money.
# MAGIC
# MAGIC **The target lives in the data already.** A contract's `status` is one of `active` / `paid_off` /
# MAGIC `delinquent` / `charged_off`. We frame a **binary label**: **at-risk** (`delinquent` or `charged_off`) vs.
# MAGIC **healthy** (`active` or `paid_off`). First, *understand* the data — how is `status` distributed?

# COMMAND ----------

# MAGIC %md
# MAGIC ### What this first table tells you
# MAGIC Run the next cell to count contracts by `status` and show each status as a percentage of the portfolio.
# MAGIC This is the first thing to check before training a classifier because it reveals the **class balance**:
# MAGIC whether the outcomes you want the model to tell apart appear in roughly equal amounts.
# MAGIC
# MAGIC For this tutorial, expect the healthy statuses (`active`, `paid_off`) to outnumber the at-risk statuses
# MAGIC (`delinquent`, `charged_off`). That means the model will see fewer examples of the case we care about most,
# MAGIC so Stage 16 will use stratified evaluation and metrics that do not hide that imbalance.

# COMMAND ----------

# Data Understanding — count each status before collapsing it into the binary target.
display(spark.sql("""
    SELECT status,
           count(*)                                              AS contracts,
           round(100.0 * count(*) / sum(count(*)) OVER (), 1)    AS pct
    FROM silverline.silver.silver_contracts
    GROUP BY status
    ORDER BY contracts DESC
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Reading this table — and what "class balance" means
# MAGIC A classifier learns to tell **classes** apart — here, **at-risk** vs **healthy** contracts. **Class
# MAGIC balance** is just *how many examples fall in each class*. A **balanced** problem has roughly equal counts;
# MAGIC ours is **imbalanced** — the statuses that make a contract at-risk (`delinquent` + `charged_off`) are a
# MAGIC small slice, while `active` / `paid_off` dominate.
# MAGIC
# MAGIC **What you should take away from the counts above:**
# MAGIC - The class we actually care about — **at-risk** — is the **minority** (most contracts are healthy).
# MAGIC - That's realistic, but it **changes how we train and evaluate** (all in Stage 16):
# MAGIC   - **Accuracy lies here.** "Predict everyone healthy" scores ~85% accuracy yet catches **zero** bad
# MAGIC     contracts — useless. So we judge the model with **ROC-AUC / PR-AUC**, not accuracy.
# MAGIC   - We **weight the rare class up** during training (`class_weight="balanced"`) so it isn't ignored.
# MAGIC   - We **split by class** (*stratified*) so small train/test sets keep the same balance.
# MAGIC
# MAGIC Next we collapse the four statuses into the **binary label** the model predicts — the balance, made explicit.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Collapse status into the model's target label
# MAGIC The model does not predict four separate contract statuses. It predicts one operational question:
# MAGIC **is this contract at risk?**
# MAGIC
# MAGIC This cell turns the raw `status` values into a binary target:
# MAGIC - `1` = **at-risk** (`delinquent` or `charged_off`)
# MAGIC - `0` = **healthy** (`active` or `paid_off`)
# MAGIC
# MAGIC Then it counts each label so you can see the exact two-class balance the model will train on. This is the
# MAGIC target column Stage 16 uses as `at_risk`.
# MAGIC
# MAGIC At real portfolio scale, this is also where you decide whether to **rebalance** the training data. If you
# MAGIC have thousands or millions of healthy examples (`0`) and far fewer at-risk examples (`1`), one simple
# MAGIC approach is to **downsample the majority class** — keep all or most of the `1` rows, but train on only a
# MAGIC representative slice of the `0` rows. That gives the model a clearer view of both outcomes. Here we keep
# MAGIC all 85 rows because the dataset is intentionally tiny; Stage 16 handles the imbalance with stratified
# MAGIC evaluation and class weights instead.

# COMMAND ----------

# Collapse four business statuses into the binary target column the classifier will learn.
display(spark.sql("""
    SELECT CASE WHEN status IN ('delinquent','charged_off') THEN 1 ELSE 0 END AS at_risk,
           count(*) AS contracts
    FROM silverline.silver.silver_contracts
    GROUP BY 1 ORDER BY at_risk
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC > ⚠️ **Small + imbalanced, on purpose.** The seeded portfolio is **85 contracts** with a **minority
# MAGIC > at-risk class** (~1 in 6). That's too little to train a *production-grade* risk model — and that's fine.
# MAGIC > The goal here is to learn the **Databricks ML mechanics end-to-end** (feature store → train → register →
# MAGIC > batch + online serving → an agent that uses it), with the lineage and governance that scale unchanged to
# MAGIC > millions of rows. We'll evaluate honestly (Stage 16) with that caveat, not chase a headline accuracy.
# MAGIC
# MAGIC **What signal might predict risk?** Three families, all already in your gold/silver:
# MAGIC - **Customer** — `segment`, `region`, `credit_rating`, `annual_revenue` (who we financed)
# MAGIC - **Contract** — `contract_type`, `principal`, `apr`, `term_months` (the deal terms)
# MAGIC - **Billing / AR behavior** — `overdue_amount`, `open_amount`, `paid_amount`, `total_billed` from
# MAGIC   `gold_contract_aging` (are they *already* falling behind?)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Why ML teams use feature stores
# MAGIC Without a feature store, ML engineers and data scientists usually rebuild the same feature logic in many
# MAGIC places: one SQL query for exploration, another notebook for training, another job for batch scoring, and
# MAGIC sometimes another service path for real-time scoring. That creates real production hurdles:
# MAGIC
# MAGIC - **Duplicated feature logic** — every model team rewrites joins and calculations, so definitions drift.
# MAGIC - **Train/serve skew** — the model trains on one version of `overdue_amount` but scores on a slightly
# MAGIC   different version later.
# MAGIC - **Slow experimentation** — data scientists spend time rebuilding joins instead of testing hypotheses.
# MAGIC - **Hard debugging** — when a score looks wrong, nobody knows exactly which feature definition produced it.
# MAGIC - **Weak governance** — features may not have clear ownership, lineage, access control, or reuse history.
# MAGIC - **Leakage risk** — a training query can accidentally include data that would not have existed at scoring
# MAGIC   time, making offline metrics look better than reality.
# MAGIC
# MAGIC A feature store gives the team a **contract**: each feature has one governed definition, one primary key, and
# MAGIC one lookup path that can be reused for training and scoring. Data scientists still own model design and
# MAGIC preprocessing; ML engineers get repeatable, production-ready inputs.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Data Prep (CRISP-DM phase 3): engineer the feature table
# MAGIC Assemble those three families into **one row per contract**, keyed by `contract_id`, then register it as a
# MAGIC **feature table** with the `FeatureEngineeringClient`. Under the hood that's a UC **Delta** table with a
# MAGIC **primary key** — governed, lineage-tracked, and reusable by any model or team.

# COMMAND ----------

from databricks.feature_engineering import FeatureEngineeringClient

fe = FeatureEngineeringClient()
spark.sql("CREATE SCHEMA IF NOT EXISTS silverline.ml")

FEATURE_TABLE = "silverline.ml.contract_features"

# Join the three feature families into one contract-grain frame. CAST decimals -> double so downstream
# ML libraries get plain floats; COALESCE the AR columns (a brand-new contract has no aging rows yet).
features = spark.sql("""
    SELECT c.contract_id,
           c.contract_type,
           CAST(c.principal       AS DOUBLE) AS principal,
           CAST(c.apr             AS DOUBLE) AS apr,
           c.term_months,
           cu.segment, cu.region, cu.credit_rating,
           CAST(cu.annual_revenue AS DOUBLE) AS annual_revenue,
           CAST(COALESCE(a.overdue_amount, 0) AS DOUBLE) AS overdue_amount,
           CAST(COALESCE(a.open_amount,    0) AS DOUBLE) AS open_amount,
           CAST(COALESCE(a.paid_amount,    0) AS DOUBLE) AS paid_amount,
           CAST(COALESCE(a.total_billed,   0) AS DOUBLE) AS total_billed
    FROM silverline.silver.silver_contracts c
    JOIN silverline.silver.silver_customers cu USING (customer_id)
    LEFT JOIN silverline.gold.gold_contract_aging a USING (contract_id)
""")

# Idempotent: drop + recreate so re-runs are safe (a feature table IS its UC Delta table).
spark.sql(f"DROP TABLE IF EXISTS {FEATURE_TABLE}")
fe.create_table(
    name=FEATURE_TABLE,
    primary_keys=["contract_id"],
    df=features,
    description="Contract credit-risk features (customer + contract terms + AR aging), keyed by contract_id",
)
print(f"created feature table {FEATURE_TABLE}  ·  {spark.table(FEATURE_TABLE).count()} rows, "
      f"{len(spark.table(FEATURE_TABLE).columns)} columns")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Look at what you stored
# MAGIC One governed row per contract. In **Catalog Explorer** (`silverline` → `ml` → `contract_features`) you'll
# MAGIC see it flagged as a **feature table** with `contract_id` as the primary key, and **lineage** back to the
# MAGIC silver/gold tables it was built from — the same governance you saw across the medallion, now for ML inputs.
# MAGIC
# MAGIC Notice that categorical values such as `contract_type`, `segment`, `region`, and `credit_rating` are stored
# MAGIC as their **business-readable labels**, not one-hot encoded columns. That's intentional:
# MAGIC - The feature store is the shared, governed source of feature definitions. It should stay useful across
# MAGIC   models, BI, agents, and debugging.
# MAGIC - One-hot encoding is a **model-specific transformation**. Different models may need different encodings
# MAGIC   or no encoding at all.
# MAGIC - Stage 16 applies one-hot encoding inside the sklearn `Pipeline`, then logs that pipeline with MLflow, so
# MAGIC   the exact same transformation runs during training and batch scoring.
# MAGIC
# MAGIC This is called **preprocessing**: the step between raw features and the model where you convert data into
# MAGIC the numeric shape the algorithm expects. Common preprocessing includes one-hot encoding categories, scaling
# MAGIC numeric columns, filling missing values, or clipping outliers. In Stage 16 you'll see that explicitly:
# MAGIC
# MAGIC `raw feature table → preprocessing pipeline → trained model`
# MAGIC
# MAGIC So the store keeps stable, explainable features; the model package owns the preprocessing needed by that
# MAGIC model.
# MAGIC
# MAGIC This table is also intentionally **wide**. A **long** table usually stores repeated observations as rows,
# MAGIC often with a shape like `entity_id`, `attribute`, `value`, `timestamp` — useful for logs, events, ledger
# MAGIC entries, and time series. A **wide** table stores one entity per row and many attributes as columns —
# MAGIC exactly what most ML training APIs expect.
# MAGIC
# MAGIC Feature stores are wide by nature because a model needs a complete feature vector for each entity it scores.
# MAGIC Here, each row is one `contract_id`, and each feature column describes that contract: deal terms, customer
# MAGIC attributes, and billing behavior. When Stage 16 trains or scores, Databricks can look up one key and hand the
# MAGIC model one complete row of inputs.

# COMMAND ----------

display(spark.table(FEATURE_TABLE).orderBy("contract_id").limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — The payoff: a **feature-lookup training set**
# MAGIC A feature store isn't just a table — it's the **join-by-key contract** between labels and features. You
# MAGIC hand it a thin frame of **`contract_id` + label**, declare a **`FeatureLookup`**, and it assembles the
# MAGIC training rows for you. That exact declaration is what Stage 16 packages *into the model* (`fe.log_model`)
# MAGIC so inference looks features up the **same** way — the anti-skew guarantee, made concrete.
# MAGIC
# MAGIC **Anti-skew guarantee** means the model is trained and scored with the **same feature definitions and lookup
# MAGIC logic**. Without it, training might use one join or calculation while production scoring uses another,
# MAGIC creating **train/serve skew**: the model sees different inputs in production than the inputs it learned from.
# MAGIC Feature lookups prevent that by making the key, source table, and selected features part of the training set
# MAGIC and the logged model package.

# COMMAND ----------

from databricks.feature_engineering import FeatureLookup

# The labels: just the key + the target. NO features here — the store supplies those by lookup.
labels = spark.sql("""
    SELECT contract_id,
           CASE WHEN status IN ('delinquent','charged_off') THEN 1 ELSE 0 END AS at_risk
    FROM silverline.silver.silver_contracts
""")

# Declare the lookup: join contract_features on contract_id. Exclude the key from the model's inputs.
training_set = fe.create_training_set(
    df=labels,
    feature_lookups=[FeatureLookup(table_name=FEATURE_TABLE, lookup_key="contract_id")],
    label="at_risk",
    exclude_columns=["contract_id"],
)

train_df = training_set.load_df()
print(f"training set assembled by lookup: {train_df.count()} rows × {len(train_df.columns)} columns")
print("columns:", train_df.columns)
display(train_df.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 — One feature store, **two** serving modes (the frame for Stage 16)
# MAGIC The table you just built is the **offline** store — high-throughput Delta, read by Spark for **training and
# MAGIC batch inference**. But a model also has to score **fresh** data at decision time, fast. Same features, two
# MAGIC access paths — and you'll build **both** next stage:
# MAGIC
# MAGIC | | **Offline / batch** (this table) | **Online / real-time** (Stage 16) |
# MAGIC |---|---|---|
# MAGIC | Store | UC **Delta** feature table | **Lakebase Postgres** synced table |
# MAGIC | Read by | Spark — `fe.score_batch` | app / agent — a per-key lookup |
# MAGIC | Latency | minutes, high-throughput | milliseconds, one contract |
# MAGIC | Use | **train** the model · score the whole book nightly | score **one** contract on request |
# MAGIC
# MAGIC **Why both:** train offline for consistency + scale; serve online for freshness + speed — from the *same*
# MAGIC governed definitions, so training and serving never drift apart. Stage 16 trains on this table, batch-scores
# MAGIC the portfolio into a gold table, **and** publishes these features to Lakebase for the Stage-17 agent to look
# MAGIC up live.
# MAGIC
# MAGIC > 🧹 **Cost & cleanup:** quota only — this created one small Delta feature table in `silverline.ml`. The
# MAGIC > tutorial's `cleanup` drops it. Nothing here spends money.
