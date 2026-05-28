#!/bin/bash
set -euo pipefail

# Log all output for debugging
exec > /var/log/user-data.log 2>&1

echo "=== Installing Docker ==="
dnf update -y
dnf install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

echo "=== Installing Docker Compose plugin ==="
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "=== Creating Docker Compose project ==="
mkdir -p /home/ec2-user/cdc-stack
cd /home/ec2-user/cdc-stack

# Get the instance's public IP for Redpanda advertised address
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
EC2_PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/public-ipv4)

export EC2_PUBLIC_IP

cat > docker-compose.yml << 'COMPOSE_EOF'
version: "3.8"

services:
  postgres:
    image: postgres:16
    container_name: postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: financial_risk
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    command:
      - "postgres"
      - "-c"
      - "wal_level=logical"
      - "-c"
      - "max_replication_slots=4"
      - "-c"
      - "max_wal_senders=4"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redpanda:
    image: docker.redpanda.com/redpandadata/redpanda:v24.1.1
    container_name: redpanda
    command:
      - redpanda
      - start
      - --smp 1
      - --memory 512M
      - --overprovisioned
      - --kafka-addr internal://0.0.0.0:9092,external://0.0.0.0:19092
      - --advertise-kafka-addr internal://redpanda:9092,external://${EC2_PUBLIC_IP}:19092
      - --pandaproxy-addr internal://0.0.0.0:8082,external://0.0.0.0:18082
      - --advertise-pandaproxy-addr internal://redpanda:8082,external://${EC2_PUBLIC_IP}:18082
    ports:
      - "9092:9092"
      - "19092:19092"
      - "8082:8082"
      - "18082:18082"
    volumes:
      - redpanda:/var/lib/redpanda/data
    healthcheck:
      test: ["CMD", "rpk", "cluster", "health"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  debezium:
    image: debezium/connect:2.7.3.Final
    container_name: debezium
    ports:
      - "8083:8083"
    environment:
      BOOTSTRAP_SERVERS: redpanda:9092
      GROUP_ID: 1
      CONFIG_STORAGE_TOPIC: _debezium_configs
      OFFSET_STORAGE_TOPIC: _debezium_offsets
      STATUS_STORAGE_TOPIC: _debezium_status
      CONFIG_STORAGE_REPLICATION_FACTOR: 1
      OFFSET_STORAGE_REPLICATION_FACTOR: 1
      STATUS_STORAGE_REPLICATION_FACTOR: 1
    depends_on:
      postgres:
        condition: service_healthy
      redpanda:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8083/connectors || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  redpanda-console:
    image: docker.redpanda.com/redpandadata/console:v2.6.0
    container_name: redpanda-console
    ports:
      - "8080:8080"
    environment:
      CONFIG_FILEPATH: ""
      KAFKA_BROKERS: redpanda:9092
    depends_on:
      redpanda:
        condition: service_healthy
    restart: unless-stopped

volumes:
  pgdata:
  redpanda:
COMPOSE_EOF

echo "=== Starting Docker Compose ==="
docker compose up -d

echo "=== Waiting for services to be healthy ==="
sleep 30
docker compose ps

echo "=== CDC stack ready ==="
chown -R ec2-user:ec2-user /home/ec2-user/cdc-stack
