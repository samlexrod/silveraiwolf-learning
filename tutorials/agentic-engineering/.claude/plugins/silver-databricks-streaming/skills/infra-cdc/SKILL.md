---
description: "[Stage 3] Provision EC2 with Postgres + Debezium + Redpanda via Terraform — AWS billing starts here (~$0.02/hr)"
---

# Infrastructure — CDC Stack (EC2)

Provision the CDC infrastructure: an EC2 instance running PostgreSQL, Debezium, and Redpanda via Docker Compose. **AWS billing starts at this stage (~$0.02/hr).** OpenSearch is provisioned later in Stage 11.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 2 (deploy-dev), the learner has:
- Project scaffolded and tools installed
- Databricks Unity Catalog schema and landing zone created
- No AWS resources provisioned yet

---

## Instructions

---

### Step 1 — What We're About to Create

Before touching AWS, explain what this stage provisions and why:

**Present this overview to the user:**

This stage creates a single EC2 instance running four Docker containers via Docker Compose:

| Container | Port | Purpose |
|-----------|------|---------|
| **PostgreSQL 16** | 5432 | OLTP database — source of truth for 7 financial tables |
| **Redpanda** | 19092 | Kafka-compatible broker — receives CDC events from Debezium |
| **Redpanda Console** | 8080 | Web UI — browse topics, inspect messages, view consumer groups |
| **Debezium 2.x** | 8083 | CDC connector — watches Postgres WAL, publishes changes to Redpanda |

**What gets created in your AWS account:**

| AWS Resource | Name | Details |
|-------------|------|---------|
| **EC2 key pair** | `silveraiwolf-streaming` | SSH key for accessing the instance |
| **Security group** | `silveraiwolf-streaming-sg` | Ports: 22, 5432, 8080, 8083, 19092 |
| **EC2 instance** | `silveraiwolf-streaming-cdc` | `t3.small`, 20GB gp3, Amazon Linux 2023 |

All resources are tagged `Project = silveraiwolf-streaming` and are fully reversible with `terraform destroy`.

**Local files created:**
- `~/.ssh/silveraiwolf-streaming.pem` — private key for SSH access (never committed)
- `infra/terraform/terraform.tfvars` — your Terraform variables (gitignored)
- `infra/terraform/.terraform/` — Terraform provider cache (gitignored)

**Estimated cost:** ~$0.02/hr ($15/month). Run `/silver-databricks-streaming:cleanup` to destroy everything when done.

Use `AskUserQuestion` to confirm the user understands what will be created before proceeding.

---

### Step 2 — Configure AWS Region and Key Pair

1. Ask the user which AWS region to use (default: `us-east-1`)
2. Ask if they have an existing EC2 key pair or want to generate one:
   - **Generate new**: Creates a key pair named `silveraiwolf-streaming` in AWS and saves the private key to `~/.ssh/silveraiwolf-streaming.pem`. This key is the **only way** to SSH into the EC2 instance. Explain the command before running it:
     ```bash
     # Creates a key pair in AWS and saves the private key locally
     aws ec2 create-key-pair \
       --key-name silveraiwolf-streaming \
       --query 'KeyMaterial' --output text \
       --region us-east-1 \
       > ~/.ssh/silveraiwolf-streaming.pem

     # Restrict permissions — SSH requires the key to not be publicly readable
     chmod 400 ~/.ssh/silveraiwolf-streaming.pem
     ```
   - **Use existing**: Ask for the key pair name and path to the `.pem` file
3. After creating/confirming the key pair, present what was done:
   - Key pair `silveraiwolf-streaming` registered in AWS (public key stored by AWS)
   - Private key saved to `~/.ssh/silveraiwolf-streaming.pem` (local only, never leaves your machine)
4. Create `infra/terraform/terraform.tfvars` from the sample — explain that this file tells Terraform which region, key pair, and features to use:
   ```hcl
   aws_region    = "us-east-1"
   key_pair_name = "silveraiwolf-streaming"
   key_path      = "~/.ssh/silveraiwolf-streaming.pem"
   enable_opensearch = false  # Will be enabled in Stage 11
   ```
5. Verify `.gitignore` includes `terraform.tfvars`, `*.pem`, `.terraform/`, `*.tfstate*` — confirm to the user that sensitive files are protected from accidental commits

Use `AskUserQuestion` to confirm region and key pair.

---

### Step 3 — Configure Security Group Ingress

The EC2 security group controls which IPs can reach the instance. It needs to allow inbound traffic from Databricks on port 19092 (Redpanda/Kafka).

