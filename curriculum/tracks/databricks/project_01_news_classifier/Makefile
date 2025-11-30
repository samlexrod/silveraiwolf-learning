# Makefile for News Classifier Agent MLflow Experiments

.PHONY: help install activate setup test-connection notebook run-external run-internal run-both run-all promote promote-auto compare clean clean-databricks

# Default target
help:
	@echo "News Classifier Agent - MLflow Experiments"
	@echo ""
	@echo "Setup commands:"
	@echo "  make install          - Install conda environment"
	@echo "  make activate         - Show how to activate conda environment"
	@echo "  make setup            - Setup environment (copy .env.example)"
	@echo "  make test-connection  - Test Databricks connection (requires activated env)"
	@echo "  make notebook         - Launch JupyterLab for EDA notebooks (requires activated env)"
	@echo ""
	@echo "Experiment commands:"
	@echo "  make run-external     - Run Track A (External Model) via MLflow"
	@echo "  make run-internal     - Run Track B (Internal Model) via MLflow"
	@echo "  make run-both         - Run both tracks sequentially via MLflow"
	@echo "  make run-all          - Run ALL models to determine Champion 🏆"
	@echo ""
	@echo "Production commands:"
	@echo "  make promote          - Promote challenger to champion (interactive approval)"
	@echo ""
	@echo "Utility commands:"
	@echo "  make compare          - Compare results from both tracks"
	@echo "  make clean            - Clean up temporary files"
	@echo "  make clean-databricks - Delete ALL models and experiments from Databricks"
	@echo ""
	@echo "Track A Examples:"
	@echo "  make run-external PROVIDER=openai"
	@echo "  make run-external PROVIDER=anthropic"
	@echo ""
	@echo "Track B Examples:"
	@echo "  make run-internal MODEL=databricks-dbrx-instruct"
	@echo "  make run-internal MODEL=databricks-meta-llama-3-70b-instruct"

# Install conda environment
install:
	@echo "Creating conda environment from conda.yaml..."
	conda env create -f conda.yaml || conda env update -f conda.yaml
	@echo "✓ Conda environment created/updated: news-classifier-agent"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Activate environment: conda activate news-classifier-agent"
	@echo "  2. Setup credentials:    make setup"
	@echo "  3. Test connection:      make test-connection"

# Show how to activate environment
activate:
	@echo "To activate the conda environment, run:"
	@echo ""
	@echo "  conda activate news-classifier-agent"
	@echo ""
	@echo "Commands that REQUIRE activation:"
	@echo "  - make test-connection"
	@echo "  - make notebook"
	@echo "  - make run-external"
	@echo "  - make run-internal"
	@echo "  - make run-both"

# Setup environment file
setup:
	@if [ ! -f config/.env ]; then \
		echo "Creating config/.env from template..."; \
		cp config/.env.example config/.env; \
		echo "✓ Created config/.env - Please edit with your credentials"; \
	else \
		echo "config/.env already exists"; \
	fi

# Test Databricks connection (requires activated environment)
test-connection:
	@echo "Testing Databricks connection..."
	@echo "⚠️  Note: This requires 'conda activate news-classifier-agent' first"
	@echo ""
	@python -c "from dotenv import load_dotenv; load_dotenv('config/.env'); from utils.databricks_auth import verify_databricks_connection; verify_databricks_connection()" || \
		(echo "" && echo "❌ Connection test failed. Did you activate the environment?" && echo "   Run: conda activate news-classifier-agent" && exit 1)

# Launch JupyterLab (requires activated environment)
notebook:
	@echo "Launching JupyterLab..."
	@echo "⚠️  Note: This requires 'conda activate news-classifier-agent' first"
	@echo ""
	@echo "Opening notebooks directory: ./notebooks"
	@echo "Press Ctrl+C to stop JupyterLab"
	@echo ""
	@jupyter lab --notebook-dir=notebooks || \
		(echo "" && echo "❌ JupyterLab failed to start. Did you activate the environment?" && echo "   Run: conda activate news-classifier-agent" && exit 1)

# Run Track A (External Model) - uses mlflow run
PROVIDER ?= openai
run-external:
	@echo "Running Track A: External Model ($(PROVIDER)) via MLflow..."
	@echo "⚠️  Note: This requires 'conda activate news-classifier-agent' first"
	@echo ""
	@export $$(grep -v '^#' config/.env | grep -v '^$$' | sed 's/#.*//' | xargs) && \
		EXPERIMENT_NAME=$${MLFLOW_EXPERIMENT_NAME_EXTERNAL:-/Users/default/news-classifier-external} && \
		RUN_NAME="external_$(PROVIDER)_$$(date +%Y%m%d_%H%M%S)" && \
		mlflow run . -e track_a_external -P provider=$(PROVIDER) --experiment-name "$$EXPERIMENT_NAME" --run-name "$$RUN_NAME" || \
		(echo "" && echo "❌ Experiment failed. Did you activate the environment?" && echo "   Run: conda activate news-classifier-agent" && exit 1)

