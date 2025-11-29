# Project 01: News Classifier Agent

> **Part of:** [Databricks Lakehouse Track](../)

A 2-Way Track Experiment comparing External vs. Internal LLMs for news classification using zero-shot learning.

## Quick Start

```bash
# Navigate to project
cd databricks/project_01_news_classifier

# Install environment
conda env create -f conda.yaml
conda activate news-classifier-agent

# Configure credentials
cp config/.env.example config/.env
# Edit config/.env with your Databricks credentials

# Start with EDA
jupyter lab
# Open: notebooks/01_eda_news_classifier.ipynb

# Run experiments
make run-both
```

## Experimental Strategy

### The Question We're Answering

**"Should we use external LLMs (OpenAI/Anthropic) or Databricks Foundation Models for news classification in production?"**

This is a **controlled experiment** comparing two approaches to solve the same problem:

### The Problem
Automatically classify news articles by:
1. **Category** (Politics, Technology, Business, Sports, etc.)
2. **Sentiment** (Positive, Neutral, Negative)

### The Hypothesis
Both external and internal LLMs can perform zero-shot classification, but they differ in:
- **Accuracy** - Which produces better results?
- **Cost** - External API calls vs internal compute
- **Latency** - Network roundtrip vs internal network
- **Governance** - External data egress vs Unity Catalog controls

### The Experimental Design

We run **identical experiments** on both tracks:
- ✅ **Same dataset** - 10 sample news articles
- ✅ **Same prompts** - Zero-shot classification template
- ✅ **Same metrics** - Accuracy, precision, recall, F1
- ✅ **Same evaluation** - Confusion matrices, per-class metrics

**The only variable:** External LLM vs Databricks Foundation Model

### Track A: External Model Agent
- **What**: Use external LLM providers (OpenAI/Anthropic)
- **Why**: Industry-leading models, potentially higher accuracy
- **Trade-offs**:
  - ✅ State-of-the-art models (GPT-4, Claude)
  - ✅ Proven performance
  - ❌ Higher cost ($$$)
  - ❌ Data leaves Databricks (compliance concern)
  - ❌ API key management required

**Models tested:**
- GPT-4o-mini (OpenAI)
- Claude 3.5 Sonnet (Anthropic)

### Track B: Databricks Foundation Model Agent
- **What**: Use Databricks-hosted Foundation Models (OpenAI, Google, Meta, Anthropic, and open models)
- **Why**: Cost-effective, governed, internal to platform, no data egress
- **Trade-offs**:
  - ✅ Lower cost (pay-per-token, no external API fees)
  - ✅ Data stays in Databricks (governance & compliance)
  - ✅ Lower latency (no external API calls)
  - ✅ Built-in Unity Catalog integration
  - ✅ Access to GPT-5.1, Claude, Gemini via Databricks
  - ✅ Wide model variety (20+ models)

**Models available:**
- **OpenAI via Databricks**: GPT-5.1, GPT-5, GPT-5-mini, GPT OSS 120B, GPT OSS 20B
- **Google**: Gemini 3 Pro, Gemini 2.5 Pro, Gemini 2.5 Flash
- **Meta Llama**: Llama 4 Maverick, Llama 3.3 70B, Llama 3.1 405B/8B
- **Anthropic**: Claude Sonnet 4.5, Claude Sonnet 4, Claude Opus 4.1
- **Databricks**: DBRX (proprietary flagship)
- **Open models**: Qwen3 Next 80B (Alibaba)

### What Gets Measured

For each track, we log:

| Metric Type | What We Measure | Why It Matters |
|-------------|----------------|----------------|
| **Accuracy** | % correct predictions | Core performance indicator |
| **Precision/Recall/F1** | Per-category metrics | Understand class-specific performance |
| **Confusion Matrix** | Which categories get confused | Identify systematic errors |
| **Latency** | Time per prediction | Production SLA consideration |
| **Cost** | $ per prediction | Budget impact at scale |

### The Decision Framework

After running both experiments, you can make a **data-driven decision**:

```
If accuracy difference < 5% AND cost savings > 50%
  → Use Track B (Databricks Foundation Models)

If accuracy is critical AND budget allows
  → Use Track A (External LLMs)

If data governance is required
  → Use Track B (data stays in Databricks)

If real-time latency is critical
  → Use Track B (lower network overhead)
```

