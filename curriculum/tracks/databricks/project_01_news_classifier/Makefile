# Makefile for News Classifier Agent MLflow Experiments

.PHONY: help install activate setup test-connection notebook run-external run-internal run-both compare clean

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
	@echo ""
	@echo "Utility commands:"
	@echo "  make compare          - Compare results from both tracks"
	@echo "  make clean            - Clean up temporary files"
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

# Run Track A (External Model) - runs Python script directly
PROVIDER ?= openai
run-external:
	@echo "Running Track A: External Model ($(PROVIDER))..."
	@echo "⚠️  Note: This requires 'conda activate news-classifier-agent' first"
	@echo ""
	@python track_a_external/experiment_external.py --provider $(PROVIDER) || \
		(echo "" && echo "❌ Experiment failed. Did you activate the environment?" && echo "   Run: conda activate news-classifier-agent" && exit 1)

# Run Track B (Internal Model) - runs Python script directly
MODEL ?= databricks-gpt-oss-20b
run-internal:
	@echo "Running Track B: Internal Model ($(MODEL))..."
	@echo "⚠️  Note: This requires 'conda activate news-classifier-agent' first"
	@echo ""
	@python track_b_internal/experiment_internal.py --model $(MODEL) || \
		(echo "" && echo "❌ Experiment failed. Did you activate the environment?" && echo "   Run: conda activate news-classifier-agent" && exit 1)

# Run both tracks sequentially
run-both:
	@echo "Running BOTH tracks sequentially..."
	@echo "⚠️  Note: This requires 'conda activate news-classifier-agent' first"
	@echo ""
	@python main.py --track both || \
		(echo "" && echo "❌ Experiment failed. Did you activate the environment?" && echo "   Run: conda activate news-classifier-agent" && exit 1)

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