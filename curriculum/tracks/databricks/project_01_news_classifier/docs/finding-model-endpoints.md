# Finding Databricks Foundation Model Endpoints

The Foundation Model API endpoint names vary by Databricks workspace and availability. Here's how to find the correct endpoint names for your workspace:

## Option 1: Via Databricks UI

1. Go to your Databricks workspace
2. Navigate to **Machine Learning** → **Serving**
3. Look for **Foundation Model APIs** or **Model Serving Endpoints**
4. Copy the exact endpoint name (e.g., `databricks-dbrx-instruct`, `dbrx-instruct`, or just `dbrx`)

## Option 2: Via Python Script

Run this script to list all available endpoints:

```python
from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv
import os

# Load credentials
load_dotenv('config/.env')

# Connect
client = WorkspaceClient(
    host=os.getenv('DATABRICKS_HOST'),
    token=os.getenv('DATABRICKS_TOKEN')
)

# List all serving endpoints
print("Available Serving Endpoints:")
print("=" * 80)

endpoints = client.serving_endpoints.list()
for endpoint in endpoints:
    print(f"\nName: {endpoint.name}")
    if hasattr(endpoint, 'config') and endpoint.config:
        if hasattr(endpoint.config, 'served_models'):
            for model in endpoint.config.served_models:
                print(f"  Model: {model.model_name}")
                print(f"  Version: {model.model_version}")

print("\n" + "=" * 80)
print("\nTo use a model, update your experiment command:")
print("  make run-internal MODEL=<endpoint-name>")
print("\nOr edit track_b_internal/experiment_internal.py default model")
```

## Option 3: Check Databricks Documentation

Visit: https://docs.databricks.com/en/machine-learning/foundation-models/index.html

Look for:
- Foundation Model APIs
- Pay-per-token Foundation Models
- External Models (OpenAI, Anthropic via Databricks)

## Common Endpoint Names

Depending on your workspace, endpoints might be:

### External Models via Databricks:
- `databricks-meta-llama-3-3-70b-instruct`
- `databricks-meta-llama-3-1-405b-instruct`
- Model names may vary - check your workspace!

### Databricks Proprietary:
- `databricks-dbrx-instruct` or `dbrx-instruct`
- Model availability depends on workspace tier

### Pay-Per-Token Models:
- Availability varies by workspace region and subscription

## Updating the Project

Once you find your endpoint name, update the default in [track_b_internal/experiment_internal.py](../track_b_internal/experiment_internal.py):

```python
parser.add_argument(
    "--model",
    type=str,
    default="YOUR-ACTUAL-ENDPOINT-NAME",  # Update this!
    ...
)
```

Or pass it as a parameter:

```bash
make run-internal MODEL=your-actual-endpoint-name
```

## Error: "Failed to find MT LLM Endpoint"

If you see this error, it means the endpoint name doesn't exist in your workspace. Follow the steps above to find the correct name.

**Note:** This is a learning project - the endpoint names are examples and may not match your workspace configuration!
