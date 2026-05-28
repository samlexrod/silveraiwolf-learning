"""Financial Risk Analysis Agent.

A ResponsesAgent that uses Databricks Foundation Models and Unity Catalog
function tools to answer questions about counterparty risk, financial ratios,
and portfolio concentration.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Generator

import mlflow
from openai import OpenAI

from risk_agent.config import load_model_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions — each maps to a Unity Catalog function
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_risk_exposure",
            "description": (
                "Retrieve counterparty risk exposure data including risk tier, "
                "total exposure, credit rating, and default probability."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "counterparty_name": {
                        "type": "string",
                        "description": "Name of the counterparty to look up",
                    }
                },
                "required": ["counterparty_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_ratios",
            "description": (
                "Retrieve financial ratios for a counterparty including debt-to-equity, "
                "current ratio, interest coverage, and return on equity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "counterparty_name": {
                        "type": "string",
                        "description": "Name of the counterparty to look up",
                    }
                },
                "required": ["counterparty_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_summary",
            "description": (
                "Retrieve portfolio summary showing concentration by sector, "
                "total exposure, number of counterparties, and average risk score."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolios",
            "description": (
                "List all available portfolios with their strategy, manager, "
                "and creation date. Use this to find valid portfolio IDs."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_counterparties",
            "description": (
                "Retrieve all counterparties in a specific portfolio with their "
                "allocation percentage, risk tier, total exposure, credit rating, "
                "and default probability. Use a portfolio_id from get_portfolios."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "string",
                        "description": "Portfolio ID (e.g., PF-ALPHA, PF-MERID, PF-GLOBE, PF-EMRKT)",
                    }
                },
                "required": ["portfolio_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_financial_health",
            "description": (
                "Retrieve all counterparties in a portfolio with BOTH risk exposure "
                "AND financial ratios in a single call. Returns allocation, risk tier, "
                "exposure, credit rating, default probability, debt-to-equity, current "
                "ratio, interest coverage, ROE, and revenue growth. Use this instead of "
                "calling get_financial_ratios per counterparty."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "string",
                        "description": "Portfolio ID (e.g., PF-ALPHA, PF-MERID, PF-GLOBE, PF-EMRKT)",
                    }
                },
                "required": ["portfolio_id"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool dispatch — calls the matching UC function wrapper
# ---------------------------------------------------------------------------


def _dispatch_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool call by dispatching to the appropriate UC function wrapper."""
    from risk_agent.tools.financial_ratios import get_financial_ratios
    from risk_agent.tools.portfolio_summary import get_portfolio_summary
    from risk_agent.tools.portfolios import get_portfolio_counterparties, get_portfolio_financial_health, get_portfolios
    from risk_agent.tools.risk_exposure import get_risk_exposure

    dispatch_map = {
        "get_risk_exposure": get_risk_exposure,
        "get_financial_ratios": get_financial_ratios,
        "get_portfolio_summary": get_portfolio_summary,
        "get_portfolios": get_portfolios,
        "get_portfolio_counterparties": get_portfolio_counterparties,
        "get_portfolio_financial_health": get_portfolio_financial_health,
    }

    func = dispatch_map.get(tool_name)
    if func is None:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    with mlflow.start_span(name=f"tool_{tool_name}", span_type="TOOL") as span:
        span.set_inputs({"tool_name": tool_name, "arguments": arguments})
        try:
            result = func(**arguments)
            output = json.dumps(result, default=str)
            span.set_outputs({"result": output})
            return output
        except Exception as e:
            logger.exception("Tool %s failed", tool_name)
            error_output = json.dumps({"error": str(e)})
            span.set_outputs({"error": str(e)})
            span.set_status("ERROR")
            return error_output


# ---------------------------------------------------------------------------
# Input normalization
# ---------------------------------------------------------------------------