### Real-World Scenario

**Example:** A news aggregation company needs to classify 1M articles/day

| Approach | Accuracy | Cost/Day | Latency | Governance |
|----------|----------|----------|---------|------------|
| Track A (GPT-4o-mini via OpenAI API) | 92% | $500 | 2.5s | ❌ Data egress |
| Track B (GPT-5.1 via Databricks) | 94% | $150 | 1.5s | ✅ Internal |
| Track B (GPT OSS 20B via Databricks) | 88% | $30 | 1.0s | ✅ Internal |
| Track B (DBRX) | 88% | $50 | 1.2s | ✅ Internal |

**Decision:** Track B with GPT-5.1 provides BETTER accuracy at 70% lower cost with full governance. **Winner: Track B (GPT-5.1)**

### Why This Matters

This experiment teaches you to:
1. ✅ **Design controlled ML experiments** - Single variable testing
2. ✅ **Use MLflow for tracking** - Professional experiment management
3. ✅ **Make data-driven decisions** - Not just "use the best model"
4. ✅ **Consider total cost** - Accuracy isn't everything
5. ✅ **Production thinking** - Governance, latency, cost matter

## Overview

This project implements two parallel MLflow experiments for news classification:

### Track A: External Model Agent
- **Provider**: OpenAI or Anthropic
- **Models**: GPT-4o-mini, Claude 3.5 Sonnet
- **Approach**: External API calls with secrets management

### Track B: Databricks Foundation Model Agent
- **Provider**: Databricks Foundation Model APIs (OpenAI, Google, Meta, Anthropic, OSS)
- **Models**: GPT-5.1, GPT OSS 20B/120B, Claude 4.5, Gemini 3, Llama 4, DBRX, and more
- **Approach**: Pay-per-token via Databricks, data stays internal

## Project Structure

```
project_01_news_classifier/
├── MLproject                     # MLflow project file (entry points)
├── conda.yaml                    # Conda environment specification
├── main.py                       # Main entry point (runs both tracks)
├── Makefile                      # Quick commands for running experiments
├── notebooks/                    # 📓 Jupyter notebooks for EDA
│   ├── 01_eda_news_classifier.ipynb  # Exploratory data analysis
│   └── README.md                 # Notebook documentation
├── config/
│   ├── .env.example              # Environment variables template
│   └── news_categories.py        # Classification categories & prompts
├── track_a_external/
│   ├── external_agent.py         # External model implementation
│   └── experiment_external.py    # MLflow experiment runner
├── track_b_internal/
│   ├── internal_agent.py         # Internal model implementation
│   └── experiment_internal.py    # MLflow experiment runner
├── data/
│   └── sample_news.json          # Sample news dataset (10 articles)
├── utils/
│   ├── databricks_auth.py        # Databricks authentication
│   └── mlflow_helpers.py         # MLflow utilities
├── docs/
│   └── notebooks-vs-mlproject.md # Why MLproject > notebooks
└── README.md                     # This file
```

## Why MLproject with Conda (Not Jupyter Notebooks)?

This project uses MLflow's `MLproject` file with conda environments - **not Jupyter notebooks** - for production-grade ML experimentation:

### Key Benefits:

1. **Reproducibility** 🔄
   - Conda ensures identical environments across machines
   - No "works on my machine" issues
   - Cells can't run out of order

2. **Automation** 🤖
   - Run experiments via CLI: `mlflow run . -P provider=openai`
   - Easy CI/CD integration
   - Scheduled experiments in Databricks Jobs

3. **Version Control** 📝
   - Clean Python files = readable git diffs
   - Easy code reviews
   - No JSON bloat from notebooks

4. **MLflow Integration** 📊
   - Automatic experiment tracking
   - Compare runs side-by-side
   - Model registry integration

5. **Production-Ready** 🚀
   - Same code runs locally and in production
   - Deploy directly to Databricks
   - No "productionization" rewrite needed

6. **Professional Structure** 🧩
   - Modular, reusable code
   - Unit testable
   - Team collaboration friendly

