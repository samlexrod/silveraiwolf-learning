# Exploration Notebooks

This directory contains Jupyter notebooks for **exploratory data analysis** and **prototyping** before running formal MLflow experiments.

## Philosophy: Notebooks → MLproject

```
┌─────────────────────────────────────────────────────────────┐
│                   ML Development Workflow                     │
└─────────────────────────────────────────────────────────────┘

1. 📓 Notebooks (Exploration)
   ├── Understand the data
   ├── Test different prompts
   ├── Quick prototypes
   └── Validate approach
              ↓
2. 🔬 MLproject (Experimentation)
   ├── Formal experiments
   ├── MLflow tracking
   ├── Model comparison
   └── Reproducible results
              ↓
3. 🚀 MLproject (Production)
   ├── Deploy winning model
   ├── Automated retraining
   └── Model serving
```

## Available Notebooks

### [01_eda_news_classifier.ipynb](01_eda_news_classifier.ipynb)

**Purpose:** Initial exploration of the news classification task

**What it covers:**
1. **Data Exploration**
   - Load and inspect sample news articles
   - Visualize category and sentiment distributions
   - Analyze article lengths and characteristics

2. **Prompt Prototyping**
   - Test zero-shot classification prompts
   - Experiment with different prompt formats
   - Validate prompt structure

3. **Model Prototypes**
   - Quick tests with OpenAI (external)
   - Quick tests with Databricks DBRX (internal)
   - Validate approach before formal experiments

4. **Insights**
   - Document what works
   - Identify potential issues
   - Plan formal experiments

**When to use this notebook:**
- ✅ First time exploring the dataset
- ✅ Testing new prompt ideas
- ✅ Quick validation before formal experiments
- ✅ Teaching/presenting the approach

**When NOT to use this notebook:**
- ❌ Running formal experiments (use MLproject)
- ❌ Tracking metrics (use MLproject)
- ❌ Comparing models (use MLproject)
- ❌ Production deployment (use MLproject)

## Running the Notebook

### Option 1: Jupyter Lab (Local)

```bash
# Activate conda environment
conda activate news-classifier-agent

# Start Jupyter Lab
jupyter lab

# Navigate to notebooks/01_eda_news_classifier.ipynb
```

### Option 2: Databricks Notebooks

1. Go to your Databricks workspace
2. Navigate to **Workspace** → **Users** → your email
3. Click **Import**
4. Upload `01_eda_news_classifier.ipynb`
5. Attach to a cluster
6. Run cells

**Tip:** You can import the entire `notebooks/` directory to Databricks.

### Option 3: VS Code

```bash
# Install Jupyter extension in VS Code
# Open the notebook file
# Select kernel: news-classifier-agent
# Run cells interactively
```

## After EDA: Next Steps

Once you've completed the exploratory analysis:

### 1. Run Formal Experiments (MLproject)

```bash
# Track A: External Model
make run-external PROVIDER=openai

# Track B: Internal Model
make run-internal MODEL=databricks-dbrx-instruct

# Both tracks for comparison
make run-both
```

### 2. View Results in Databricks

Navigate to **Machine Learning** → **Experiments** to compare:
- Accuracy metrics
- Confusion matrices
- Model parameters
- Cost analysis

### 3. Optional: Create Analysis Notebook

Create `02_analyze_results.ipynb` to:
- Load MLflow experiment results
- Visualize Track A vs Track B comparison
- Generate final report
- Document insights

## Best Practices

### ✅ DO Use Notebooks For:
- Data exploration and visualization
- Quick prototyping and testing
- Iterating on prompts
- Understanding the problem
- Presenting findings

### ❌ DON'T Use Notebooks For:
- Production experiments
- Model training pipelines
- Automated workflows
- Final model deployment
- Critical reproducibility

## Example Workflow

### Day 1: Exploration (Notebook)
```python
# 01_eda_news_classifier.ipynb
# - Explore 10 sample articles
# - Test 3 different prompts
# - Quick prototype with OpenAI
# Result: Zero-shot works! 90% accuracy on 3 samples
```

### Day 2: Experimentation (MLproject)
```bash
# Run formal experiments
make run-both

# Result: Both tracks tracked in MLflow
# - Track A (OpenAI): 92% accuracy, $0.05/article
# - Track B (DBRX): 88% accuracy, $0.02/article
```

### Day 3: Analysis (Notebook)
```python
# 02_analyze_results.ipynb
# - Load MLflow results
# - Compare Track A vs B
# - Visualize confusion matrices
# Decision: Use Track B (DBRX) - good accuracy, lower cost
```

### Day 4: Production (MLproject)
```bash
# Deploy Track B model
databricks jobs create --json '{
  "name": "News Classifier - Production",
  "mlflow_project": {"entry_point": "track_b_internal"}
}'
```

## Why This Separation Matters

| Aspect | Notebook | MLproject |
|--------|----------|-----------|
| **Speed** | ✅ Fast iteration | Slower (reproducibility overhead) |
| **Tracking** | ❌ Manual | ✅ Automatic |
| **Reproducibility** | ❌ Poor | ✅ Excellent |
| **Collaboration** | ⚠️ Okay for sharing results | ✅ Great for team work |
| **Production** | ❌ Requires rewrite | ✅ Deploy directly |

**Use both together for maximum productivity!**

## Contributing Notebooks

When adding new notebooks:

1. **Naming Convention:** `XX_descriptive_name.ipynb`
   - `01_` - Initial EDA
   - `02_` - Analysis of results
   - `03_` - Advanced visualizations
   - etc.

2. **Structure:**
   - Clear markdown headers
   - Explain purpose upfront
   - Document insights
   - Link to next steps

3. **Keep Notebooks Clean:**
   - Clear all outputs before committing
   - Remove unused cells
   - Add meaningful comments
   - Include summary at end

4. **Git Best Practice:**
   ```bash
   # Clear outputs before committing
   jupyter nbconvert --clear-output --inplace *.ipynb

   # Then commit
   git add notebooks/
   git commit -m "Add EDA notebook"
   ```

## Additional Resources

- [Jupyter Documentation](https://jupyter.org/documentation)
- [Databricks Notebooks Guide](https://docs.databricks.com/notebooks/index.html)
- [Why MLproject > Notebooks](../docs/notebooks-vs-mlproject.md)