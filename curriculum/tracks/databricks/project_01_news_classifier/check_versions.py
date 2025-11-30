#!/usr/bin/env python
"""Check all registered model versions and their aliases"""

import os
import mlflow
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv

# Load environment
load_dotenv('config/.env')

# Setup
mlflow.set_registry_uri(os.getenv('MLFLOW_REGISTRY_URI', 'databricks-uc'))
client = MlflowClient()

model_name = 'main.news_classifier.news_classifier'

print("=" * 80)
print(f"MODEL VERSIONS: {model_name}")
print("=" * 80)
print()

try:
    # First get basic version list
    versions_basic = client.search_model_versions(f"name='{model_name}'")
    print(f"Total versions registered: {len(versions_basic)}\n")

    # Then get detailed info for each version
    for v_basic in sorted(versions_basic, key=lambda x: int(x.version)):
        # Get full version details with tags (required for Unity Catalog)
        v = client.get_model_version(model_name, v_basic.version)

        aliases = v.aliases if hasattr(v, 'aliases') else []
        tags = v.tags if hasattr(v, 'tags') else {}

        provider = tags.get('provider', 'unknown') if tags else 'unknown'
        model_tag = tags.get('model', 'unknown') if tags else 'unknown'
        acc = tags.get('category_accuracy', 'N/A') if tags else 'N/A'

        alias_str = ', '.join(aliases) if aliases else 'None'

        print(f"Version {v.version}:")
        print(f"  Provider: {provider}")
        print(f"  Model: {model_tag}")
        print(f"  Accuracy: {acc}")
        print(f"  Aliases: {alias_str}")
        print(f"  Status: {v.current_stage}")
        print()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
