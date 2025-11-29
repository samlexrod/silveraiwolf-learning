"""
Internal Databricks Foundation Model Agent for News Classification
Uses Databricks-hosted models (DBRX, Llama-3) via Foundation Model APIs
"""

import os
from typing import Dict, Optional
import sys
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.news_categories import (
    NEWS_CATEGORIES,
    SENTIMENT_CATEGORIES,
    COMBINED_PROMPT_TEMPLATE
)
from utils.databricks_auth import get_databricks_client


class InternalNewsClassifierAgent:
    """
    News classification agent using Databricks Foundation Models
    """

    def __init__(
        self,
        model: str = "databricks-gpt-oss-20b"
    ):
        """
        Initialize internal agent

        Args:
            model: Foundation model endpoint name

                   OpenAI models via Databricks:
                   - databricks-gpt-5-1 (Latest GPT with reasoning, 128K context)
                   - databricks-gpt-5 (State-of-the-art reasoning, 128K context)
                   - databricks-gpt-5-mini (Cost-optimized, 128K context)
                   - databricks-gpt-5-nano (High-throughput, 128K context)
                   - databricks-gpt-oss-120b (OSS reasoning model, 128K context)
                   - databricks-gpt-oss-20b (Lightweight OSS, 128K context)

                   Google models:
                   - databricks-gemini-3-pro (Hybrid reasoning, 1M context)
                   - databricks-gemini-2.5-pro (Deep Think Mode, 1M context)
                   - databricks-gemini-2.5-flash (Cost-efficient, 1M context)
                   - databricks-gemma-3-12b (Multimodal vision, 128K context)

                   Meta Llama models:
                   - databricks-llama-4-maverick (Mixture of experts)
                   - databricks-meta-llama-3-3-70b-instruct (Multilingual, 128K)
                   - databricks-meta-llama-3-1-405b-instruct (Largest open, 128K)
                   - databricks-meta-llama-3-1-8b-instruct (Lightweight, 128K)
                   - databricks-meta-llama-3-70b-instruct (Original, 128K)

                   Anthropic Claude models:
                   - databricks-claude-sonnet-4-5 (Hybrid reasoning)
                   - databricks-claude-sonnet-4 (State-of-the-art)
                   - databricks-claude-opus-4-1 (200K context, image support)
                   - databricks-claude-3.7-sonnet (Extended thinking)

                   Databricks proprietary:
                   - databricks-dbrx-instruct (Databricks flagship model)

                   Other open models:
                   - databricks-qwen3-next-80b-a3b-instruct (Alibaba model)
        """
        self.model = model
        self.client = get_databricks_client()

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

        # Call Databricks Foundation Model API
        response = self._call_foundation_model(prompt)

        # Parse response
        return self._parse_response(response)

    def _call_foundation_model(self, prompt: str) -> str:
        """
        Call Databricks Foundation Model API

        Args:
            prompt: User prompt

        Returns:
            str: Model response
        """
        try:
            # Create chat message
            messages = [
                ChatMessage(
                    role=ChatMessageRole.SYSTEM,
                    content="You are a news classification expert."
                ),
                ChatMessage(
                    role=ChatMessageRole.USER,
                    content=prompt
                )
            ]

            # Call the serving endpoint
            response = self.client.serving_endpoints.query(
                name=self.model,
                messages=messages,
                temperature=0.0,  # Deterministic for classification
                max_tokens=300  # Increased for reasoning models that explain first
            )

            # Extract response text
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content

                # Handle different response formats
                if isinstance(content, list):
                    # List of content chunks
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            # Structured response (e.g., reasoning models)
                            if 'text' in item:
                                text_parts.append(str(item['text']))
                            elif 'summary' in item:
                                # Extract from summary field
                                summary = item['summary']
                                if isinstance(summary, list):
                                    for summary_item in summary:
                                        if isinstance(summary_item, dict) and 'text' in summary_item:
                                            text_parts.append(str(summary_item['text']))
                                        else:
                                            text_parts.append(str(summary_item))
                                else:
                                    text_parts.append(str(summary))
                            else:
                                text_parts.append(str(item))
                        else:
                            text_parts.append(str(item))
                    content = ''.join(text_parts)
                elif isinstance(content, dict):
                    # Single dict response (reasoning models)
                    if 'text' in content:
                        content = str(content['text'])
                    elif 'summary' in content:
                        summary = content['summary']
                        if isinstance(summary, list):
                            text_parts = []
                            for item in summary:
                                if isinstance(item, dict) and 'text' in item:
                                    text_parts.append(str(item['text']))
                                else:
                                    text_parts.append(str(item))
                            content = ''.join(text_parts)
                        else:
                            content = str(summary)
                    else:
                        content = str(content)
                elif isinstance(content, str):
                    # Already a string
                    pass
                else:
                    content = str(content)

                return content.strip()
            else:
                raise Exception("No response from model")

        except Exception as e:
            raise Exception(f"Error calling Databricks Foundation Model: {e}")

    def _parse_response(self, response: str) -> Dict[str, str]:
        """
        Parse model response to extract category and sentiment

        Args:
            response: Raw model response

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
            "provider": "databricks",
            "model": self.model,
            "model_type": "foundation_model_api"
        }