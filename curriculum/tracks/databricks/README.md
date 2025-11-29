# Databricks Lakehouse Track

Master the Data Intelligence Platform. From Unity Catalog to Mosaic AI, we build production-grade agents where the data lives.

## Overview

This track focuses on building AI agents and ML systems using the **Databricks Lakehouse Platform**, integrating:

- **Unity Catalog** - Data governance and model registry
- **MLflow** - Experiment tracking and model management
- **Databricks Foundation Models** - Internal LLMs (DBRX, Llama-3)
- **External LLM Integration** - OpenAI, Anthropic with secret management
- **Delta Lake** - Data storage and versioning
- **Model Serving** - Production deployment

## Track Philosophy

### Learning Approach

```
┌─────────────────────────────────────────────────────────────┐
│              Professional ML Engineering Workflow             │
└─────────────────────────────────────────────────────────────┘

1. 📓 Notebooks (Exploration)
   ├── Understand the problem
   ├── Explore data
   ├── Prototype solutions
   └── Validate approach
          ↓
2. 🔬 MLproject (Experimentation)
   ├── Formal experiments
   ├── MLflow tracking
   ├── Model comparison
   └── Reproducible results
          ↓
3. 🚀 MLproject (Production)
   ├── Deploy models
   ├── Automated workflows
   └── Monitor performance
```

### Why This Track?

- ✅ **Industry-Standard Tools** - MLflow, Unity Catalog, Delta Lake
- ✅ **Production-Ready Patterns** - Not just tutorials, real engineering
- ✅ **Cost-Aware** - Compare external vs internal models
- ✅ **Governance-First** - Security, secrets, permissions
- ✅ **End-to-End** - From EDA to production deployment

## Projects

### [Project 01: News Classifier Agent](project_01_news_classifier/)

**Goal:** Build a 2-way track experiment comparing External vs Internal LLMs for news classification using zero-shot learning.

**What You'll Learn:**
- ✅ MLflow experiment tracking
- ✅ MLproject with conda environments
- ✅ ResponsesAgent for model logging
- ✅ Unity Catalog model registration
- ✅ Databricks Secrets management
- ✅ External API integration (OpenAI/Anthropic)
- ✅ Databricks Foundation Model APIs (DBRX/Llama-3)
- ✅ Zero-shot classification with LLMs
- ✅ Why MLproject > Jupyter notebooks for production

**Tech Stack:**
- MLflow 3.1+
- Databricks SDK
- OpenAI / Anthropic APIs
- Databricks Foundation Models
- Unity Catalog
- Python 3.10

**Time:** 2-4 hours

**Status:** ✅ Complete

---

### Project 02: [Coming Soon]

**Goal:** TBD - Next project in the Databricks track

Ideas:
- RAG system with Vector Search
- Fine-tuning with Databricks
- Multi-agent orchestration
- Real-time feature engineering

---

### Project 03: [Coming Soon]

**Goal:** TBD

---

## Track Structure

```
databricks/
├── project_01_news_classifier/      # News classification with LLMs
│   ├── MLproject                    # MLflow project definition
│   ├── conda.yaml                   # Reproducible environment
│   ├── notebooks/                   # Jupyter notebooks for EDA
│   ├── track_a_external/            # External model experiments
│   ├── track_b_internal/            # Internal model experiments
│   ├── config/                      # Configuration files
│   ├── data/                        # Sample datasets
│   ├── utils/                       # Shared utilities
│   ├── docs/                        # Project documentation
│   └── README.md                    # Project-specific guide
│
├── project_02_*/                    # Future project
├── project_03_*/                    # Future project
└── README.md                        # This file (track overview)
```

## Prerequisites

### Required Knowledge

- Python programming (intermediate)
- Basic ML concepts (classification, metrics)
- Git basics
- Command line comfort

### Required Tools

1. **Databricks Workspace**
   - Free trial available: https://databricks.com/try-databricks
   - AWS, Azure, or GCP

2. **Local Development**
   - Python 3.10+
   - Conda or Miniconda
   - Git
   - Jupyter (optional, for EDA)

3. **API Keys (Project-Specific)**
   - OpenAI API key (for Project 01 Track A)
   - Anthropic API key (for Project 01 Track A, optional)

### Recommended Background

- Complete the **Foundation Track** first (optional but helpful)
- Familiarity with Jupyter notebooks
- Basic understanding of LLMs and prompting

## Getting Started

### 1. Set Up Databricks