**Explain the trade-off:**
- `0.0.0.0/0` — open to all IPs, simplest for a tutorial, safe because the instance is short-lived
- Databricks NAT CIDRs — restricts Kafka access to only your Databricks workspace
- Your IP only — most restrictive, but breaks if your IP changes

Use `AskUserQuestion` to let the user choose. For the tutorial, recommend `0.0.0.0/0`.

---

### Step 4 — Provision EC2 with Terraform

**Important:** Terraform needs AWS credentials. Verify `AWS_PROFILE` is set (Stage 1 should have added it to `~/.zshrc`). If not, run `export AWS_PROFILE=silveraiwolf` before proceeding.

```bash
cd infra
mise run init       # terraform init
mise run plan       # terraform plan
```

Present the plan summary:

| Resource | Type | Cost |
|----------|------|------|
| EC2 instance | `t3.small` | ~$0.02/hr |
| Security group | Ingress rules | Free |

**Note:** OpenSearch is NOT provisioned yet (`enable_opensearch = false`). It will be added in Stage 11.

Use `AskUserQuestion` — "This will create an EC2 instance. Estimated cost: ~$0.02/hr ($15/month). Proceed?"

```bash
mise run apply      # terraform apply
```

Capture outputs:
```bash
cd infra && terraform -chdir=terraform output -json
```

| Output | Value |
|--------|-------|
| Public IP | `xx.xx.xx.xx` |
| SSH command | `ssh -i ~/.ssh/silveraiwolf-streaming.pem ec2-user@xx.xx.xx.xx` |
| Kafka bootstrap | `xx.xx.xx.xx:19092` |
| Redpanda Console | `http://xx.xx.xx.xx:8080` |
| Postgres host | `xx.xx.xx.xx:5432` |
| OpenSearch | `not provisioned — set enable_opensearch = true` |

**DBeaver / SQL client connection:**

| Field | Value |
|-------|-------|
| JDBC URL | `jdbc:postgresql://xx.xx.xx.xx:5432/financial_risk` |
| Username | `postgres` |
| Password | `postgres` |
| Database | `financial_risk` |

---

### Step 5 — Verify CDC Stack

Wait ~1-2 minutes for cloud-init, then verify:

```bash
ssh -i <key_path> ec2-user@<public_ip> "cd ~/cdc-stack && docker compose ps"
```

Expected: 4 containers running (postgres, redpanda, redpanda-console, debezium).

**Important — Set EC2_PUBLIC_IP on the EC2 instance.** Redpanda uses this to advertise the correct external address to Kafka clients (including Databricks). Without it, clients connect to port 19092 but get metadata with a blank/wrong IP and can't produce or consume:

```bash
ssh -i <key_path> ec2-user@<public_ip> "echo 'EC2_PUBLIC_IP=<public_ip>' > ~/cdc-stack/.env && cd ~/cdc-stack && docker compose down && docker compose up -d"
```

Wait ~30 seconds for containers to restart, then verify:

```bash
# Confirm Redpanda advertises the correct external IP
ssh -i <key_path> ec2-user@<public_ip> "docker exec redpanda cat /etc/redpanda/redpanda.yaml | grep -A3 'advertised_kafka'"
```

The external listener should show the EC2 public IP, not blank or `0.0.0.0`.

Tell the user they can open the Redpanda Console in their browser at `http://<public_ip>:8080` to visually browse topics, inspect messages, and monitor consumer groups throughout the tutorial.

```bash
# Test Kafka connectivity
nc -zv <public_ip> 19092

# Test Postgres connectivity
PGPASSWORD=postgres psql -h <public_ip> -U postgres -c "SELECT 1"
```

---

### Step 6 — Save Connection Config

Update `.env` with infrastructure outputs:

```bash
EC2_PUBLIC_IP=xx.xx.xx.xx
KAFKA_BOOTSTRAP_SERVERS=xx.xx.xx.xx:19092
POSTGRES_HOST=xx.xx.xx.xx
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=financial_risk
```

---

### Step 7 — Summary

| Component | Status | Cost |
|-----------|--------|------|
| EC2 instance | ✓ Running | ~$0.02/hr |
| PostgreSQL | ✓ Running | (included in EC2) |
| Debezium | ✓ Running | (included in EC2) |
| Redpanda | ✓ Running | (included in EC2) |
| Redpanda Console | ✓ Running | `http://<public_ip>:8080` |
| OpenSearch | Not provisioned | $0 (Stage 11) |
| **Total AWS cost** | | **~$0.02/hr** |

**Next:** Run `/silver-databricks-streaming:seed-postgres` to create tables and insert seed data.
