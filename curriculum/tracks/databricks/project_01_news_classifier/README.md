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

# Run all experiments to determine champion
make run-all

# Promote challenger to champion (after review)
make promote
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
- Claude Sonnet 4.5 (Anthropic) - Latest as of Sept 2025

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

**Models available in Free Edition (as of November 2025):**

**✅ Available in Free Edition:**
- **OpenAI**: `databricks-gpt-5-1` ⚠️ **Heavy rate limits**, `databricks-gpt-oss-120b`, `databricks-gpt-oss-20b` ✅ **Recommended**
- **Meta Llama**: `databricks-llama-4-maverick`, `databricks-meta-llama-3-3-70b-instruct`, `databricks-meta-llama-3-1-405b-instruct`, `databricks-meta-llama-3-1-8b-instruct`
- **Google**: `databricks-gemma-3-12b`
- **Alibaba**: `databricks-qwen3-next-80b-a3b-instruct`
- **Embeddings**: `databricks-gte-large-en`, `databricks-bge-large-en`

**❌ NOT Available in Free Edition:**
- **Anthropic**: Claude models (Sonnet 4.5, Sonnet 4, Opus 4.1)
- **Google**: Gemini 2.5/3 Pro/Flash models
- Other commercial models may require paid tier

> ⚠️ **RETIRED (April 2025):** `databricks-dbrx-instruct`, `databricks-mixtral-8x7b-instruct`
>
> ⚠️ **Rate Limits in Free Edition:**
> - **GPT-5.1**: Very restrictive rate limits (may fail on 10+ article batch)
> - **Recommended for Free Edition**: `databricks-gpt-oss-20b`, `databricks-meta-llama-3-3-70b-instruct`
>
> 💡 **Tip:** Check your workspace's Serving Endpoints page to see exactly which models are available in your region.

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
- **Models**: GPT-4o-mini, Claude Sonnet 4.5
- **Approach**: External API calls with secrets management
- **Available Claude Models**: Sonnet 4.5, Haiku 4.5, Opus 4.5, Opus 4.1

### Track B: Databricks Foundation Model Agent
- **Provider**: Databricks Foundation Model APIs (OpenAI OSS, Meta, Google, Anthropic)
- **Models**: Llama 3.3 70B/405B, GPT OSS 20B/120B, Claude 4.5 (paid), Gemini 3 (paid), and more
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

## Technical Implementation: MLflow Run Compatibility