**📖 Read the full comparison:** [docs/notebooks-vs-mlproject.md](docs/notebooks-vs-mlproject.md)

### When to Use Notebooks:
- ✅ Exploratory data analysis (EDA)
- ✅ Quick prototyping
- ✅ Visualizing MLflow results

### When to Use MLproject (This Project):
- ✅ Production experiments
- ✅ Reproducible research
- ✅ Team collaboration
- ✅ Automated training pipelines

## Setup

### 1. Install Conda Environment

```bash
cd /Users/samuel/Programing/silveraiwolf-learning/curriculum/tracks/databricks

# Create conda environment from conda.yaml
make install

# Or manually with conda
conda env create -f conda.yaml

# Activate the environment
conda activate news-classifier-agent
```

### 2. Configure Databricks Connection

Copy the example environment file and configure your credentials:

```bash
cp config/.env.example config/.env
```

Edit `config/.env` with your details:

```bash
# Databricks Configuration
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-personal-access-token

# MLflow Configuration (defaults are usually fine)
MLFLOW_TRACKING_URI=databricks
MLFLOW_REGISTRY_URI=databricks-uc

# Experiment Names
MLFLOW_EXPERIMENT_NAME_EXTERNAL=/Users/your-email@company.com/news-classifier-external
MLFLOW_EXPERIMENT_NAME_INTERNAL=/Users/your-email@company.com/news-classifier-internal

# Unity Catalog (adjust to your workspace)
UC_CATALOG=main
UC_SCHEMA=news_classifier
```

### 3. Get Databricks Personal Access Token

1. Go to your Databricks workspace
2. Click on your user profile (top right)
3. Select **User Settings**
4. Go to **Access tokens** tab
5. Click **Generate new token**
6. Copy the token and add to `.env`

### 4. Configure API Keys (Track A Only)

For Track A (external models), you need API keys:

**Option 1: Local Development (Environment Variables)**
```bash
# Add to config/.env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Option 2: Production (Databricks Secrets)**

Create a secret scope in Databricks:
```bash
# Using Databricks CLI
databricks secrets create-scope news-classifier-secrets

# Add your API keys
databricks secrets put-secret news-classifier-secrets openai-api-key
databricks secrets put-secret news-classifier-secrets anthropic-api-key
```

Then run experiments with `--use-secrets` flag.

### 5. Create MLflow Experiments in Databricks

1. Go to your Databricks workspace
2. Navigate to **Workspace** → **Users** → your email
3. Create folders for experiments (or let the scripts create them automatically)

Alternatively, the scripts will auto-create experiments on first run.

## Complete Workflow: Exploration → Experimentation → Production

### Phase 1: Exploration (Notebooks) 📓

**Start here to understand the data and prototype your approach.**

```bash
# Launch Jupyter
conda activate news-classifier-agent
jupyter lab

# Open: notebooks/01_eda_news_classifier.ipynb
```

**What you'll do:**
1. ✅ Explore the 10 sample news articles
2. ✅ Visualize category and sentiment distributions
3. ✅ Test zero-shot prompts with OpenAI
4. ✅ Test zero-shot prompts with Databricks DBRX
5. ✅ Validate that the approach works

**Output:** Understanding of the data + confidence that zero-shot works

**Time:** 30-60 minutes

---

### Phase 2: Experimentation (MLproject) 🔬

**Run formal experiments with automatic MLflow tracking.**

```bash
# Run Track A (External - OpenAI)
make run-external PROVIDER=openai

# Run Track A (External - Anthropic)
make run-external PROVIDER=anthropic

# Run Track B (Internal - DBRX)
make run-internal MODEL=databricks-dbrx-instruct

# Or run both tracks at once
make run-both
```

**What happens:**
1. ✅ All 10 articles classified
2. ✅ Metrics automatically logged to MLflow
3. ✅ Confusion matrices generated
4. ✅ Models registered to Unity Catalog
5. ✅ Results comparable in Databricks UI

**Output:** Tracked experiments with metrics, artifacts, and registered models

**Time:** 5-10 minutes per track

---

### Phase 3: Analysis (Optional Notebook) 📊

**Create a notebook to analyze MLflow results.**

```python
# notebooks/02_analyze_results.ipynb

