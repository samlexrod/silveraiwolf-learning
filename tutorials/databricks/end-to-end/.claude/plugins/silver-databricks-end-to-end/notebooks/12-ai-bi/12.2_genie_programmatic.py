# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 12 · 12.2 — **The many ways to use Genie** (it's an API, not just a chat box)
# MAGIC
# MAGIC In `12.1` you asked Genie questions in the UI. But Genie is really a **programmatic, SQL-generating
# MAGIC service** over your governed metric view — so you can drive it from a **notebook, a script, an app, or
# MAGIC an agent**. Every answer comes with the **generated SQL** (governed `MEASURE()` over `portfolio_metrics`)
# MAGIC *and* the result rows, so you can show the number, audit the SQL, or reuse it downstream.
# MAGIC
# MAGIC This notebook shows five ways to use it. Run on **serverless**.
# MAGIC
# MAGIC | Way | Surface | When |
# MAGIC |---|---|---|
# MAGIC | Chat | Genie space (UI) — `12.1` | ad-hoc business questions |
# MAGIC | **Notebook / SDK** | `w.genie.*` (this notebook) | embed NL→SQL in a data workflow |
# MAGIC | **REST / CLI** | `databricks genie start-conversation` | scripts, CI, language-agnostic |
# MAGIC | **Reuse the SQL** | run Genie's generated SQL yourself | promote a good answer to a query/tile |
# MAGIC | **Multi-turn** | follow-up messages keep context | drill-downs, refinement |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0 — Setup
# MAGIC The Genie SDK surface needs a recent `databricks-sdk`. Upgrade + restart, then point at YOUR space.
# MAGIC (Find your space id with `w.genie.list_spaces()` if you recreated it — the data asset is `portfolio_metrics`.)

# COMMAND ----------

# MAGIC %pip install -U "databricks-sdk>=0.104.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# Your "Silverline Capital — Portfolio Genie" space (created via CLI in 12.1). If it differs, list + pick:
SPACE_ID = "01f16a39c0fa1592b293e173ace9d5ee"   # ← if needed, set from the list below
for s in w.genie.list_spaces().spaces or []:
    print(s.space_id, "|", s.title)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Ask a question from code → get the generated SQL + answer
# MAGIC `start_conversation_and_wait` sends a question and blocks until Genie finishes. The response carries
# MAGIC **attachments**: a `text` answer and a `query` (the SQL Genie wrote). Notice the SQL uses the **governed
# MAGIC `MEASURE(total_billed)`** — not a guessed `SUM()`.

# COMMAND ----------

msg = w.genie.start_conversation_and_wait(SPACE_ID, "What is the total billed by segment?")
conversation_id = msg.conversation_id

for a in msg.attachments or []:
    if a.text:
        print("ANSWER:\n", a.text.content, "\n")
    if a.query:
        print("GENERATED SQL:\n", a.query.query)
        attachment_id = a.attachment_id

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Get the **data rows** (not just the text) as a DataFrame
# MAGIC The text answer is nice for humans; for a workflow you want the rows. Fetch the attachment's query result
# MAGIC and turn it into a DataFrame you can chart, join, or export.

# COMMAND ----------

import pandas as pd

res = w.genie.get_message_attachment_query_result(SPACE_ID, conversation_id, msg.id, attachment_id)
sr = res.statement_response
cols = [c.name for c in sr.manifest.schema.columns]
pdf = pd.DataFrame(sr.result.data_array or [], columns=cols)
display(pdf)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 — Reuse Genie's SQL directly
# MAGIC Because Genie returns the **exact governed SQL**, you can run it yourself — promote a good answer into a
# MAGIC scheduled query, a dashboard tile, or a downstream table. Same `MEASURE()`, same governed number.

# COMMAND ----------

