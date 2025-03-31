# Databricks notebook source
# MAGIC %md
# MAGIC ## 1. Introduction
# MAGIC ---
# MAGIC     
# MAGIC In this tutorial, we explore and compare two optimization strategies in Databricks: Partitioning with Z-Ordering and Liquid Clustering. These techniques help optimize data skipping and read performance for large Delta Lake tables.
# MAGIC
# MAGIC **Explanation**
# MAGIC - Partitioning splits data into directories based on column values.
# MAGIC - Z-Ordering reorders data within files to colocate related information.
# MAGIC - Liquid Clustering introduces automatic optimization without strict partition boundaries.

# COMMAND ----------

# DBTITLE 1,- Imports & Session
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.functions import expr
from pprint import pprint
import json 

# spark comes instatiated out of the box in databricks. However, if you're running locally, you'll need to instantiate it.
# We will instantiate to showcase how to instantiate it.
spark = SparkSession.builder.appName("DeltaOptimization").getOrCreate()


# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Dataset Preparation
# MAGIC ---
# MAGIC We'll create a synthetic dataset that simulates a typical claims dataset, saved as a Delta table.
# MAGIC
# MAGIC **Explanation**
# MAGIC - The dataset includes `claim_id`, `member_id`, `claim_date`, `claim_amount`, and `state`.
# MAGIC - We'll use this dataset to demonstrate both optimization approaches.

# COMMAND ----------

# DBTITLE 1,- Dataset Mockup
df = spark.range(0, 100)
claims_df = df.withColumn("claim_id", expr("id")) \
              .withColumn("member_id", expr("id % 100000")) \
              .withColumn("claim_date", expr("date_add('2020-01-01', cast(id % 10 as int))")) \
              .withColumn("state", expr("CASE WHEN id % 5 = 0 THEN 'CA' WHEN id % 5 = 1 THEN 'TX' WHEN id % 5 = 2 THEN 'NY' WHEN id % 5 = 3 THEN 'FL' ELSE 'WA' END")) \
              .withColumn("claim_amount", expr("round(rand() * 1000, 2)"))
claims_df.display()

# COMMAND ----------

#TODO: Add ingestion time clustering here

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Traditional Partitioning + Z-Ordering
# MAGIC ---
# MAGIC We write the data into a Delta table using `state` as the partition column and then apply Z-Ordering on `claim_date`.
# MAGIC
# MAGIC **Explanation**
# MAGIC - Partitioning creates directory structures like `/state=CA/`.
# MAGIC - Z-Ordering within each partition sorts data to improve skipping on `claim_date`.
# MAGIC - Z-Ordering physically colocates similar `claim_date` values into the same files, so when queries filter by date, Spark can skip unrelated files more effectively.
# MAGIC - The Spark optimizer uses **min/max statistics per file** to determine if a file can be skipped for a query predicate.
# MAGIC
# MAGIC **File Structure Example**:
# MAGIC ```
# MAGIC /tmp/delta/claims_partitioned/
# MAGIC ├── state=CA/
# MAGIC │   ├── part-0000.snappy.parquet
# MAGIC │   └── ...
# MAGIC ├── state=TX/
# MAGIC │   ├── part-0000.snappy.parquet
# MAGIC ...
# MAGIC ```

# COMMAND ----------

# DBTITLE 1,- Removing old data
# Removing the old data for new tutorial runs
%rm -rf /dbfs/tmp/delta/claims_partitioned

# COMMAND ----------

# DBTITLE 1,- Creating Partitioned Data
claims_df.write.format("delta") \
    .partitionBy("state") \
    .mode("overwrite") \
    .save("/tmp/delta/claims_partitioned")

# COMMAND ----------

# DBTITLE 1,- Observing Partitions
# Partition structure
%ls /dbfs/tmp/delta/claims_partitioned

# COMMAND ----------

# DBTITLE 1,- Observing Partitioned Files
# File structure
%ls /dbfs/tmp/delta/claims_partitioned/state=CA