import mlflow
mlflow.set_tracking_uri("databricks")

# Load experiment results
runs = mlflow.search_runs(experiment_ids=['...'])

# Compare Track A vs Track B
# - Accuracy by category
# - Cost per prediction
# - Latency analysis
# - Visualizations
```

**Output:** Data-driven decision on which model to use

---

### Phase 4: Production (MLproject) 🚀

**Deploy the winning model to production.**

```bash
# Deploy as Databricks Job
databricks jobs create --json '{
  "name": "News Classifier - Production",
  "schedule": {"quartz_cron_expression": "0 0 * * *"},
  "mlflow_project": {
    "git_url": "https://github.com/...",
    "entry_point": "track_b_internal"
  }
}'

# Or serve via Model Serving
# Load model: main.news_classifier.internal_dbrx_classifier
```

**Output:** Production-ready model deployment

---

## Running Experiments

### Using Make (Recommended)

```bash
# Run Track A (External Model with OpenAI)
make run-external

# Run Track A with Anthropic
make run-external PROVIDER=anthropic

# Run Track B (Internal Model with DBRX)
make run-internal

# Run Track B with Llama-3
make run-internal MODEL=databricks-meta-llama-3-70b-instruct

# Run BOTH tracks for comparison
make run-both
```

### Using MLflow Run Directly

```bash
# Activate conda environment first
conda activate news-classifier-agent

# Run Track A (External Model)
mlflow run . -e track_a_external -P provider=openai
mlflow run . -e track_a_external -P provider=anthropic

# Run Track B (Internal Model)
mlflow run . -e track_b_internal -P model=databricks-dbrx-instruct
mlflow run . -e track_b_internal -P model=databricks-meta-llama-3-70b-instruct

# Run both tracks
mlflow run . -e main -P track=both
```

### Using Python Directly (Alternative)

```bash
# Activate conda environment first
conda activate news-classifier-agent

# Run Track A
python track_a_external/experiment_external.py --provider openai
python track_a_external/experiment_external.py --provider anthropic

# Run Track B
python track_b_internal/experiment_internal.py --model databricks-dbrx-instruct

# Run both
python main.py --track both
```

## What Gets Logged to MLflow

Each experiment logs:

1. **Parameters**:
   - Model provider and name
   - Track identifier (A or B)
   - Timestamp
   - Number of articles processed

2. **Metrics**:
   - Category classification accuracy
   - Category precision, recall, F1 (overall + per-class)
   - Sentiment classification accuracy
   - Sentiment precision, recall, F1 (overall + per-class)

3. **Artifacts**:
   - Predictions CSV and JSON
   - Confusion matrices
   - Model wrapper (using MLflow ResponsesAgent)

4. **Model**:
   - Registered to Unity Catalog as: `{catalog}.{schema}.{model_name}`
   - Versioned automatically
   - Tagged with track and provider info

## Viewing Results

### In Databricks UI

1. Navigate to **Machine Learning** → **Experiments**
2. Find your experiments:
   - `/Users/your-email/news-classifier-external`
   - `/Users/your-email/news-classifier-internal`
3. Compare runs side-by-side
4. View metrics, parameters, and artifacts

### Via MLflow Python API

```python
import mlflow

mlflow.set_tracking_uri("databricks")

# Get experiment
experiment = mlflow.get_experiment_by_name("/Users/your-email/news-classifier-external")

