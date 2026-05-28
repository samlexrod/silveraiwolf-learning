"""OpenSearch sink — NOT USED in the unified pipeline.

This file is kept for reference only. The actual OpenSearch sink runs as a
Docker container on EC2 using PySpark JDBC + opensearch-hadoop. See:
  infra/opensearch-sink/sink.py      — the production sink
  infra/opensearch-sink/Dockerfile   — PySpark + JDK + JDBC/OpenSearch JARs

Why not in-pipeline?
  Databricks serverless SDP has several limitations that prevent in-pipeline
  OpenSearch sinking:
  1. Maven JARs blocked — opensearch-hadoop requires a JVM connector JAR
  2. foreachPartition / toPandas blocked — PY4J_BLOCKED_API (RDD access denied)
  3. collect() works but materialized views cache results, preventing re-execution
  4. environment.dependencies works for PyPI packages (set via pipeline REST API)
     but the serverless runtime still blocks RDD-level operations needed to
     extract data from DataFrames for external writes

The production-ready pattern:
  Serverless SDP handles pure transforms (Bronze → Silver → Gold).
  A separate PySpark process on EC2 reads Gold tables via JDBC from the SQL
  warehouse and writes to OpenSearch via df.write.format("opensearch") using
  the opensearch-hadoop connector. Sync stats are written back to
  gold_opensearch_sync via JDBC for monitoring.
"""