This project implements a fix for [MLflow GitHub Issue #2735](https://github.com/mlflow/mlflow/issues/2735) to support **both** execution methods:

1. **MLflow Projects**: `mlflow run . -e track_b_internal -P model=databricks-gpt-oss-20b`
2. **Direct Python**: `python track_b_internal/experiment_internal.py --model databricks-gpt-oss-20b`

### The Problem

When using `mlflow run`, MLflow creates a run and sets the `MLFLOW_RUN_ID` environment variable. If your code also calls `mlflow.set_experiment()` or `mlflow.start_run()`, it can cause conflicts:

```
MlflowException: Cannot start run with ID because active run ID
does not match environment run ID
```

This is a known MLflow bug affecting projects that need to work with both execution methods.

### The Solution

We implemented a two-part fix:

#### Part 1: Smart Experiment Setup ([utils/mlflow_helpers.py](utils/mlflow_helpers.py))

```python
def setup_mlflow(experiment_name: str) -> str:
    """Setup MLflow experiment - compatible with both mlflow run and direct execution"""
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "databricks"))
    mlflow.set_registry_uri(os.getenv("MLFLOW_REGISTRY_URI", "databricks-uc"))

    # FIX for mlflow run compatibility (GitHub issue #2735):
    # If MLFLOW_RUN_ID is set, mlflow run already created a run
    # Do NOT call set_experiment() as it will cause a mismatch
    if os.getenv("MLFLOW_RUN_ID"):
        # Use the existing run's experiment
        run_id = os.getenv("MLFLOW_RUN_ID")
        client = mlflow.tracking.MlflowClient()
        run = client.get_run(run_id)
        experiment_id = run.info.experiment_id
        experiment = mlflow.get_experiment(experiment_id)
        print(f"✓ Using existing experiment: {experiment.name} (ID: {experiment_id})")
        return experiment_id

    # No mlflow run context - create or get experiment normally
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        experiment_id = mlflow.create_experiment(experiment_name)
    else:
        experiment_id = experiment.experiment_id

    mlflow.set_experiment(experiment_name)
    return experiment_id
```

**Key Insight**: When `MLFLOW_RUN_ID` environment variable is set, we skip calling `set_experiment()` and use the existing run's experiment instead.

#### Part 2: Smart Run Management (Experiment Scripts)

```python
# Check if mlflow run already created a run
if os.getenv("MLFLOW_RUN_ID"):
    # mlflow run context - use existing run
    created_run = False
    if not mlflow.active_run():
        # Activate the run that mlflow run created
        mlflow.start_run(run_id=os.getenv("MLFLOW_RUN_ID"))
    print(f"Using existing MLflow run: {mlflow.active_run().info.run_id}")
else:
    # Direct Python execution - create our own run
    mlflow.start_run(run_name=f"internal_{model}_{timestamp}")
    created_run = True
    print(f"Started MLflow run: {mlflow.active_run().info.run_id}")

try:
    # ... experiment code ...
finally:
    # Only end run if we created it (not if mlflow run created it)
    if created_run:
        mlflow.end_run()
```

**Key Insight**: Detect the execution context using `MLFLOW_RUN_ID` environment variable. When present, activate the existing run instead of creating a new one.

### Why This Matters

✅ **Flexibility** - Run experiments any way you want
✅ **Local Development** - Use direct Python for debugging
✅ **Production Deployment** - Use `mlflow run` for reproducibility
✅ **CI/CD Integration** - Both methods work in automated pipelines
✅ **Team Collaboration** - Developers can choose their preferred method

### Testing the Fix

Both methods produce identical results:

```bash
# Method 1: MLflow Projects (recommended for production)
mlflow run . -e track_b_internal -P model=databricks-gpt-oss-20b

# Method 2: Direct Python (useful for debugging)
python track_b_internal/experiment_internal.py --model databricks-gpt-oss-20b
```

Both will:
- Log to the same MLflow experiment
- Track metrics identically
- Register models to Unity Catalog with the same logic
- Follow Champion/Challenger/Candidate lifecycle

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
# Run all experiments to determine champion/challenger
make run-all

# Or run individual tracks:
# Track A (External - OpenAI)
make run-external PROVIDER=openai

# Track A (External - Anthropic)
make run-external PROVIDER=anthropic

# Track B (Internal - specific model)
make run-internal MODEL=databricks-gpt-oss-20b
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

### Phase 3: Review Models in Databricks UI 📊

**Review registered models and their aliases before promotion.**

After running experiments, review the results in Databricks:

```bash
# Navigate to Databricks UI
# 1. Go to: Machine Learning → Models
# 2. Find: main.news_classifier.news_classifier
# 3. Review model versions and their aliases:
#    - champion: Current production model
#    - challenger: Waiting for promotion (beats champion by ≥2%)
#    - candidate: Meets criteria but doesn't beat champion
#    - defeated: Previous champion that was replaced
```

**What to check:**
- Compare accuracy between champion and challenger
- Review F1 score, precision, recall metrics
- Check which provider/model each version uses
- Verify performance improvement justifies replacement

**Output:** Understanding of which models are ready for promotion

---

### Phase 4: Champion Promotion (Human-in-the-Loop) 🏆

**Promote challenger to champion after manual review.**

After running experiments, you may have a **challenger** waiting for promotion to **champion**. Use the standalone promotion workflow to review and approve:

```bash
# Review challenger and promote to champion (with approval prompt)
make promote

# What happens:
# 1. Checks if challenger exists (waiting for review)
# 2. Shows side-by-side comparison with current champion
# 3. Prompts: "Proceed? (yes/no):"
# 4. If approved:
#    - Current champion → defeated
#    - Challenger → champion
#    - Challenger alias removed
```

**Example workflow:**

```bash
# Step 1: Run experiments to create challenger
make run-all

# Step 2: Review results in Databricks UI
# Navigate to: Machine Learning → Models → main.news_classifier.news_classifier

# Step 3: Promote challenger to champion
make promote

# Output:
# ================================================================================
# [1/5] Checking for challenger waiting for review...
# ✓ Challenger found: Version 2
#   Provider: anthropic
#   Model: claude-sonnet-4-5-20250929
#   Accuracy: 100.00%
#
# [2/5] Checking current champion...
# ✓ Champion found: Version 1
#   Provider: openai
#   Model: gpt-4o-mini
#   Accuracy: 90.00%
#
# [3/5] Performance Comparison...
# Metric                   Current Champion           Challenger     Improvement
# --------------------------------------------------------------------------------
# Accuracy                          90.00%             100.00%         10.00%
#
# [4/5] Approval Gate...
# 🤔 Promote challenger to champion?
#    • Current champion (v1) will be demoted to 'defeated'
#    • Challenger (v2) will become new champion
#
# Proceed? (yes/no): yes
#
# [5/5] Executing promotion...
#    ✓ Version 1 is now defeated
#    ✓ Version 2 is now champion
#    ✓ Removed 'challenger' alias
# ================================================================================
```

**Champion Lifecycle:**

```
New Model → Passes Criteria → Beats Champion by ≥2%
                                      ↓
                                 challenger (waiting for review)
                                      ↓
                               [make promote]
                            [human approval: yes]
                                      ↓
                   ┌──────────────────┴──────────────────┐
                   ↓                                     ↓
            Old champion → defeated              challenger → champion
                                                  (challenger alias removed)
```

**Orchestration with Airflow:**

Use the MLflow entry point for workflow orchestration:

```python
# Airflow DAG example with human-in-the-loop
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor

with DAG('news_classifier_promotion', ...) as dag:

    # Task 1: Run experiments
    run_experiments = BashOperator(
        task_id='run_experiments',
        bash_command='cd /path/to/project && make run-all'
    )

    # Task 2: Promote challenger (human approval via Airflow UI)
    promote_champion = BashOperator(
        task_id='promote_champion',
        bash_command='cd /path/to/project && make promote'
    )

    run_experiments >> promote_champion
```

**Output:** Champion model promoted to production after human review

**Time:** 2-5 minutes for review and approval

---

### Phase 5: Production Deployment (MLproject) 🚀

**Deploy the champion model to production.**

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

### Prerequisites

```bash
# 1. Activate conda environment
conda activate news-classifier-agent

# 2. Ensure config/.env is set up with your Databricks credentials
# See "Setup" section below
```

### Using Make (Recommended - Uses MLflow Projects)

The Makefile commands use `mlflow run` under the hood for reproducibility:

```bash
# Track A: External Models (OpenAI/Anthropic)
make run-external                    # Default: OpenAI GPT-4o-mini
make run-external PROVIDER=anthropic # Anthropic Claude 3.5 Sonnet

# Track B: Databricks Foundation Models (Free Edition)
make run-internal                                                # Default: databricks-gpt-oss-20b
make run-internal MODEL=databricks-gpt-5-1                       # GPT-5.1
make run-internal MODEL=databricks-gpt-oss-120b                  # GPT-OSS 120B
make run-internal MODEL=databricks-llama-4-maverick              # Meta Llama 4 Maverick
make run-internal MODEL=databricks-meta-llama-3-3-70b-instruct   # Meta Llama 3.3 70B
make run-internal MODEL=databricks-meta-llama-3-1-405b-instruct  # Meta Llama 3.1 405B
make run-internal MODEL=databricks-gemma-3-12b                   # Google Gemma 3 12B
make run-internal MODEL=databricks-qwen3-next-80b-a3b-instruct   # Qwen3 Next 80B

# Run ALL experiments to determine champion/challenger
make run-all

# Promote challenger to champion (after review)
make promote
```

### Using MLflow Projects Directly

Run experiments using MLflow's project specification:

```bash
# Activate conda environment first
conda activate news-classifier-agent

# Track A: External Models
mlflow run . -e track_a_external -P provider=openai
mlflow run . -e track_a_external -P provider=anthropic

# Track B: Databricks Foundation Models
mlflow run . -e track_b_internal -P model=databricks-gpt-oss-20b
mlflow run . -e track_b_internal -P model=databricks-meta-llama-3-3-70b-instruct
mlflow run . -e track_b_internal -P model=databricks-meta-llama-3-1-405b-instruct

# Run both tracks
mlflow run . -e main -P track=both
```

### Using Python Directly (Alternative Method)

```bash
# Activate conda environment first
conda activate news-classifier-agent

# Track A: External Models
python track_a_external/experiment_external.py --provider openai
python track_a_external/experiment_external.py --provider anthropic

# Track B: Databricks Foundation Models (Free Edition)
python track_b_internal/experiment_internal.py --model databricks-gpt-oss-20b
python track_b_internal/experiment_internal.py --model databricks-gpt-oss-120b
python track_b_internal/experiment_internal.py --model databricks-meta-llama-3-3-70b-instruct
python track_b_internal/experiment_internal.py --model databricks-meta-llama-3-1-405b-instruct

# Run both tracks
python main.py --track both
```

### Production Model Registration Options

The experiments support 3 production promotion patterns:

```bash
# Option 1: Manual approval (requires human approval before registering)
python track_b_internal/experiment_internal.py --model databricks-gpt-5.1 --require-approval

# Option 2: Automated gating (default - compares to Champion, registers as Challenger/Candidate)
python track_b_internal/experiment_internal.py --model databricks-gpt-5.1

# Option 3: Skip registration entirely
python track_b_internal/experiment_internal.py --model databricks-gpt-5.1 --no-register
```

### Available Models

**Track A - External Models:**
- `openai` → GPT-4o-mini (default)
- `anthropic` → Claude Sonnet 4.5 (default, latest as of Sept 2025)

**Available Anthropic Claude Models (via Anthropic API):**
- **Claude Sonnet 4.5**: `claude-sonnet-4-5-20250929` - Most balanced, recommended (default)
- **Claude Haiku 4.5**: `claude-haiku-4-5-20251001` - Fastest, lowest cost
- **Claude Opus 4.5**: `claude-opus-4-5-20251101` - Maximum intelligence
- **Claude Opus 4.1**: `claude-opus-4-1-20250805` - Specialized reasoning

> 📝 **Note**: Track A uses the Anthropic API directly (external), not Databricks Foundation Model API

**Track B - Databricks Foundation Models:**

**✅ Available in Free Edition:**
- **OpenAI**: `databricks-gpt-5-1` ⚠️ **Heavy rate limits**, `databricks-gpt-oss-120b`, `databricks-gpt-oss-20b` ✅ **Recommended (default)**
- **Meta Llama**: `databricks-llama-4-maverick`, `databricks-meta-llama-3-3-70b-instruct` ✅ **Recommended**, `databricks-meta-llama-3-1-405b-instruct`, `databricks-meta-llama-3-1-8b-instruct`
- **Google**: `databricks-gemma-3-12b`
- **Alibaba**: `databricks-qwen3-next-80b-a3b-instruct`

**❌ NOT Available in Free Edition:**
- **Anthropic**: Claude models (requires paid tier)
- **Google**: Gemini 2.5/3 Pro/Flash models

> ⚠️ **RETIRED (April 2025):** `databricks-dbrx-instruct`, `databricks-mixtral-8x7b-instruct`
>
> ⚠️ **Rate Limits:** GPT-5.1 has restrictive limits in Free Edition. Use `databricks-gpt-oss-20b` or `databricks-meta-llama-3-3-70b-instruct` for reliable experiments.
>
> 💡 **Tip:** Check your workspace's Serving Endpoints page to confirm availability. Navigate to: **Compute** → **Serving** in Databricks UI.
> ```bash
> make list-models  # Lists available Foundation Model endpoints
> ```

### Using MLflow Run (Alternative)

✅ **`mlflow run .` IS supported** - The experiments automatically detect and use existing runs.

```bash
# Activate conda environment first
conda activate news-classifier-agent

# Run Track A (External Model)
mlflow run . -e track_a_external -P provider=openai
mlflow run . -e track_a_external -P provider=anthropic

# Run Track B (Internal Model)
mlflow run . -e track_b_internal -P model=databricks-gpt-oss-20b
mlflow run . -e track_b_internal -P model=databricks-meta-llama-3-3-70b-instruct

# Run both tracks
mlflow run . -e main -P track=both
```

**How it works:**
- Scripts check for active runs using `mlflow.active_run()`
- If `mlflow run` created a run → uses it
- If no active run → creates its own (for direct Python execution)
- Both approaches work seamlessly!

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

## Production Model Lifecycle

This project implements a **2-phase production lifecycle** for models:

### Production Criteria

All models must meet minimum criteria before registration:

Before any model reaches production, it must pass validation gates defined in [utils/production_criteria.py](utils/production_criteria.py):

| Criterion | Threshold | Why |
|-----------|-----------|-----|
| **Accuracy** | ≥ 90% | Minimum acceptable performance |
| **F1 Score** | ≥ 0.85 | Balanced precision/recall |
| **Precision** | ≥ 0.80 | Low false positive rate |
| **Recall** | ≥ 0.80 | Low false negative rate |
| **Beats Champion** | +2% accuracy | Must improve on current production |

---

## Phase 1: Registration (Creating Challenger/Candidate)

**Two options for gating whether models get registered as champion/challenger/candidate:**

### Registration Option 1: Manual Approval Gate

**Use case:** Critical systems - human approves each registration

After experiment completes, require manual approval before registering to Unity Catalog:

```bash
# Run with manual approval gate
python track_b_internal/experiment_internal.py \
  --model databricks-gpt-5-1 \
  --require-approval
```

**What happens:**
1. Experiment runs and logs metrics
2. System evaluates production criteria
3. Determines alias (champion/challenger/candidate) based on performance
4. **Prompts for manual approval**: `Register to Unity Catalog? (yes/no):`
5. Only registers with determined alias if you type `yes`

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

### Registration Option 2: Automated Gating (DEFAULT)

**Use case:** Fast iteration - automatically registers as champion/challenger/candidate

Models are automatically registered with appropriate alias based on performance:

```bash
# Run with automated gating (default)
python track_b_internal/experiment_internal.py \
  --model databricks-gpt-oss-20b
```

**What happens:**
1. Experiment runs and logs metrics
2. System evaluates production criteria
3. Determines alias (champion/challenger/candidate) based on performance
4. **Always registers** to Unity Catalog with determined alias
5. Tags model with `production_ready=true` or `production_ready=false`

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

---

## Phase 2: Promotion (Replacing Champion)

**Human-in-the-loop approval for promoting challenger → champion**

After a challenger has been registered (via Phase 1), promote it to champion with manual approval:

```bash
# Promote challenger to champion (interactive approval)
make promote

# What happens:
# 1. Checks if challenger exists (waiting for review)
# 2. Shows side-by-side comparison with current champion
# 3. Prompts: "Proceed? (yes/no):"
# 4. If approved:
#    - Current champion → defeated
#    - Challenger → champion
#    - Challenger alias removed
```

**Champion Lifecycle:**
1. ✅ **First model** - Automatically becomes champion
2. ✅ **Better model** - Becomes challenger if beats champion by ≥2%
3. ✅ **Manual promotion** - Human approves challenger → champion
4. ✅ **Previous champion** - Demoted to defeated

**Example workflow:**
```bash
# Step 1: Run experiments to create challenger
make run-all

# Step 2: Review results in Databricks UI
# Navigate to: Machine Learning → Models → main.news_classifier.news_classifier

# Step 3: Promote challenger to champion
make promote

# Output:
# ================================================================================
# [1/5] Checking for challenger waiting for review...
# ✓ Challenger found: Version 2
#   Provider: anthropic
#   Model: claude-sonnet-4-5-20250929
#   Accuracy: 100.00%
#   F1 Score: 1.000
#
# [2/5] Checking current champion...
# ✓ Champion found: Version 1
#   Provider: openai
#   Model: gpt-4o-mini
#   Accuracy: 90.00%
#   F1 Score: 0.860
#
# [3/5] Performance Comparison...
# Metric                   Current Champion           Challenger     Improvement
# --------------------------------------------------------------------------------
# Accuracy                          90.00%             100.00%         10.00%
# F1 Score                            0.860                1.000
#
# [4/5] Approval Gate...
# 🤔 Promote challenger to champion?
#    • Current champion (v1) will be demoted to 'defeated'
#    • Challenger (v2) will become new champion
#
# Proceed? (yes/no): yes
#
# [5/5] Executing promotion...
#    • Demoting champion v1 → defeated...
#    ✓ Version 1 is now defeated
#    • Promoting challenger v2 → champion...
#    ✓ Version 2 is now champion
#    ✓ Removed 'challenger' alias
#
# ✅ PROMOTION SUCCESSFUL
# 🏆 New Champion: Version 2
#    Provider: anthropic
#    Model: claude-sonnet-4-5-20250929
#    Accuracy: 100.00%
#    F1 Score: 1.000
#
# ⚔️  Defeated: Version 1
#    Provider: openai
#    Model: gpt-4o-mini
#    Accuracy: 90.00%
#
# To load new champion in production:
#   model = mlflow.pyfunc.load_model('models:/main.news_classifier.news_classifier@champion')
# ================================================================================
```

### Unity Catalog Aliases

Models use lowercase aliases to indicate production stages:

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()
model_name = "main.news_classifier.news_classifier"

# Production lifecycle aliases (automatically assigned)
# - champion: Current production model
# - challenger: Candidate for replacing champion (beats by ≥2%)
# - candidate: Meets criteria but doesn't beat champion
# - defeated: Previous champion that was replaced

# Load specific stage
champion_model = mlflow.pyfunc.load_model(f"models:/{model_name}@champion")
challenger_model = mlflow.pyfunc.load_model(f"models:/{model_name}@challenger")
candidate_model = mlflow.pyfunc.load_model(f"models:/{model_name}@candidate")
```

---

### Summary: 2-Phase Production Lifecycle

| Phase | Options | When to Use | Automation | Safety |
|-------|---------|-------------|------------|--------|
| **Phase 1: REGISTRATION** | **Option 1: Manual Gate**<br>`--require-approval` | Critical systems - approve each registration | ❌ Manual approval | 🔒 Highest |
| **Phase 1: REGISTRATION** | **Option 2: Automated** (DEFAULT)<br>`make run-all` | Fast iteration - automatic registration | ✅ Full automation | ⚠️ Medium |
| **Phase 2: PROMOTION** | **Human-in-the-loop**<br>`make promote` | Replace champion with approved challenger | 🔄 Interactive approval | 🔒 High |

**Key Points:**
- **Phase 1** has 2 options for gating challenger/candidate REGISTRATION
- **Phase 2** has 1 process for promoting challenger → champion
- Most teams use **Option 2** (automated) + **Phase 2** (manual promotion)

### Duplicate Performance Detection

**NEW FEATURE**: The system automatically prevents registering models with identical performance:

- Before registration, checks if any existing model version has the same accuracy and F1 score (within 0.001 tolerance)
- If duplicate found, skips registration and displays which version already has that performance
- Prevents unnecessary model versions in Unity Catalog

**Example:**
```bash
# If model achieves 100% accuracy (same as existing v2)
⚠️  Model with identical performance already exists:
   Version 2: anthropic/claude-sonnet-4-5-20250929
   Accuracy: 100.00%
   Alias: challenger
   ❌ Will NOT register duplicate model to Unity Catalog
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

## How MLflow Run Support Works {#mlflow-run-explanation}

### Automatic Run Detection

This project supports **BOTH** `mlflow run` and direct Python execution through automatic run detection:

```python
# Check if mlflow run already created a run for us
active_run = mlflow.active_run()
created_run = False

if active_run:
    # Use existing run from `mlflow run`
    run = active_run
    print(f"Using existing MLflow run: {run.info.run_id}")
else:
    # Create our own run (for direct Python execution)
    run = mlflow.start_run(run_name=f"internal_{model}_{timestamp}")
    created_run = True
    print(f"Started MLflow run: {run.info.run_id}")

try:
    # ... experiment code ...
finally:
    # Only end run if we created it
    if created_run:
        mlflow.end_run()
```

### The Two Approaches

**Approach 1: Direct Python Execution**
```bash
# You control the entire run lifecycle
python track_b_internal/experiment_internal.py --model databricks-gpt-oss-20b

# ✅ Script creates run with custom name
# ✅ Full control over run naming
# ✅ Better for learning/debugging
```

**Approach 2: MLflow Run**
```bash
# MLflow controls the run lifecycle
mlflow run . -e track_b_internal -P model=databricks-gpt-oss-20b

# ✅ Script detects and uses MLflow's run
# ✅ Better for packaged/remote projects
# ✅ Standard MLflow workflow
```

### When to Use Each

| Use `mlflow run` | Use Direct Python |
|------------------|-------------------|
| Running remote git repos | Local development |
| Deploying packaged projects | Learning/debugging |
| CI/CD pipelines | Custom run naming |
| Team standardization | Quick iteration |

**Both work perfectly!** Choose based on your workflow preference.

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