# List runs
runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
print(runs[['metrics.category_accuracy', 'metrics.sentiment_accuracy', 'params.provider']])
```

## Expected Results

With the sample dataset (10 articles):

| Track | Model | Category Acc | Sentiment Acc | Latency | Notes |
|-------|-------|--------------|---------------|---------|-------|
| A | GPT-4o-mini (external) | ~90% | ~90% | ~2-3s | Direct API call |
| A | Claude 3.5 (external) | ~90% | ~90% | ~2-3s | Direct API call |
| B | GPT-5.1 (Databricks) | ~92-95% | ~92-95% | ~1.5s | Latest GPT via DB |
| B | GPT-5 (Databricks) | ~92-94% | ~92-94% | ~1.5s | SOTA reasoning |
| B | GPT OSS 120B | ~90-92% | ~90-92% | ~1.8s | OSS reasoning model |
| B | GPT OSS 20B | ~85-90% | ~85-90% | ~0.8s | Lightweight OSS |
| B | Claude 4.5 (Databricks) | ~92-94% | ~92-94% | ~1.6s | Hybrid reasoning |
| B | Gemini 3 Pro | ~90-93% | ~90-93% | ~1.7s | 1M context |
| B | Llama 4 Maverick | ~88-92% | ~88-92% | ~1.4s | MoE architecture |
| B | DBRX | ~85-90% | ~85-90% | ~1.2s | Databricks flagship |
| B | Llama 3.3 70B | ~86-90% | ~86-90% | ~1.3s | Open model |

*Note: Results may vary based on model versions and prompt engineering*

## Zero-Shot Classification Approach

Both tracks use the same zero-shot classification prompt template defined in `config/news_categories.py`:

```python
Categories: Politics, Technology, Business, Sports, Entertainment, Health, Science, World News
Sentiments: Positive, Neutral, Negative

News Article:
Title: {title}
Content: {content}

Response:
Category: <category>
Sentiment: <sentiment>
```

No training or fine-tuning is required - the models classify based on their pre-trained knowledge.

## Unity Catalog Model Registry

Models are registered to Unity Catalog with naming convention:

- Track A: `{catalog}.{schema}.external_{provider}_classifier`
  - Example: `main.news_classifier.external_openai_classifier`
- Track B: `{catalog}.{schema}.internal_{model}_classifier`
  - Example: `main.news_classifier.internal_dbrx_classifier`

To use a registered model:

```python
import mlflow

# Load latest version
model = mlflow.pyfunc.load_model("models:/main.news_classifier.external_openai_classifier/latest")

# Predict
result = model.predict({"title": "Breaking News", "content": "..."})
print(result)  # {"category": "World News", "sentiment": "Neutral", ...}
```

## Troubleshooting

### Error: "DATABRICKS_HOST and DATABRICKS_TOKEN must be set"
- Check that `config/.env` exists and contains valid credentials
- Ensure you're loading the `.env` file (scripts use `python-dotenv`)

### Error: "Could not retrieve secret from Databricks"
- Verify secret scope exists: `databricks secrets list-scopes`
- Check secret keys exist: `databricks secrets list --scope news-classifier-secrets`
- Ensure you have permissions to read the scope

### Error: "Foundation Model endpoint not found"
- Verify the model endpoint name in Databricks UI: **Serving** → **Foundation Model APIs**
- Common endpoints: `databricks-dbrx-instruct`, `databricks-meta-llama-3-70b-instruct`

### Error: "Failed to register to Unity Catalog"
- Ensure the catalog and schema exist: `{catalog}.{schema}`
- Check you have `CREATE MODEL` permissions on the schema
- Use `--no-register` flag to skip registration during testing

## Production Model Promotion

This project implements **3 production-grade approaches** for promoting models from experiments to production. Learn all three patterns used in real ML engineering teams:

### Production Criteria

Before any model reaches production, it must pass validation gates defined in [utils/production_criteria.py](utils/production_criteria.py):

| Criterion | Threshold | Why |
|-----------|-----------|-----|
| **Accuracy** | ≥ 90% | Minimum acceptable performance |
| **F1 Score** | ≥ 0.85 | Balanced precision/recall |
| **Precision** | ≥ 0.80 | Low false positive rate |
| **Recall** | ≥ 0.80 | Low false negative rate |
| **Beats Champion** | +2% accuracy | Must improve on current production |

### Option 1: Manual Approval Gate

**Use case:** Human-in-the-loop validation for critical production systems

After experiment completes, require manual approval before Unity Catalog registration:

```bash
# Run with manual approval gate
python track_b_internal/experiment_internal.py \
  --model databricks-gpt-5-1 \
  --require-approval
```

**What happens:**
1. Experiment runs and logs metrics
2. System evaluates production criteria
3. **Prompts for manual approval**: `Register to Unity Catalog? (yes/no):`
4. Only registers if you type `yes`

**Example output:**
```
================================================================================
PRODUCTION CRITERIA EVALUATION
================================================================================

