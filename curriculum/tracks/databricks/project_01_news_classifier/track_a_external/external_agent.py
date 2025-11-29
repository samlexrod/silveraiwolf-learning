"""
External LLM Agent for News Classification
Uses OpenAI or Anthropic APIs with secrets managed in Databricks
"""

import os
from typing import Dict, Literal, Optional
from openai import OpenAI
from anthropic import Anthropic
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.news_categories import (
    NEWS_CATEGORIES,
    SENTIMENT_CATEGORIES,
    COMBINED_PROMPT_TEMPLATE
)
from utils.databricks_auth import get_databricks_secret


class ExternalNewsClassifierAgent:
    """
    News classification agent using external LLM providers
    """

    def __init__(
        self,
        provider: Literal["openai", "anthropic"] = "openai",
        model: Optional[str] = None,
        use_databricks_secrets: bool = False
    ):
        """
        Initialize external agent

        Args:
            provider: LLM provider ('openai' or 'anthropic')
            model: Model name (defaults to best available)
            use_databricks_secrets: Whether to use Databricks secret scope
        """
        self.provider = provider
        self.use_databricks_secrets = use_databricks_secrets

        # Set default models
        if model is None:
            self.model = "gpt-4o-mini" if provider == "openai" else "claude-3-5-sonnet-20241022"
        else:
            self.model = model

        # Initialize client
        self._init_client()

    def _init_client(self):
        """Initialize LLM client with API key"""
        if self.provider == "openai":
            api_key = self._get_api_key("OPENAI_API_KEY", "openai-api-key")
            self.client = OpenAI(api_key=api_key)
        elif self.provider == "anthropic":
            api_key = self._get_api_key("ANTHROPIC_API_KEY", "anthropic-api-key")
            self.client = Anthropic(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _get_api_key(self, env_var: str, secret_key: str) -> str:
        """
        Get API key from Databricks secrets or environment

        Args:
            env_var: Environment variable name
            secret_key: Databricks secret key

        Returns:
            str: API key
        """
        if self.use_databricks_secrets:
            scope = os.getenv("DATABRICKS_SECRET_SCOPE", "news-classifier-secrets")
            return get_databricks_secret(scope, secret_key)
        else:
            api_key = os.getenv(env_var)
            if not api_key:
                raise ValueError(f"{env_var} environment variable not set")
            return api_key

    def classify(self, title: str, content: str) -> Dict[str, str]:
        """
        Classify news article (category + sentiment)

        Args:
            title: Article title
            content: Article content

        Returns:
            Dict with 'category', 'sentiment', and 'raw_response'
        """
        # Build prompt
        prompt = COMBINED_PROMPT_TEMPLATE.format(
            categories=", ".join(NEWS_CATEGORIES),
            sentiments=", ".join(SENTIMENT_CATEGORIES),
            title=title,
            content=content
        )

        # Call LLM
        if self.provider == "openai":
            response = self._call_openai(prompt)
        else:
            response = self._call_anthropic(prompt)

        # Parse response
        return self._parse_response(response)

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a news classification expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,  # Deterministic for classification
            max_tokens=100
        )
        return response.choices[0].message.content.strip()

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=100,
            temperature=0,  # Deterministic for classification
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text.strip()

    def _parse_response(self, response: str) -> Dict[str, str]:
        """
        Parse LLM response to extract category and sentiment

        Args:
            response: Raw LLM response

        Returns:
            Dict with category, sentiment, and raw_response
        """
        result = {
            "category": "Unknown",
            "sentiment": "Unknown",
            "raw_response": response
        }

        # Parse response (format: "Category: X\nSentiment: Y")
        lines = response.strip().split("\n")
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()

                if "category" in key:
                    # Validate against known categories
                    if value in NEWS_CATEGORIES:
                        result["category"] = value
                    else:
                        # Try to find closest match
                        for cat in NEWS_CATEGORIES:
                            if cat.lower() in value.lower():
                                result["category"] = cat
                                break

                elif "sentiment" in key:
                    # Validate against known sentiments
                    if value in SENTIMENT_CATEGORIES:
                        result["sentiment"] = value
                    else:
                        # Try to find closest match
                        for sent in SENTIMENT_CATEGORIES:
                            if sent.lower() in value.lower():
                                result["sentiment"] = sent
                                break

        return result

    def get_model_info(self) -> Dict[str, str]:
        """Get model information for logging"""
        return {
            "provider": self.provider,
            "model": self.model,
            "use_databricks_secrets": str(self.use_databricks_secrets)
        }