1. Create a Databricks account (free trial available)
2. Create a workspace (AWS/Azure/GCP)
3. Generate a personal access token:
   - User Settings → Access Tokens → Generate New Token

### 2. Clone the Repository

```bash
cd /path/to/your/workspace
git clone <repository-url>
cd curriculum/tracks/databricks
```

### 3. Start with Project 01

```bash
cd project_01_news_classifier
conda env create -f conda.yaml
conda activate news-classifier-agent

# Configure Databricks credentials
cp config/.env.example config/.env
# Edit config/.env with your credentials

# Start with EDA
jupyter lab
# Open: notebooks/01_eda_news_classifier.ipynb
```

## Learning Path

### Recommended Order

1. **Project 01: News Classifier Agent** (Start Here)
   - Foundation of MLflow experimentation
   - Learn MLproject vs notebooks
   - Master Unity Catalog basics
   - Compare external vs internal models

2. **Project 02: [TBD]**
   - Build on Project 01 knowledge
   - Advanced MLflow features
   - More complex architectures

3. **Project 03: [TBD]**
   - Production deployment patterns
   - Advanced governance
   - Cost optimization

### Time Commitment

- **Project 01:** 2-4 hours
- **Project 02:** TBD
- **Project 03:** TBD

**Total Track Time:** ~10-15 hours (estimated)

## Key Concepts Covered

### Databricks Platform

- ✅ Unity Catalog (governance, model registry)
- ✅ Databricks Workflows (jobs, scheduling)
- ✅ Databricks Secrets (API key management)
- ✅ Foundation Model APIs (DBRX, Llama-3)
- ✅ Model Serving (deployment)
- ✅ Delta Lake (data storage)

### MLflow

- ✅ Experiment tracking
- ✅ MLproject structure
- ✅ ResponsesAgent for GenAI
- ✅ Model registry
- ✅ Model versioning
- ✅ Artifacts and metrics

### Engineering Best Practices

- ✅ Reproducible environments (Conda)
- ✅ Version control (Git)
- ✅ Modular code structure
- ✅ Automated workflows (Make, MLflow)
- ✅ Professional experimentation
- ✅ Production-ready code

## Common Patterns Across Projects

### Project Template Structure

Every project follows a consistent pattern:

```
project_XX_name/
├── MLproject                    # Entry points for experiments
├── conda.yaml                   # Environment specification
├── notebooks/                   # EDA and analysis
│   ├── 01_eda_*.ipynb
│   └── README.md
├── config/                      # Configuration
│   └── .env.example
├── data/                        # Sample data
├── utils/                       # Shared utilities
├── docs/                        # Documentation
├── main.py                      # Main entry point
├── Makefile                     # Quick commands
└── README.md                    # Project guide
```

### Standard Workflow

1. **Exploration** → Jupyter notebooks
2. **Experimentation** → MLproject with tracking
3. **Analysis** → Jupyter notebooks (optional)
4. **Production** → MLproject deployment

## Resources

### Databricks Documentation

- [Databricks Documentation](https://docs.databricks.com/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Unity Catalog Guide](https://docs.databricks.com/data-governance/unity-catalog/index.html)
- [Foundation Model APIs](https://docs.databricks.com/machine-learning/foundation-models/index.html)

### Community

- [Databricks Community](https://community.databricks.com/)
- [MLflow GitHub](https://github.com/mlflow/mlflow)
- [Databricks Academy](https://www.databricks.com/learn/training)

## Track Completion

### What You'll Have Built

By completing this track, you will have:

1. ✅ Production-ready ML experiments with MLflow
2. ✅ Models registered in Unity Catalog
3. ✅ Experience with both external and internal LLMs
4. ✅ Automated experiment workflows
5. ✅ Portfolio-worthy Databricks projects
6. ✅ Industry-standard ML engineering skills

### Next Steps After This Track

- **Advanced Databricks** - RAG, fine-tuning, multi-agent systems
- **LangGraph Track** - Complex agent orchestration
- **Production Deployment** - Scale to real workloads
- **Contribute** - Add new projects to this track!

## Contributing

Want to add a new project to this track?

1. Follow the standard project template structure
2. Include comprehensive README
3. Add EDA notebooks for exploration
4. Use MLproject for experiments
5. Document learnings and best practices
6. Submit a pull request!

## License

Part of the SilverAIWolf curriculum.

## Support

For questions or issues:
1. Check project-specific READMEs
2. Review Databricks documentation
3. Ask in the community forums

---

**Ready to start?** → [Project 01: News Classifier Agent](project_01_news_classifier/)