genie_sql = next(a.query.query for a in msg.attachments if a.query)
display(spark.sql(genie_sql))   # run Genie's own SQL — identical result, now in your pipeline

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 — Multi-turn: follow-ups keep context
# MAGIC `create_message_and_wait` continues the SAME conversation — Genie remembers what "segment" meant and
# MAGIC refines. Great for drill-downs ("now just the top 3", "filter to loans", "as a percentage").

# COMMAND ----------

follow = w.genie.create_message_and_wait(SPACE_ID, conversation_id, "Now show only the top 3 by overdue amount")
for a in follow.attachments or []:
    if a.text:  print("ANSWER:\n", a.text.content, "\n")
    if a.query: print("GENERATED SQL:\n", a.query.query)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 — The same thing from the CLI / REST (language-agnostic)
# MAGIC No Python needed — the Conversation API is reachable from the `databricks` CLI (and plain REST), so
# MAGIC scripts, CI jobs, or any language can ask Genie and parse the generated SQL + answer:
# MAGIC ```bash
# MAGIC databricks genie start-conversation <SPACE_ID> "Which region has the highest overdue ratio?" -o json
# MAGIC # → response.attachments[].query.query  (the SQL)   +   .text.content  (the answer)
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 — Genie vs `ai_query()` — don't confuse them
# MAGIC A common question: *"can I just call Genie with `ai_query()`?"* **No** — they're different planes, and
# MAGIC mixing them up leads to wrong numbers:
# MAGIC
# MAGIC | | **Genie** (this notebook) | **`ai_query()`** |
# MAGIC |---|---|---|
# MAGIC | What it is | governed **NL → SQL** over your metric view | **LLM/ML inference** in SQL (a Model Serving endpoint) |
# MAGIC | Output | exact `MEASURE()` SQL + real rows | generated text / labels / embeddings (can hallucinate) |
# MAGIC | "Total billed by segment?" | ✅ correct, governed | ❌ an LLM *guessing* — wrong tool |
# MAGIC | Best for | business Q&A on governed data | enrich **unstructured** data: summarize, classify, sentiment |
# MAGIC | Called via | Conversation API / `w.genie.*` | `ai_query('<endpoint>', prompt)` |
# MAGIC
# MAGIC `ai_query()` targets a **Model Serving endpoint** (`SHOW` them with the serving UI / `w.serving_endpoints.list()`),
# MAGIC not Genie — there is no Genie serving endpoint. Use Genie for *governed metrics*; use `ai_query()` for
# MAGIC *generative work on text*. They're complementary: below, `ai_query()` reads a **credit memo** (the
# MAGIC unstructured docs from the `seed` stage — something Genie/SQL can't compute) and summarizes + risk-rates it.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ai_query() over an UNSTRUCTURED credit memo — the job Genie is NOT for.
# MAGIC WITH memo AS (
# MAGIC   SELECT concat_ws('\n', collect_list(value)) AS text
# MAGIC   FROM read_files('/Volumes/silverline/bronze/files/memos/credit_memo_1.md', format => 'text')
# MAGIC )
# MAGIC SELECT ai_query(
# MAGIC   'databricks-meta-llama-3-3-70b-instruct',
# MAGIC   'You are a credit analyst. In 2 sentences summarize this credit memo, then on a new line output RISK: LOW|MEDIUM|HIGH.\n\n' || text
# MAGIC ) AS ai_assessment
# MAGIC FROM memo;

# COMMAND ----------