# COMMAND ----------

# DBTITLE 1,- Inspecting First Delta Log
# Inspecting the first delta log
with open("/dbfs/tmp/delta/claims_partitioned/_delta_log/00000000000000000000.json", "r") as f:
    for line in f:
        pprint(json.loads(line))

# COMMAND ----------

# DBTITLE 1,- Inspecting Partitioned Data
# File observation prior to optimizing
spark.read.format("delta").load(
    "dbfs:/tmp/delta/claims_partitioned/state=CA"
).withColumn("file_name", F.element_at(F.split(F.input_file_name(), "/"), -1)).display()

# COMMAND ----------

# DBTITLE 1,- Optimizing Partitions
# Optimizing the parquet files
results = spark.sql("OPTIMIZE delta.`/tmp/delta/claims_partitioned` ZORDER BY (claim_date)")

# Inspecting the first delta log
with open("/dbfs/tmp/delta/claims_partitioned/_delta_log/00000000000000000001.json", "r") as f:
    for line in f:
        pprint(json.loads(line))

# COMMAND ----------

# DBTITLE 1,- Observing New Partitioned Files
# File structure
%ls /dbfs/tmp/delta/claims_partitioned/state=CA

# COMMAND ----------

# DBTITLE 1,- Inspecting New Partitioned Data
# File inspection after to optimizing
spark.read.format("delta").load(
    "dbfs:/tmp/delta/claims_partitioned/state=CA"
).withColumn("file_name", F.element_at(F.split(F.input_file_name(), "/"), -1)).display()

# COMMAND ----------

# MAGIC %md
# MAGIC **Why Z-Ordering ordered files by `claim_date`**
# MAGIC - Z-Ordering sorts the data within each partition by the specified columns—in this case, `claim_date`.
# MAGIC - This ensures that data with similar `claim_date` values ends up together in fewer files.
# MAGIC
# MAGIC **Benefit of Ordering**
# MAGIC - When a query filters on `claim_date`, Spark reads only the small subset of files that contain the relevant dates.
# MAGIC - Spark uses **file-level statistics (min/max values)** for `claim_date` to skip files that are outside the filter range. You can see these statistics in the `*.json` files of the `_delta_log`.
# MAGIC - Example:
# MAGIC     - id: 0 → `claim_date`: 2020-01-01 → file: `part-00000`
# MAGIC     - id: 5 → `claim_date`: 2020-01-06 → same file: `part-00000`
# MAGIC - Thus, file `part-00000` holds a range of sorted dates, enabling **data skipping** and faster reads.
# MAGIC
# MAGIC The `OPTIMIZE` command with Z-Ordering coalesces small files (e.g., many part files) into larger, fewer files and reorders the data by the Z-Order columns.
# MAGIC
# MAGIC **So why files are combined?**
# MAGIC - Spark and Delta Lake aim to reduce the small file problem, which can hurt performance due to high metadata and shuffle overhead.
# MAGIC - When `OPTIMIZE` runs, it rewrites many small files into fewer, larger files (typically 1 GB) and physically sorts the rows within those files using a space-filling curve (like Z-order).
# MAGIC - If two small files both contain rows for similar `claim_date` values, they are merged into one and sorted.
# MAGIC
# MAGIC **Benefits of combining**
# MAGIC - Improves query performance through better data skipping.
# MAGIC - Reduces file system overhead and metadata load.
# MAGIC - Enhances parallel read performance by creating more evenly sized files.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Liquid Clustering
# MAGIC ---
# MAGIC Next, we load the same dataset into a non-partitioned Delta table and enable Liquid Clustering with clustering on `state` and `claim_date`.
# MAGIC
# MAGIC **Explanation**
# MAGIC - Liquid clustering avoids rigid directories by clustering within files.
# MAGIC - More flexible for high-cardinality or skewed columns.
# MAGIC
# MAGIC **File Structure Example**:
# MAGIC ```
# MAGIC /tmp/delta/claims_liquid/
# MAGIC ├── part-0000.snappy.parquet
# MAGIC ├── part-0001.snappy.parquet
# MAGIC ...
# MAGIC ```