Performance Metrics:
  Accuracy:  92.00% ✅ (threshold: 90.00%)
  F1 Score:  0.876 ✅ (threshold: 0.850)
  Precision: 0.891 ✅ (threshold: 0.800)
  Recall:    0.862 ✅ (threshold: 0.800)

================================================================================
✅ PASSES PRODUCTION CRITERIA
Reason: All performance criteria met
================================================================================

================================================================================
MANUAL APPROVAL REQUIRED
================================================================================
✅ Model meets production criteria

🤔 Register to Unity Catalog? (yes/no): yes
```

### Option 2: Automated Gating with Tags

**Use case:** Fast iteration with automatic safety checks (Default behavior)

Models are automatically registered with tags indicating production readiness:

```bash
# Run with automated gating (default)
python track_b_internal/experiment_internal.py \
  --model databricks-gpt-oss-20b
```

**What happens:**
1. Experiment runs and logs metrics
2. System evaluates production criteria
3. **Always registers** to Unity Catalog
4. Tags model with `production_ready=true` or `production_ready=false`

**Model tags in Unity Catalog:**
```python
{
    "track": "B",
    "provider": "databricks",
    "model": "databricks-gpt-oss-20b",
    "category_accuracy": "0.8800",
    "category_f1": "0.8520",
    "production_ready": "false",  # ❌ Failed criteria
    "validation_reason": "Accuracy 88.00% below 90.00% threshold"
}
```

**Query production-ready models:**
```python
import mlflow
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Find all production-ready models
models = client.search_registered_models(
    filter_string="tags.production_ready='true'"
)

for model in models:
    print(f"✅ {model.name} - Ready for production")
```

### Option 3: Standalone Promotion Script

**Use case:** Post-experiment promotion with champion comparison (Netflix/Uber pattern)

Promote a specific experiment run after manual review:

```bash
# List candidate models
python scripts/promote_to_production.py --list-candidates

# Promote a specific run
python scripts/promote_to_production.py --run-id abc123def456

# Force promotion (override criteria)
python scripts/promote_to_production.py --run-id abc123def456 --force

# Promote to Staging (not production)
python scripts/promote_to_production.py --run-id abc123def456 --alias Staging
```

**Validation gates:**
1. ✅ **Performance criteria** - Must meet minimum thresholds
2. ✅ **Champion comparison** - Must beat current production model by ≥2%
3. ✅ **Manual override** - Use `--force` to bypass gates

**Example workflow:**
```bash
# Step 1: Run experiments
python track_b_internal/experiment_internal.py --model databricks-gpt-5-1 --no-register

# Step 2: Review results in Databricks UI
# Navigate to: Machine Learning → Experiments → news-classifier-internal

# Step 3: List candidates
python scripts/promote_to_production.py --list-candidates

# Output:
# Found 3 candidate(s):
#
# 1. Run ID: abc123
#    Name: internal_gpt-5-1_20251129_143022
#    Accuracy: 94.00%
#    F1 Score: 0.912
#
# 2. Run ID: def456
#    Name: internal_gpt-oss-120b_20251129_142015
#    Accuracy: 91.00%
#    F1 Score: 0.887

# Step 4: Promote best model
python scripts/promote_to_production.py --run-id abc123

# Output:
# [1/5] Loading run details...
# ✓ Run Name: internal_gpt-5-1_20251129_143022
#
# [2/5] Validating performance criteria...
# ✅ PASSES PRODUCTION CRITERIA
#
# [3/5] Extracting model information...
# ✓ Model Name: main.news_classifier.internal_gpt-5-1_classifier
#
# [4/5] Checking against current champion...
# ✓ New model beats current Champion by 2.50%
#
# [5/5] Promoting model to production...
# ✓ Registered as version: 3
# ✓ Set alias 'Champion' to version 3
#
# ✅ PROMOTION SUCCESSFUL
# Model: main.news_classifier.internal_gpt-5-1_classifier
# Version: 3
# Alias: Champion
#
# To load in production:
#   model = mlflow.pyfunc.load_model('models:/main.news_classifier.internal_gpt-5-1_classifier@Champion')
```

### Unity Catalog Aliases

Models use aliases to indicate production stages:

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()
model_name = "main.news_classifier.internal_gpt-5-1_classifier"

# Set production stages
client.set_registered_model_alias(model_name, "Candidate", version=1)  # Testing
client.set_registered_model_alias(model_name, "Staging", version=2)    # Pre-prod
client.set_registered_model_alias(model_name, "Champion", version=3)   # Production

# Load specific stage
champion_model = mlflow.pyfunc.load_model(f"models:/{model_name}@Champion")
staging_model = mlflow.pyfunc.load_model(f"models:/{model_name}@Staging")
```