def _extract_messages(model_input: Any) -> list[dict]:
    """Extract messages list from any input format.

    Handles:
    - dict: {"messages": [...]}  (local calls)
    - pandas DataFrame: single-row DF with "messages" column  (MLflow serving)
    - list of dicts: [{"messages": [...]}]  (dataframe_records conversion)
    - list of messages: [{"role": "user", "content": "..."}]  (raw messages)
    """
    # pandas DataFrame (MLflow serving sends this)
    if hasattr(model_input, "iloc"):
        try:
            row = model_input.iloc[0]
            msgs = row.get("messages", row.to_dict() if hasattr(row, "to_dict") else {})
            if isinstance(msgs, list):
                return msgs
            return []
        except Exception:
            return []

    # dict with "messages" key
    if isinstance(model_input, dict):
        msgs = model_input.get("messages", [])
        # Handle DataFrame.to_dict() format: {"messages": {0: [...]}}
        if isinstance(msgs, dict) and 0 in msgs:
            return msgs[0]
        if isinstance(msgs, list):
            return msgs
        return []

    # list — could be [{"messages": [...]}] or [{"role": "user", ...}]
    if isinstance(model_input, list) and model_input:
        first = model_input[0]
        if isinstance(first, dict) and "messages" in first:
            return first["messages"]
        if isinstance(first, dict) and "role" in first:
            return model_input
        return []

    return []


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class FinancialRiskAgent(mlflow.pyfunc.PythonModel):
    """Financial risk analysis agent backed by a Databricks Foundation Model.

    Uses OpenAI-compatible chat completions with tool calling to query
    Unity Catalog functions for real financial data.
    """

    def __init__(self) -> None:
        self.config = load_model_config()

        # Set experiment so traces are logged in serving containers.
        # Only activates when MLFLOW_EXPERIMENT_NAME is explicitly set
        # (by the serving endpoint env vars). Without it, traces go to
        # the active experiment or default — avoids creating stray
        # experiments during log_model() or local dev.
        exp_name = os.environ.get("MLFLOW_EXPERIMENT_NAME")
        if exp_name:
            try:
                mlflow.set_experiment(exp_name)
            except Exception:
                pass

        # Auth: use env vars if set, otherwise fall back to WorkspaceClient
        # (which auto-authenticates in Databricks serving endpoints and apps)
        host = self.config.get("databricks_host", "")
        token = self.config.get("databricks_token", "")

        if not host or not token:
            try:
                from databricks.sdk import WorkspaceClient

                w = WorkspaceClient()
                host = w.config.host
                token = w.config.token
            except Exception:
                pass

        self.client = OpenAI(
            api_key=token or "dapi-placeholder",
            base_url=f"{host}/serving-endpoints",
        )
        self.model = self.config["llm_endpoint"]
        self.system_prompt = self.config["system_prompt"]
        self.temperature = self.config.get("temperature", 0.1)
        self.max_tokens = self.config.get("max_tokens", 2048)

    @mlflow.trace(span_type="AGENT")
    def predict(self, context: Any = None, model_input: dict | list | None = None) -> dict:
        """Handle a single request and return a response.

        Args:
            context: MLflow model context (unused in direct calls).
            model_input: A dict with a "messages" key containing the conversation,
                         or a list of messages directly.

        Returns:
            A dict with a "content" key containing the agent's response text.
        """
        # Normalize input — handle dict (local), DataFrame (serving), and list formats
        messages = _extract_messages(model_input)

        # Use custom system prompt if provided in messages, otherwise use default
        if messages and messages[0].get("role") == "system":
            system_prompt = messages[0]["content"]
            full_messages = messages
        else:
            system_prompt = self.system_prompt
            full_messages = [{"role": "system", "content": system_prompt}] + messages

        # Set clean trace inputs (replaces the auto-captured raw args)
        span = mlflow.get_current_active_span()
        if span:
            user_msg = next((m["content"] for m in messages if m.get("role") == "user"), "")
            is_custom = messages and messages[0].get("role") == "system"
            span.set_inputs({
                "question": user_msg,
                "system_prompt": system_prompt[:300],
                "prompt_source": "custom" if is_custom else "default",
            })

        # Agentic loop — iterate until no more tool calls
        for _ in range(5):  # max 5 tool-call rounds
            response = self._call_llm(full_messages)
            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                # Append assistant message with tool calls
                msg = choice.message.model_dump(exclude_none=True)
                msg.pop("annotations", None)
                if "tool_calls" in msg:
                    for tc in msg["tool_calls"]:
                        tc.pop("annotations", None)
                full_messages.append(msg)

                # Execute each tool call and append results
                for tool_call in choice.message.tool_calls:
                    arguments = json.loads(tool_call.function.arguments)
                    result = _dispatch_tool(tool_call.function.name, arguments)
                    full_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )
            else:
                # Final response — no more tool calls
                output = {"content": choice.message.content}
                if span:
                    span.set_outputs(output)
                return output

        fallback = {"content": "I was unable to fully answer after multiple tool calls. Please try a simpler question."}
        if span:
            span.set_outputs(fallback)
        return fallback

    @mlflow.trace(span_type="AGENT")
    def predict_stream(
        self, context: Any = None, model_input: dict | list | None = None
    ) -> Generator[str, None, None]:
        """Streaming version of predict that yields response chunks.

        Args:
            context: MLflow model context (unused in direct calls).
            model_input: A dict with a "messages" key or a list of messages.

        Yields:
            String chunks of the agent's response.
        """
        # Normalize input — handle dict (local), DataFrame (serving), and list formats
        messages = _extract_messages(model_input)

        # Use custom system prompt if provided in messages, otherwise use default
        if messages and messages[0].get("role") == "system":
            full_messages = messages
        else:
            full_messages = [{"role": "system", "content": self.system_prompt}] + messages

        # Handle tool calls in a non-streaming pre-pass
        for _ in range(5):
            response = self._call_llm(full_messages)
            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                msg = choice.message.model_dump(exclude_none=True)
                msg.pop("annotations", None)
                if "tool_calls" in msg:
                    for tc in msg["tool_calls"]:
                        tc.pop("annotations", None)
                full_messages.append(msg)
                for tool_call in choice.message.tool_calls:
                    arguments = json.loads(tool_call.function.arguments)
                    result = _dispatch_tool(tool_call.function.name, arguments)
                    full_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )
            else:
                break

        # Final streaming call
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            tools=TOOL_DEFINITIONS,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    @mlflow.trace(span_type="LLM")
    def _call_llm(self, messages: list[dict]) -> Any:
        """Make a non-streaming LLM call with tool definitions."""
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )


# ---------------------------------------------------------------------------
# MLflow model registration entry point
# ---------------------------------------------------------------------------

agent = FinancialRiskAgent()
mlflow.models.set_model(agent)


if __name__ == "__main__":
    # Quick local test
    test_input = {"messages": [{"role": "user", "content": "What is the risk tier for Acme Corp?"}]}
    result = agent.predict(model_input=test_input)
    print(result["content"])
