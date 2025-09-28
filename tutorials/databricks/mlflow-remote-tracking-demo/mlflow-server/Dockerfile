FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    mlflow \
    boto3 \
    psycopg2-binary \
    pymysql \
    sqlalchemy

EXPOSE 5000

ENV MLFLOW_BACKEND_STORE_URI=sqlite:///mlflow.db
ENV MLFLOW_DEFAULT_ARTIFACT_ROOT=./artifacts
ENV MLFLOW_HOST=0.0.0.0
ENV MLFLOW_PORT=5000

CMD ["sh", "-c", "mlflow server --backend-store-uri ${MLFLOW_BACKEND_STORE_URI} --default-artifact-root ${MLFLOW_DEFAULT_ARTIFACT_ROOT} --host ${MLFLOW_HOST} --port ${MLFLOW_PORT}"]