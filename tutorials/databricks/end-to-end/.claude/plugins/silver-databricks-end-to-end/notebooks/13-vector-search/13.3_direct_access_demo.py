# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 13 · 13.3 — (Optional) Direct Vector Access, the *other* index type
# MAGIC
# MAGIC `13.1` built a **delta-sync** index: bound to a Delta table, and it embedded every chunk for you. This
# MAGIC optional notebook shows the **other** kind — a **Direct Vector Access** index — *live*, so the contrast is
# MAGIC real, not hand-waved. Here **you** own everything: no source table, you compute the embeddings yourself and
# MAGIC **upsert the raw vectors** through the API.
# MAGIC
# MAGIC > ⚠️ Free Edition allows a single Vector Search endpoint, so this demo attaches its `DIRECT_ACCESS` index to
# MAGIC > the same `silverline-vs`. The **first index attached takes ~10–20 min to provision** (a property of the
# MAGIC > endpoint, not of delta-sync). This notebook **deletes its own index at the end**, so it leaves nothing behind.
# MAGIC >
# MAGIC > ✅ Verified live on Free Edition ($0): the query below ranked the wheel-loader doc top (score ~0.81) for
# MAGIC > an "earth-moving machinery" query, then tore down clean.

# COMMAND ----------

# MAGIC %pip install -U "databricks-sdk>=0.104.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Embed a few docs yourself
# MAGIC With Direct Vector Access there's no managed embedding — *you* call the model. We send three short docs to
# MAGIC the Free-Edition `databricks-bge-large-en` endpoint and get back one 1024-dim vector each.

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
ENDPOINT = "silverline-vs"
INDEX    = "silverline.silver.dva_demo_idx"
EMB      = "databricks-bge-large-en"

docs = [
    ("d1", "Wheel loader financing agreement for heavy earth-moving equipment."),
    ("d2", "Forklift lease for warehouse material handling."),
    ("d3", "Credit memo: customer near concentration limit, AA rating."),
]

def embed(texts):
    """Call the embedding endpoint and return one vector per input text."""
    return [d.embedding for d in w.serving_endpoints.query(name=EMB, input=texts).data]

vectors = embed([text for _, text in docs])
print(f"embedded {len(vectors)} docs · dim = {len(vectors[0])}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Create the `DIRECT_ACCESS` index
# MAGIC No `source_table`: instead we declare the **vector column** (name + dimension) and a **schema** for the rows
# MAGIC we'll write. Idempotent — drop any prior demo index of the same name first.

# COMMAND ----------

import json
from databricks.sdk.service.vectorsearch import (
    DirectAccessVectorIndexSpec, EmbeddingVectorColumn, VectorIndexType)

try:
    w.vector_search_indexes.delete_index(index_name=INDEX)
    print("deleted existing demo index")
except Exception:
    pass

w.vector_search_indexes.create_index(
    name=INDEX,
    endpoint_name=ENDPOINT,
    primary_key="id",
    index_type=VectorIndexType.DIRECT_ACCESS,
    direct_access_index_spec=DirectAccessVectorIndexSpec(
        embedding_vector_columns=[EmbeddingVectorColumn(name="embedding", embedding_dimension=1024)],
        schema_json=json.dumps({"id": "string", "text": "string", "embedding": "array<float>"}),
    ),
)
print("DIRECT_ACCESS index created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Wait for the endpoint to provision (~10–20 min on first attach)
# MAGIC Same lazy provisioning as `13.1` — you can't upsert until the index reports `ready`. Poll until it flips.

# COMMAND ----------

import time

for i in range(120):                                 # up to ~30 min
    s = w.vector_search_indexes.get_index(index_name=INDEX).status
    if s.ready:
        print(f"[{i}] ready"); break
    print(f"[{i}] {s.message}")
    time.sleep(15)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Upsert YOUR vectors
# MAGIC This is the crux of the contrast: with delta-sync the table drove the index; here you hand it fully-formed
# MAGIC rows, each carrying the embedding **you** computed in Step 1.

# COMMAND ----------

rows = [{"id": did, "text": text, "embedding": vec}
        for (did, text), vec in zip(docs, vectors)]
w.vector_search_indexes.upsert_data_vector_index(index_name=INDEX, inputs_json=json.dumps(rows))
print(f"upserted {len(rows)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 — Query by vector
# MAGIC No managed embedding means no `query_text` either — you embed the question yourself and pass a
# MAGIC `query_vector`. Nearest neighbors come back ranked by score.

# COMMAND ----------

query_vec = embed(["agreements that finance earth-moving machinery"])[0]
res = w.vector_search_indexes.query_index(
    index_name=INDEX, columns=["id", "text"], query_vector=query_vec, num_results=3)
for row in (res.result.data_array or []):
    print(row)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6 — Tear down
# MAGIC The demo has made its point — delete the index so it doesn't hold your one endpoint.

# COMMAND ----------

w.vector_search_indexes.delete_index(index_name=INDEX)
print("demo index deleted — endpoint free")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Recap — delta-sync vs direct access
# MAGIC | | **Delta Sync** (`13.1`) | **Direct Vector Access** (this notebook) |
# MAGIC |---|---|---|
# MAGIC | Source of truth | a **Delta table** (`doc_chunks`) | **none** — you own the rows |
# MAGIC | Embeddings | **managed** — the index embeds `content` for you | **you** compute + upsert the vectors |
# MAGIC | Staying current | **automatic** via Change Data Feed | **you** re-upsert on every change |
# MAGIC | Query input | `query_text` (it embeds the query too) | `query_vector` (you embed the query) |
# MAGIC | Best for | a table-backed corpus (our contracts/memos) | vectors from your own pipeline |
# MAGIC
# MAGIC **Verified live output** (query = *"agreements that finance earth-moving machinery"*):
# MAGIC ```
# MAGIC ['d1', 'Wheel loader financing agreement for heavy earth-moving equipment.', 0.808]  ← top
# MAGIC ['d2', 'Forklift lease for warehouse material handling.',                    0.591]
# MAGIC ['d3', 'Credit memo: customer near concentration limit, AA rating.',         0.506]
# MAGIC ```
# MAGIC The wheel-loader doc ranks top for an "earth-moving" query it shares no keywords with — semantic match,
# MAGIC exactly like `13.1`, just with you holding the embedding + upsert yourself. For our table-backed corpus,
# MAGIC delta-sync is the right default; direct access is the tool when the vectors are yours to manage.
