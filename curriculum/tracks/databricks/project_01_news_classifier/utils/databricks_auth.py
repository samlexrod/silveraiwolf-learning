"""
Databricks authentication and secret management utilities
"""

import os
from typing import Optional
from databricks.sdk import WorkspaceClient


def get_databricks_client() -> WorkspaceClient:
    """
    Initialize Databricks workspace client using environment variables

    Returns:
        WorkspaceClient: Authenticated Databricks client
    """
    host = os.getenv("DATABRICKS_HOST")
    token = os.getenv("DATABRICKS_TOKEN")

    if not host or not token:
        raise ValueError(
            "DATABRICKS_HOST and DATABRICKS_TOKEN must be set in environment variables"
        )

    return WorkspaceClient(host=host, token=token)


def get_databricks_secret(scope: str, key: str) -> str:
    """
    Retrieve a secret from Databricks secret scope

    Args:
        scope: Secret scope name
        key: Secret key name

    Returns:
        str: Secret value
    """
    try:
        client = get_databricks_client()
        secret_value = client.secrets.get_secret(scope=scope, key=key)
        return secret_value.value
    except Exception as e:
        print(f"Warning: Could not retrieve secret {key} from scope {scope}: {e}")
        print("Falling back to environment variable...")

        # Fallback to environment variable for local development
        env_key = key.upper().replace("-", "_")
        value = os.getenv(env_key)
        if not value:
            raise ValueError(
                f"Could not find secret {key} in Databricks scope {scope} "
                f"and environment variable {env_key} is not set"
            )
        return value


def verify_databricks_connection() -> bool:
    """
    Verify that Databricks connection is working

    Returns:
        bool: True if connection is successful
    """
    try:
        client = get_databricks_client()
        # Try to get current user as a simple connectivity test
        user = client.current_user.me()
        print(f"✓ Successfully connected to Databricks as: {user.user_name}")
        return True
    except Exception as e:
        print(f"✗ Failed to connect to Databricks: {e}")
        return False