# MAGIC %md
# MAGIC > 🧠 **Rule of thumb:** numbers from your governed model → **Genie** (or plain SQL over the metric view);
# MAGIC > language *about* your data (summaries, classification, extraction) → **`ai_query()`** / AI Functions.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7 — Package the AI as a reusable **UC SQL function** (and why Genie can't be one)
# MAGIC `ai_query()` is an expression, so you can wrap it in a **Unity Catalog SQL function** — governed, named,
# MAGIC reusable, permissionable. Now *any* analyst calls `assess_credit_memo(text)` from plain SQL without knowing
# MAGIC the endpoint or the prompt:

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION silverline.gold.assess_credit_memo(memo STRING)
# MAGIC RETURNS STRING
# MAGIC COMMENT 'LLM risk-assessment of a credit memo via ai_query — a governed, SQL-callable UC function.'
# MAGIC RETURN ai_query(
# MAGIC   'databricks-meta-llama-3-3-70b-instruct',
# MAGIC   'You are a credit analyst. In 2 sentences summarize this credit memo, then on a new line output RISK: LOW|MEDIUM|HIGH.\n\n' || memo
# MAGIC );

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Reuse it across EVERY memo in one query — AI enrichment as a governed SQL function:
# MAGIC WITH memos AS (
# MAGIC   SELECT _metadata.file_path AS path, concat_ws('\n', collect_list(value)) AS text
# MAGIC   FROM read_files('/Volumes/silverline/bronze/files/memos/', format => 'text')
# MAGIC   GROUP BY _metadata.file_path
# MAGIC )
# MAGIC SELECT element_at(split(path, '/'), -1) AS memo,
# MAGIC        silverline.gold.assess_credit_memo(text) AS assessment
# MAGIC FROM memos ORDER BY memo LIMIT 3;

# COMMAND ----------

# MAGIC %md
# MAGIC ### …but you can't wrap **Genie** in a SQL-callable UC function
# MAGIC A natural next thought: "wrap Genie the same way." You can't — verified live on Free Edition:
# MAGIC
# MAGIC | Path | Result here |
# MAGIC |---|---|
# MAGIC | UC **SQL** function | no HTTP/procedural calls — can't reach the Genie API at all |
# MAGIC | UC **Python** UDF | network **sandboxed** → `urlopen` gave `[Errno 101] Network is unreachable` |
# MAGIC | **`http_request()`** SQL fn | **not available** here (`function cannot be resolved`); only system-managed agent HTTP connections exist |
# MAGIC
# MAGIC And even where UDF egress / `http_request` *are* enabled (serverless/standard-access compute generally
# MAGIC allows UDF traffic on 443), Genie is a **stateful, async** Conversation API — `start-conversation` → poll
# MAGIC `get-message` until `COMPLETED` → fetch the attachment result. That's 3+ round-trips, not one synchronous
# MAGIC `SELECT`. So the idiomatic "Genie in a function" is an **agent tool** (`databricks_langchain.genie` in the
# MAGIC Mosaic AI Agent Framework), consumed by an agent — exactly the `ai_query → agent → Genie` bridge above.
# MAGIC `ai_query()` wraps cleanly into SQL because it's a single synchronous inference; Genie doesn't.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Recap — Genie is governed NL→SQL you can use anywhere
# MAGIC - **One space, many surfaces:** chat (UI), notebook/SDK (`w.genie.*`), CLI/REST, embedded in apps/agents.
# MAGIC - **Every answer = SQL + rows + text** — show the number, audit the SQL, or reuse it downstream.
# MAGIC - **Always governed:** because the space is scoped to `silverline.gold.portfolio_metrics`, every generated
# MAGIC   query uses `MEASURE()` — so a notebook, the CLI, the dashboard, and a chat answer all agree.
# MAGIC - **Multi-turn** keeps context for natural drill-downs.
# MAGIC - **Genie ≠ `ai_query()`:** `ai_query()` (and UC SQL functions wrapping it, like `assess_credit_memo`) =
# MAGIC   generative AI on *text*, callable from any `SELECT`; **Genie** = governed NL→SQL via the Conversation
# MAGIC   API / agent tools — not a SQL-callable function.
# MAGIC
# MAGIC 🎉 That closes the tutorial: a governed lakehouse where **humans (Genie/dashboards) and code (SDK/CLI/UC
# MAGIC functions) consume the *same* governed metrics** — and AI enriches the unstructured side.