# COMMAND ----------

# DBTITLE 1,- Removing old data
# Removing the old data for new tutorial runs
%rm -rf /dbfs/tmp/delta/claims_liquid/

# COMMAND ----------

# DBTITLE 1,- Creating Liquid Clustering
claims_df.write.format("delta") \
    .mode("overwrite") \
    .save("/tmp/delta/claims_liquid")

spark.sql("ALTER TABLE delta.`/tmp/delta/claims_liquid` CLUSTER BY (state, claim_date)")

# COMMAND ----------

# DBTITLE 1,- Observing  Parquet Files
# No partitioned structure
%ls /dbfs/tmp/delta/claims_liquid

# COMMAND ----------

# DBTITLE 1,- Inspecting  Data
spark.read.format("delta").load("dbfs:/tmp/delta/claims_liquid/").withColumn("file_name", F.element_at(F.split(F.input_file_name(), "/"), -1)).display()

# COMMAND ----------

# DBTITLE 1,- Observing Delta Log Files
# MAGIC %ls /dbfs/tmp/delta/claims_liquid/_delta_log/

# COMMAND ----------

# DBTITLE 1,- Inspecting Latest Delta Log File
# Inspecting the last delta log
with open("/dbfs/tmp/delta/claims_partitioned/_delta_log/00000000000000000003.json", "r") as f:
    for line in f:
        pprint(json.loads(line))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Performance Comparison
# MAGIC ---
# MAGIC Measure performance using Spark queries with `%timeit` for skipping benefits.
# MAGIC
# MAGIC **Explanation**
# MAGIC - Try filtering by `state='CA' AND claim_date='2020-06-01'`
# MAGIC - Compare scan statistics from both tables

# COMMAND ----------

# DBTITLE 1,- Narrow dependecy transformation for partition
# MAGIC %timeit spark.read.format("delta").load("/tmp/delta/claims_partitioned").filter("state = 'CA' AND claim_date = '2020-01-06'").show()

# COMMAND ----------

# DBTITLE 1,- Narrow dependency transformation for liquid
# MAGIC %timeit spark.read.format("delta").load("/tmp/delta/claims_liquid").filter("state = 'CA' AND claim_date = '2020-01-06'").show()

# COMMAND ----------

# DBTITLE 1,- Wide dependency transformation for partition
# MAGIC %timeit spark.read.format("delta").load("dbfs:/tmp/delta/claims_partitioned/") \
# MAGIC     .groupBy("state", "claim_date") \
# MAGIC     .agg(F.count("claim_id").alias("total_claims")) \
# MAGIC     .withColumn("file_name", F.element_at(F.split(F.input_file_name(), "/"), -1)) \
# MAGIC     .show()

# COMMAND ----------

# DBTITLE 1,- Wide dependency transformation for liquid
# MAGIC %timeit spark.read.format("delta").load("dbfs:/tmp/delta/claims_liquid/") \
# MAGIC     .groupBy("state", "claim_date") \
# MAGIC     .agg(F.count("claim_id").alias("total_claims")) \
# MAGIC     .withColumn("file_name", F.element_at(F.split(F.input_file_name(), "/"), -1)) \
# MAGIC     .show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Conclusion
# MAGIC ---
# MAGIC Use Partitioning + Z-Ordering for low-cardinality, evenly distributed columns. Use Liquid Clustering for high-cardinality or skewed distributions.
# MAGIC
# MAGIC **Explanation**
# MAGIC - Partitioning is directory-based and static.
# MAGIC - Liquid Clustering is more dynamic and easier to maintain.
# MAGIC - Choose based on data distribution and access patterns.
# MAGIC
# MAGIC **Limitations of liquid clustering**
# MAGIC - Statistucs are collected for the first 32 columns in the delta table, clustering outside this limit will not work.
# MAGIC - You can only cluster for up to 4 columns.
# MAGIC