### Comparison: When to Use Each Option

| Approach | Use Case | Automation | Safety | Speed |
|----------|----------|------------|--------|-------|
| **Option 1: Manual Gate** | Critical systems, regulatory compliance | ❌ Manual | 🔒 Highest | 🐌 Slowest |
| **Option 2: Auto Tags** | Fast iteration, experimentation | ✅ Full | ⚠️ Medium | ⚡ Fastest |
| **Option 3: Standalone** | Production workflows, champion tracking | ⚙️ Semi-auto | 🔒 High | 🚶 Medium |

### Custom Criteria

Override default production criteria by editing [utils/production_criteria.py](utils/production_criteria.py):

```python
from utils.production_criteria import ProductionCriteria

# Stricter criteria
strict_criteria = ProductionCriteria(
    min_accuracy=0.95,      # 95% accuracy required
    min_f1_score=0.90,      # 90% F1 required
    min_accuracy_improvement=0.05  # 5% improvement over champion
)

# Pass to promotion script
promote_model_to_production(run_id="abc123", criteria=strict_criteria)
```

## Next Steps

1. **Expand Dataset**: Add more news articles to `data/sample_news.json`
2. **Fine-tune Prompts**: Modify templates in `config/news_categories.py`
3. **Add Categories**: Extend `NEWS_CATEGORIES` for more specific classification
4. **Compare Costs**: Track API costs for Track A vs compute costs for Track B
5. **Production Deployment**: Deploy registered models as Databricks Model Serving endpoints
6. **A/B Testing**: Route production traffic to compare real-world performance

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Databricks Workspace                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐                      ┌──────────────┐     │
│  │   Track A    │                      │   Track B    │     │
│  │   External   │                      │   Internal   │     │
│  │              │                      │              │     │
│  │  ┌────────┐  │                      │  ┌────────┐  │     │
│  │  │OpenAI  │──┼──[Secret Scope]     │  │  DBRX  │  │     │
│  │  │Claude  │  │   (API Keys)         │  │ Llama-3│  │     │
│  │  └────────┘  │                      │  └────────┘  │     │
│  └──────┬───────┘                      └──────┬───────┘     │
│         │                                     │             │
│         └──────────────┬──────────────────────┘             │
│                        ▼                                    │
│              ┌──────────────────┐                           │
│              │  MLflow Tracking │                           │
│              │   & Experiments  │                           │
│              └─────────┬────────┘                           │
│                        ▼                                    │
│              ┌──────────────────┐                           │
│              │ Unity Catalog    │                           │
│              │ Model Registry   │                           │
│              └──────────────────┘                           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## What You'll Learn

By completing this project:

1. ✅ **MLflow Experimentation** - Professional experiment tracking
2. ✅ **MLproject Structure** - Production-ready project organization
3. ✅ **ResponsesAgent** - Proper GenAI model logging
4. ✅ **Unity Catalog** - Model registry and governance
5. ✅ **Databricks Secrets** - Secure API key management
6. ✅ **External APIs** - OpenAI/Anthropic integration
7. ✅ **Foundation Models** - Databricks internal LLMs
8. ✅ **Zero-Shot Learning** - No fine-tuning required
9. ✅ **Notebooks vs MLproject** - When to use each
10. ✅ **Cost Comparison** - External vs internal models

## License

Part of the SilverAIWolf Databricks Lakehouse Track curriculum.

## Support

For issues or questions:
1. Check this README
2. Review [Databricks documentation](https://docs.databricks.com/)
3. Check [MLflow docs](https://mlflow.org/docs/latest/index.html)
4. See [Track-level README](../)

---

← [Back to Databricks Track](../) | [Next Project →](../project_02_*)
