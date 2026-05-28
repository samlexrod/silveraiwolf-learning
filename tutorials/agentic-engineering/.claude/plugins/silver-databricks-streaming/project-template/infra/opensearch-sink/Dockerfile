FROM python:3.11-slim

# JDK 21 required by PySpark (Debian Trixie ships JDK 21)
RUN apt-get update && \
    apt-get install -y --no-install-recommends openjdk-21-jre-headless curl && \
    rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
RUN mkdir -p /app/jars

# Databricks JDBC driver (v3 — open-source, from Maven Central)
RUN curl -fSL -o /app/jars/databricks-jdbc.jar \
    "https://repo1.maven.org/maven2/com/databricks/databricks-jdbc/3.3.1/databricks-jdbc-3.3.1.jar"

# opensearch-hadoop Spark connector (Spark 4.x + Scala 2.13)
RUN curl -fSL -o /app/jars/opensearch-spark.jar \
    "https://repo1.maven.org/maven2/org/opensearch/client/opensearch-spark-40_2.13/2.0.0/opensearch-spark-40_2.13-2.0.0.jar"

COPY pyproject.toml .
RUN uv sync --no-dev

COPY sink.py .

CMD ["uv", "run", "python", "-u", "sink.py"]