# Run Track B (Internal Model) - uses mlflow run
MODEL ?= databricks-gpt-oss-20b
run-internal:
	@echo "Running Track B: Internal Model ($(MODEL)) via MLflow..."
	@echo "⚠️  Note: This requires 'conda activate news-classifier-agent' first"
	@echo ""
	@export $$(grep -v '^#' config/.env | grep -v '^$$' | sed 's/#.*//' | xargs) && \
		EXPERIMENT_NAME=$${MLFLOW_EXPERIMENT_NAME_INTERNAL:-/Users/default/news-classifier-internal} && \
		MODEL_SHORT=$$(echo $(MODEL) | sed 's/databricks-//') && \
		RUN_NAME="internal_$${MODEL_SHORT}_$$(date +%Y%m%d_%H%M%S)" && \
		mlflow run . -e track_b_internal -P model=$(MODEL) --experiment-name "$$EXPERIMENT_NAME" --run-name "$$RUN_NAME" || \
		(echo "" && echo "❌ Experiment failed. Did you activate the environment?" && echo "   Run: conda activate news-classifier-agent" && exit 1)

# Run both tracks sequentially - uses mlflow run
run-both:
	@echo "Running BOTH tracks sequentially via MLflow..."
	@echo "⚠️  Note: This requires 'conda activate news-classifier-agent' first"
	@echo ""
	@mlflow run . -e main -P track=both || \
		(echo "" && echo "❌ Experiment failed. Did you activate the environment?" && echo "   Run: conda activate news-classifier-agent" && exit 1)

# Run ALL models to determine the Champion
run-all:
	@echo "Running all experiments via Python orchestrator..."
	@echo "⚠️  Note: This requires 'conda activate news-classifier-agent' first"
	@echo ""
	@export $(grep -v '^#' config/.env | grep -v '^$' | sed 's/#.*//' | xargs) && \
		python run_all_experiments.py || \
		(echo "" && echo "❌ Experiments failed. Did you activate the environment?" && echo "   Run: conda activate news-classifier-agent" && exit 1)

# Promote Challenger to Champion (Option 3) - Interactive approval
promote:
	@echo "Promoting challenger to champion (interactive approval)..."
	@echo "⚠️  Note: This requires 'conda activate news-classifier-agent' first"
	@echo ""
	@export $$(grep -v '^#' config/.env | grep -v '^$$' | sed 's/#.*//' | xargs) && \
		python scripts/promote_to_production.py || \
		(echo "" && echo "❌ Promotion failed. Did you activate the environment?" && echo "   Run: conda activate news-classifier-agent" && exit 1)

# Auto-approve promotion (for automated workflows like Airflow)
promote-auto:
	@echo "Promoting challenger to champion (auto-approve)..."
	@echo "⚠️  Note: This requires 'conda activate news-classifier-agent' first"
	@echo ""
	@export $$(grep -v '^#' config/.env | grep -v '^$$' | sed 's/#.*//' | xargs) && \
		python scripts/promote_to_production.py --auto-approve || \
		(echo "" && echo "❌ Promotion failed. Did you activate the environment?" && echo "   Run: conda activate news-classifier-agent" && exit 1)

# Compare results
compare:
	@echo "Comparing experiment results..."
	@echo "Please check Databricks MLflow UI to compare runs side-by-side"
	@echo ""
	@echo "Track A: $${MLFLOW_EXPERIMENT_NAME_EXTERNAL:-/Users/default/news-classifier-external}"
	@echo "Track B: $${MLFLOW_EXPERIMENT_NAME_INTERNAL:-/Users/default/news-classifier-internal}"

# Clean temporary files
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	rm -rf mlruns/ mlartifacts/ 2>/dev/null || true
	@echo "✓ Cleaned up temporary files"

# Clean Databricks models and experiments (DESTRUCTIVE!)
clean-databricks:
	@echo "⚠️  WARNING: This will DELETE ALL registered models and experiments!"
	@echo ""
	@export $(grep -v '^#' config/.env | grep -v '^$' | sed 's/#.*//' | xargs) && \
		python cleanup.py