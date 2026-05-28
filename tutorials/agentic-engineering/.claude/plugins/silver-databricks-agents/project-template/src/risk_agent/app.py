"""Coliseum — Portfolio Risk Agent Dashboard (Gradio).

Four tabs:
- Multi-Turn Playground: Free-form conversation about a portfolio
- Single-Turn Playground: Edit prompt, generate all 6 insight cards for a portfolio
- A/B Testing: Compare Champion vs Custom prompt card-by-card
- Data: View A/B results and export to MLflow

Run locally:  python src/risk_agent/app.py
Deploy:       Upload to workspace alongside app.yaml + requirements.txt
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

import requests as http_requests

logger = logging.getLogger(__name__)

try:
    import gradio as gr
except ImportError:
    raise ImportError("gradio is required. Install with: pip install gradio")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ENDPOINT_NAME = "risk-agent-endpoint"
MODEL_NAME = "main.financial_risk.risk_agent"

DEFAULT_PROMPT = (
    "You are a financial risk analyst for a portfolio management firm.\n"
    "Answer using data from the Gold tables via the available tools.\n"
    "Always call get_portfolio_financial_health or get_portfolio_counterparties with the portfolio ID.\n\n"
    "Response rules:\n"
    "- Present results directly — do NOT explain your methodology or reasoning process.\n"
    "- Lead with the answer, not how you calculated it.\n"
    "- Use markdown tables for multi-counterparty data. Use short column headers (Name, Tier, Exposure, Rating, D/E, etc.). Always add a blank line after the table before any summary text.\n"
    "- Cite specific numbers, risk tiers, and counterparty names.\n"
    "- Be concise — no filler phrases like 'Let me calculate' or 'We need to'."
)

PORTFOLIOS = {
    "PF-ALPHA": {"name": "Alpha Growth", "strategy": "Aggressive", "manager": "Sarah Chen"},
    "PF-MERID": {"name": "Meridian Income", "strategy": "Conservative", "manager": "James OBrien"},
    "PF-GLOBE": {"name": "Global Balanced", "strategy": "Balanced", "manager": "Maria Santos"},
    "PF-EMRKT": {"name": "Emerging Markets", "strategy": "Growth", "manager": "Raj Patel"},
}

PORTFOLIO_CHOICES = [f"{pid} — {p['name']} ({p['strategy']})" for pid, p in PORTFOLIOS.items()]

INSIGHT_CARD_TEMPLATES = [
    {"id": "risk_overview", "icon": "📊", "title": "Risk Overview",
     "question": "Provide a risk overview: list all counterparties with their risk tier, total exposure, credit rating, and default probability. Summarize the overall risk distribution."},
    {"id": "high_risk", "icon": "🔴", "title": "High-Risk Alerts",
     "question": "Identify all CRITICAL and HIGH risk counterparties. For each, show exposure amount, default probability, and credit rating. Flag the most urgent concerns."},
    {"id": "top_exposures", "icon": "📈", "title": "Top Exposures",
     "question": "Show the top 5 counterparties by allocation percentage. Include their risk tier, exposure amount, and sector."},
    {"id": "sector_concentration", "icon": "🏭", "title": "Sector Concentration",
     "question": "Break down this portfolio's exposure by sector. Show total allocation, number of counterparties, and dominant risk tier per sector."},
    {"id": "financial_health", "icon": "💰", "title": "Financial Health",
     "question": "Summarize the financial health across this portfolio. For the top counterparties by allocation, show debt-to-equity, current ratio, interest coverage, and revenue growth."},
    {"id": "default_risk", "icon": "⚠️", "title": "Default Risk",
     "question": "Calculate the exposure-weighted default probability for this portfolio. Identify the 3 counterparties contributing most to default risk."},
]

# Mutable eval set — loaded from feedback dataset at runtime
AB_EVAL_SET: list[dict] = []

MULTI_TURN_QUESTIONS = [
    "What is the overall risk profile of this portfolio?",
    "Which counterparties should I be most concerned about?",
    "How is the exposure distributed across sectors?",
    "Are there any counterparties with deteriorating financials?",
    "What is the total exposure and weighted default probability?",
    "Compare the top 3 holdings by risk tier",
]


# ---------------------------------------------------------------------------
# MLflow integration
# ---------------------------------------------------------------------------

def _init_mlflow():
    try:
        import mlflow
        mlflow.set_experiment("/Shared/risk-agent")
    except Exception:
        pass


def _log_ab_traces(card_id: str, question: str, champ_resp: str, cand_resp: str) -> dict:
    trace_ids = {}
    try:
        import mlflow
        _init_mlflow()
        with mlflow.start_span(name="ab_champion") as span:
            span.set_inputs({"question": question, "variant": "champion", "card_id": card_id})
            span.set_outputs({"response": champ_resp})
        trace_ids["champion"] = mlflow.get_last_active_trace_id()
        with mlflow.start_span(name="ab_candidate") as span:
            span.set_inputs({"question": question, "variant": "candidate", "card_id": card_id})
            span.set_outputs({"response": cand_resp})
        trace_ids["candidate"] = mlflow.get_last_active_trace_id()
    except Exception as e:
        logger.warning("Failed to log AB traces: %s", e)
    return trace_ids


def _log_vote_feedback(trace_ids: dict, winner: str, card_title: str):
    try:
        import mlflow
        from mlflow.entities.assessment import AssessmentSource
        for variant, tid in trace_ids.items():
            if not tid:
                continue
            is_winner = (variant == winner) or (winner == "custom" and variant == "candidate")
            mlflow.log_feedback(
                trace_id=tid, name="risk_winner", value=is_winner,
                rationale=f"A/B vote: {winner} won for '{card_title}'",
                source=AssessmentSource(source_type="HUMAN", source_id="playground_user"),
            )
    except Exception as e:
        logger.warning("Failed to log vote: %s", e)


# ---------------------------------------------------------------------------
# Trace-based feedback — human assessments live on traces, datasets built from them
# ---------------------------------------------------------------------------

FEEDBACK_DATASET_NAME = "main.financial_risk.risk_agent_feedback"
_feedback_dataset_id: list[str] = []  # mutable cache
_last_load_error: list[str] = []


def _pat_auth_headers() -> tuple[str, dict]:
    """Get PAT auth headers (reads from secret scope). Needed for managed-evals API."""
    try:
        import base64
        w = _get_workspace_client()
        host = w.config.host
        raw = w.secrets.get_secret("risk-agent", "databricks-token").value
        if raw:
            token = base64.b64decode(raw).decode("utf-8")
            return host, {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    except Exception as e:
        logger.warning("Could not read PAT from secrets: %s", e)
    host = os.environ.get("DATABRICKS_HOST", "")
    token = os.environ.get("DATABRICKS_TOKEN", "")
    if host and token:
        return host, {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return _auth_headers()


def _log_expectation_on_trace(trace_id: str, expected_response: str):
    """Log an expectation assessment on a trace — the ideal answer from a domain expert."""
    try:
        import mlflow
        mlflow.log_expectation(
            trace_id=trace_id,
            name="expected_response",
            value=expected_response,
        )
    except Exception as e:
        logger.warning("Failed to log expectation on trace %s: %s", trace_id, e)


def _load_assessed_traces() -> list[dict]:
    """Load traces that have human feedback assessments. Returns list of eval dicts."""
    _last_load_error.clear()
    try:
        host, headers = _pat_auth_headers()
        # Search traces in the experiment
        exp_id = os.environ.get("MLFLOW_EXPERIMENT_ID", "")
        if not exp_id:
            # Look up experiment ID
            resp = http_requests.get(
                f"{host}/api/2.0/mlflow/experiments/get-by-name?experiment_name=/Shared/risk-agent-tutorial",
                headers=headers, timeout=15,
            )
            exp_data = resp.json()
            exp_id = exp_data.get("experiment", {}).get("experiment_id", "")
        if not exp_id:
            _last_load_error.append("Could not find experiment ID")
            return []

        # Search traces — get those with assessments
        resp = http_requests.post(
            f"{host}/api/2.0/mlflow/traces/search",
            headers=headers,
            json={"experiment_ids": [exp_id], "max_results": 100},
            timeout=30,
        )
        data = resp.json()
        if "error_code" in data:
            # Fall back to the search_traces endpoint format
            resp = http_requests.get(
                f"{host}/api/2.0/mlflow/traces?experiment_id={exp_id}&max_results=100",
                headers=headers, timeout=30,
            )
            data = resp.json()

        traces = data.get("traces", [])
        items = []
        seen_questions = set()

        for trace in traces:
            # Check for human feedback assessments
            assessments = trace.get("assessments", [])
            has_feedback = False
            winner = ""
            expected = ""
            for a in assessments:
                source = a.get("source", {})
                if source.get("source_type") == "HUMAN":
                    has_feedback = True
                    fb = a.get("feedback", {})
                    rationale = fb.get("rationale", "")
                    if "champion" in rationale:
                        winner = "champion"
                    elif "custom" in rationale:
                        winner = "custom"
                    elif "neither" in rationale:
                        winner = "neither"
                if a.get("name") == "expected_response":
                    exp_val = a.get("expectation", {})
                    expected = exp_val.get("value", "") if isinstance(exp_val, dict) else str(exp_val)

            if not has_feedback:
                continue

            # Extract question from trace inputs
            trace_data = trace.get("data", {})
            spans = trace_data.get("spans", []) if isinstance(trace_data, dict) else []
            question = ""
            response = ""

            # Try root span inputs
            if spans:
                root = spans[0] if isinstance(spans, list) else {}
                inputs = root.get("inputs", root.get("attributes", {}).get("inputs", {}))
                if isinstance(inputs, dict):
                    question = inputs.get("question", inputs.get("query", ""))
                outputs = root.get("outputs", root.get("attributes", {}).get("outputs", {}))
                if isinstance(outputs, dict):
                    response = outputs.get("response", "")

            # Also check request field
            if not question:
                req = trace.get("request", "")
                if isinstance(req, str):
                    try:
                        req_data = json.loads(req)
                        question = req_data.get("question", req_data.get("query", ""))
                    except (json.JSONDecodeError, TypeError):
                        pass
                elif isinstance(req, dict):
                    question = req.get("question", req.get("query", ""))

            if not question or question in seen_questions:
                continue
            seen_questions.add(question)

            trace_id = trace.get("info", {}).get("trace_id", trace.get("trace_id", f"t_{len(items)}"))
            items.append({
                "id": f"trace_{trace_id}",
                "trace_id": trace_id,
                "icon": "👤",
                "title": question[:50] + ("..." if len(question) > 50 else ""),
                "question": question,
                "response": response,
                "expected_response": expected,
                "source": "trace_feedback",
                "winner": winner,
            })

        return items
    except Exception as e:
        _last_load_error.append(str(e))
        logger.warning("Failed to load assessed traces: %s", e)
        return []


def _refresh_ab_eval_set() -> str:
    """Reload the A/B eval set from assessed traces. Returns status message."""
    items = _load_assessed_traces()
    AB_EVAL_SET.clear()
    _ab_results.clear()
    _ab_responses.clear()
    _ab_trace_ids.clear()
    _ab_index[0] = 0
    _votes["candidate"] = {"up": 0, "down": 0}
    if items:
        AB_EVAL_SET.extend(items)
        return f"**{len(items)}** items loaded from assessed traces"
    return "**No assessed traces found.** Vote in A/B Testing and submit feedback to create assessed traces."


def _save_feedback_on_trace(trace_id: str, expected_response: str) -> str:
    """Log expected response as an expectation on a trace. Returns status message."""
    if not trace_id or not expected_response.strip():
        return "Skipped (no trace or comment)"
    try:
        _log_expectation_on_trace(trace_id, expected_response.strip())
        return "Expectation saved on trace"
    except Exception as e:
        return f"Error: {e}"


def _build_dataset_from_traces() -> str:
    """Build the MLflow evaluation dataset from assessed traces. Returns status message."""
    try:
        items = _load_assessed_traces()
        if not items:
            return "No assessed traces to build dataset from."

        host, headers = _pat_auth_headers()

        # Get or create dataset
        dataset_id = os.environ.get("FEEDBACK_DATASET_ID", "")
        if not dataset_id:
            resp = http_requests.post(
                f"{host}/api/2.0/managed-evals/datasets",
                headers=headers,
                json={"name": FEEDBACK_DATASET_NAME, "source_type": "databricks-uc-table"},
                timeout=30,
            )
            data = resp.json()
            dataset_id = data.get("dataset_id", "")

        if not dataset_id:
            return "Could not create/find dataset"

        # Build records from assessed traces
        requests_list = []
        for item in items:
            if not item.get("expected_response"):
                continue
            requests_list.append({
                "dataset_id": dataset_id,
                "dataset_record": {
                    "inputs": [{"key": "query", "value": item["question"]}],
                    "expectations": {"expected_response": {"value": item["expected_response"]}},
                    "tags": {"source": "traces", "winner": item.get("winner", "")},
                },
            })

        if not requests_list:
            return f"{len(items)} traces found but none have expected responses. Submit feedback with comments first."

        resp = http_requests.post(
            f"{host}/api/2.0/managed-evals/datasets/{dataset_id}/records:batchCreate",
            headers=headers,
            json={"requests": requests_list},
            timeout=30,
        )
        data = resp.json()
        created = len(data.get("dataset_records", []))
        return f"Built dataset: **{created}** records from {len(items)} assessed traces → visible in MLflow Datasets tab"

    except Exception as e:
        return f"Error building dataset: {e}"


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _get_workspace_client():
    from databricks.sdk import WorkspaceClient
    return WorkspaceClient()


def _auth_headers() -> tuple[str, dict]:
    w = _get_workspace_client()
    headers = w.config.authenticate()
    headers["Content-Type"] = "application/json"
    return w.config.host, headers


def _query_endpoint(question: str, max_retries: int = 2) -> str:
    for attempt in range(max_retries + 1):
        try:
            host, headers = _auth_headers()
            resp = http_requests.post(
                f"{host}/serving-endpoints/{ENDPOINT_NAME}/invocations",
                headers=headers,
                json={"dataframe_records": [{"messages": [{"role": "user", "content": question}]}]},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            preds = data.get("predictions")
            if isinstance(preds, list) and preds:
                first = preds[0]
                return first.get("content", str(first)) if isinstance(first, dict) else str(first)
            if isinstance(preds, dict):
                return preds.get("content", json.dumps(preds))
            return json.dumps(data, default=str)[:500]
        except Exception as e:
            if attempt < max_retries and "timeout" in str(e).lower():
                time.sleep(5)
                continue
            return f"Error: {e} (endpoint may be waking up — try again in ~30s)"


def _query_custom(question: str, system_prompt: str, max_retries: int = 2) -> str:
    if not system_prompt.strip():
        return "(no custom prompt set)"
    for attempt in range(max_retries + 1):
        try:
            host, headers = _auth_headers()
            resp = http_requests.post(
                f"{host}/serving-endpoints/{ENDPOINT_NAME}/invocations",
                headers=headers,
                json={"dataframe_records": [{"messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ]}]},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            preds = data.get("predictions")
            if isinstance(preds, list) and preds:
                first = preds[0]
                return first.get("content", str(first)) if isinstance(first, dict) else str(first)
            if isinstance(preds, dict):
                return preds.get("content", json.dumps(preds))
            return json.dumps(data, default=str)[:500]
        except Exception as e:
            if attempt < max_retries and "timeout" in str(e).lower():
                time.sleep(5)
                continue
            return f"Error: {e} (endpoint may be waking up — try again in ~30s)"


def _portfolio_question(question: str, portfolio_id: str) -> str:
    pinfo = PORTFOLIOS.get(portfolio_id, {})
    return (
        f"[Portfolio: {pinfo.get('name', portfolio_id)} (ID: {portfolio_id}, "
        f"Strategy: {pinfo.get('strategy', '?')})] {question}"
    )


def _parse_portfolio_choice(choice: str) -> str:
    return choice.split(" — ")[0] if " — " in choice else "PF-ALPHA"


def _get_status_markdown() -> str:
    try:
        w = _get_workspace_client()
        ep = w.serving_endpoints.get(ENDPOINT_NAME)
        ready = str(ep.state.ready) if ep.state else "UNKNOWN"
        version = "?"
        if ep.config and ep.config.served_entities:
            version = ep.config.served_entities[0].entity_version
        badge = "🟢" if "READY" in ready else ("🟡" if "NOT_READY" in ready else "🔴")
        return f"{badge} **{ready.split('.')[-1]}** | `{MODEL_NAME}` v{version}"
    except Exception as e:
        return f"🔴 {e}"


def _parse_followups(response: str) -> tuple[str, list[str]]:
    for marker in ["Follow-up questions:", "Follow up questions:", "Suggested follow-up"]:
        if marker.lower() in response.lower():
            idx = response.lower().index(marker.lower())
            main = response[:idx].rstrip()
            items = re.findall(r'\d+[.)]\s*(.+?)(?=\n\d+[.)]|\Z)', response[idx:], re.DOTALL)
            followups = [item.strip().rstrip("?") + "?" for item in items if len(item.strip()) > 10][:3]
            return main, followups
    return response, []


# ---------------------------------------------------------------------------
# Module-level state (shared across callbacks — Gradio is single-process)
# ---------------------------------------------------------------------------

_votes: dict[str, dict[str, int]] = {"candidate": {"up": 0, "down": 0}}
_ab_responses: dict[str, dict[str, str]] = {}
_ab_trace_ids: dict[str, dict] = {}
_ab_results: dict[int, str] = {}
_ab_index: list[int] = [0]  # mutable so callbacks can change it
_pg_cards: dict[str, str] = {}


def _gate_pct() -> float:
    total = _votes["candidate"]["up"] + _votes["candidate"]["down"]
    if total == 0:
        return 0.0
    return _votes["candidate"]["up"] / total * 100


def _gate_md() -> str:
    total = _votes["candidate"]["up"] + _votes["candidate"]["down"]
    if total == 0:
        return "⬜ Pick winners to start — need ≥80% on 3+ comparisons"
    pct = _gate_pct()
    if total >= 3 and pct >= 80:
        return f"✅ **GATE PASSED** — {pct:.0f}% custom wins ({_votes['candidate']['up']}/{total})"
    return f"⬜ {pct:.0f}% custom wins ({_votes['candidate']['up']}/{total}) — need ≥80% on 3+"


def _can_register() -> bool:
    total = _votes["candidate"]["up"] + _votes["candidate"]["down"]
    return total >= 3 and _gate_pct() >= 80


# ---------------------------------------------------------------------------
# Gradio app
# ---------------------------------------------------------------------------

def build_app() -> gr.Blocks:

    with gr.Blocks(title="Coliseum", theme=gr.themes.Soft()) as app:

        # ── Sidebar — shared across all tabs ──
        with gr.Sidebar():
            gr.Markdown("## ⚔️ Coliseum")
            gr.Markdown("Portfolio Risk Dashboard")
            status_md = gr.Markdown("🔄 Checking endpoint...")
            app.load(fn=_get_status_markdown, outputs=[status_md])

            gr.Markdown("---")
            sb_portfolio = gr.Dropdown(
                choices=PORTFOLIO_CHOICES, value=PORTFOLIO_CHOICES[0],
                label="📁 Portfolio",
            )
            sb_info = gr.Markdown("")

            def _sb_info(choice):
                pid = _parse_portfolio_choice(choice)
                p = PORTFOLIOS.get(pid, {})
                return f"**{p.get('name', pid)}** — {p.get('strategy', '?')}\\\nManager: {p.get('manager', '?')}"
            sb_portfolio.change(_sb_info, [sb_portfolio], [sb_info])
            app.load(lambda: _sb_info(PORTFOLIO_CHOICES[0]), outputs=[sb_info])

            gr.Markdown("---")
            gr.Markdown("### Candidate Gate")
            sb_gate_md = gr.Markdown(_gate_md())
            with gr.Row():
                sb_reg_btn = gr.Button("📋 Register", variant="secondary", size="sm")
                sb_dspy_btn = gr.Button("⚡ DSPy", variant="secondary", size="sm")

        # ── Main content — tabs ──
        with gr.Tabs():

            # =============================================================
            # TAB 0 — Workflow
            # =============================================================
            with gr.Tab("🏠 Workflow"):
                gr.Markdown("""
## How the Coliseum Works

The Coliseum is where domain experts — not just ML engineers — improve the agent through a structured feedback loop.
""")
                gr.Markdown("""### The Optimization Flywheel

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'edgeLabelBackground': '#1a1a2e', 'lineColor': '#888'}}}%%
flowchart TD
    subgraph S1["1. EXPLORE"]
        MT["Multi-Turn — chat about any portfolio"]
        ST["Single-Turn — insight cards with custom prompt"]
    end

    subgraph S2["2. EVALUATE"]
        AB["A/B Testing — Champion vs Custom<br/>Pick a winner for each question"]
    end

    subgraph S3["3. FEEDBACK"]
        FB["Describe the ideal response after each vote<br/>Saved to MLflow Evaluation Dataset"]
    end

    subgraph S4["4. PROMOTE"]
        CG["Candidate Gate: 80%+ approval"]
        AG["Automated Gate: judges vs champion"]
        HG["Human Gate: expert approval"]
        CG --> AG --> HG
    end

    subgraph S5["5. REPEAT"]
        MA["MemAlign improves judges from feedback<br/>Better judges, better gates, better prompts"]
    end

    S1 --> S2 --> S3 --> S4 --> S5
    S5 -.-> S1

    style S1 fill:#264653,color:#fff
    style S2 fill:#2a6f97,color:#fff
    style S3 fill:#468faf,color:#fff
    style S4 fill:#6a4c93,color:#fff
    style S5 fill:#1b998b,color:#fff
    style MT fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style ST fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style AB fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style FB fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style CG fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style AG fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style HG fill:#1a1a2e,color:#e0e0e0,stroke:#444
    style MA fill:#1a1a2e,color:#e0e0e0,stroke:#444
```
""")
                gr.Markdown("""### Three-Gate Promotion Pipeline

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'edgeLabelBackground': '#1a1a2e', 'lineColor': '#888'}}}%%
flowchart LR
    CP["Custom Prompt"] --> CG1

    subgraph CG["Candidate Gate"]
        CG1["80%+ approval<br/>on 3+ comparisons"]
    end

    subgraph AG["Automated Gate"]
        AG1["LLM judges score<br/>candidate vs champion"]
    end

    subgraph HG["Human Gate"]
        HG1["Domain expert<br/>reviews and approves"]
    end

    CG -->|"@candidate"| AG -->|"@challenger"| HG -->|"@champion"| LIVE["Serving live traffic"]

    DSPy["DSPy boost"] -.-> CG

    style CG fill:#264653,color:#e0e0e0
    style AG fill:#2a6f97,color:#e0e0e0
    style HG fill:#6a4c93,color:#e0e0e0
    style CP fill:#1a1a2e,color:#e0e0e0,stroke:#555
    style CG1 fill:#1a1a2e,color:#e0e0e0,stroke:#555
    style AG1 fill:#1a1a2e,color:#e0e0e0,stroke:#555
    style HG1 fill:#1a1a2e,color:#e0e0e0,stroke:#555
    style LIVE fill:#1b998b,color:#e0e0e0
    style DSPy fill:#1a1a2e,color:#e0e0e0,stroke:#555,stroke-dasharray: 5 5
```

---

### Quick Start

| Step | Where | What to do |
|------|-------|------------|
| 1 | **💬 Multi-Turn** | Select a portfolio in the sidebar, ask questions, explore the agent |
| 2 | **⚔️ Single-Turn** | Edit the system prompt, click "Generate All Cards" to see 6 insight analyses |
| 3 | **🔬 A/B Testing** | Click "Load from feedback dataset", then "Compare" to evaluate Champion vs Custom |
| 4 | **🔬 A/B Testing** | Vote on each comparison, describe the ideal response → saved to dataset |
| 5 | **📊 Data** | Review all feedback entries, refresh to see new ones |

### Portfolios Available

| ID | Name | Strategy | Manager |
|----|------|----------|---------|
| PF-ALPHA | Alpha Growth | Aggressive | Sarah Chen |
| PF-MERID | Meridian Income | Conservative | James OBrien |
| PF-GLOBE | Global Balanced | Balanced | Maria Santos |
| PF-EMRKT | Emerging Markets | Growth | Raj Patel |

Select a portfolio in the **sidebar** — it applies across all tabs.
""")

            # =============================================================
            # TAB 1 — Multi-Turn Playground
            # =============================================================
            with gr.Tab("💬 Multi-Turn"):

                # Header row — title left, clear button right
                with gr.Row():
                    with gr.Column(scale=8):
                        gr.Markdown("### 💬 Conversation")
                    with gr.Column(scale=1, min_width=50):
                        mt_clear = gr.Button("🗑️", variant="secondary", size="sm", min_width=40)

                # Chat — full height
                mt_chatbot = gr.Chatbot(
                    show_label=False, height=500,
                    placeholder="Select a question below to get started...",
                )

                # Follow-up suggestions — hidden until first response
                mt_followup_state = gr.State([])  # stores follow-up text list
                with gr.Row(visible=False) as mt_followup_row:
                    mt_fu_btns = [gr.Button("", variant="secondary", size="sm", visible=False) for _ in range(3)]

                # Quick questions — visible until first interaction
                with gr.Group(visible=True) as mt_quick_group:
                    gr.Markdown("**Quick Questions** — click to start", elem_classes=["mt-quick-label"])
                    with gr.Row():
                        mt_quick = [gr.Button(q, variant="secondary", size="sm") for q in MULTI_TURN_QUESTIONS[:3]]
                    with gr.Row():
                        mt_quick += [gr.Button(q, variant="secondary", size="sm") for q in MULTI_TURN_QUESTIONS[3:]]

                # Input bar at the bottom
                with gr.Row():
                    mt_input = gr.Textbox(
                        placeholder="Ask about the portfolio...",
                        show_label=False, lines=1, scale=8,
                    )
                    mt_send_btn = gr.Button("Send", variant="primary", scale=1, min_width=80)

                # ── Multi-Turn handlers ──

                def _mt_send_full(message, history, portfolio_choice, prompt=DEFAULT_PROMPT):
                    """Send a message — returns (input, history, followups, quick_visible, followup_visible, fu1, fu2, fu3)."""
                    if not message.strip():
                        # No change — keep everything as-is
                        fu_updates = [gr.update() for _ in range(3)]
                        return ["", history, [], gr.update(), gr.update()] + fu_updates
                    pid = _parse_portfolio_choice(portfolio_choice)
                    q = _portfolio_question(message, pid)
                    followup_prompt = prompt + "\n\nAt the end of your response, suggest 3 brief follow-up questions the analyst might ask next. Format them as a numbered list starting with 'Follow-up questions:'"
                    response = _query_custom(q, followup_prompt)
                    main_resp, followups = _parse_followups(response)
                    history = history or []
                    history.append({"role": "user", "content": message})
                    history.append({"role": "assistant", "content": main_resp})

                    # Hide quick questions, show follow-ups
                    has_followups = len(followups) > 0
                    fu_updates = []
                    for i in range(3):
                        if i < len(followups):
                            fu_updates.append(gr.update(value=followups[i], visible=True))
                        else:
                            fu_updates.append(gr.update(visible=False))

                    return [
                        "",                                    # mt_input
                        history,                               # mt_chatbot
                        followups,                             # mt_followup_state
                        gr.update(visible=False),              # mt_quick_group — hide
                        gr.update(visible=has_followups),      # mt_followup_row — show if followups
                    ] + fu_updates                             # mt_fu_btns[0..2]

                all_mt_outputs = [mt_input, mt_chatbot, mt_followup_state, mt_quick_group, mt_followup_row] + mt_fu_btns
                all_mt_inputs = [mt_input, mt_chatbot, sb_portfolio]

                mt_input.submit(_mt_send_full, all_mt_inputs, all_mt_outputs)
                mt_send_btn.click(_mt_send_full, all_mt_inputs, all_mt_outputs)

                # Quick question buttons — hide instantly, then send
                def _make_quick_handler(question_text):
                    def handler(history, portfolio_choice):
                        return _mt_send_full(question_text, history, portfolio_choice)
                    return handler

                for btn, q in zip(mt_quick, MULTI_TURN_QUESTIONS):
                    btn.click(
                        lambda: gr.update(visible=False),
                        outputs=[mt_quick_group],
                    ).then(
                        _make_quick_handler(q),
                        [mt_chatbot, sb_portfolio],
                        all_mt_outputs,
                    )

                # Follow-up buttons — send the follow-up text
                def _make_followup_handler(idx):
                    def handler(followups, history, portfolio_choice):
                        if idx < len(followups):
                            return _mt_send_full(followups[idx], history, portfolio_choice)
                        fu_updates = [gr.update() for _ in range(3)]
                        return ["", history, followups, gr.update(), gr.update()] + fu_updates
                    return handler

                for i, fu_btn in enumerate(mt_fu_btns):
                    fu_btn.click(
                        _make_followup_handler(i),
                        [mt_followup_state, mt_chatbot, sb_portfolio],
                        all_mt_outputs,
                    )

                # Clear — reset everything, show quick questions again
                def _mt_clear():
                    fu_updates = [gr.update(visible=False) for _ in range(3)]
                    return [
                        "",                               # mt_input
                        [],                               # mt_chatbot
                        [],                               # mt_followup_state
                        gr.update(visible=True),          # mt_quick_group — show again
                        gr.update(visible=False),         # mt_followup_row — hide
                    ] + fu_updates

                mt_clear.click(_mt_clear, outputs=all_mt_outputs)

            # =============================================================
            # TAB 2 — Single-Turn Playground
            # =============================================================
            with gr.Tab("⚔️ Single-Turn"):
                with gr.Row():
                    # Left: prompt editor
                    with gr.Column(scale=1):
                        gr.Markdown("### ✏️ Custom System Prompt")
                        st_prompt = gr.Textbox(
                            value=DEFAULT_PROMPT, lines=16, show_label=False,
                            placeholder="Edit system prompt here...",
                        )
                        with gr.Row():
                            st_save = gr.Button("💾 Save & Generate", variant="primary")
                            st_reset = gr.Button("🔄 Reset")

                    # Right: insight cards
                    with gr.Column(scale=2):
                        gr.Markdown("### 📋 Insight Cards")
                        st_gen = gr.Button("🔄 Generate All Cards", variant="primary")
                        st_cards = []
                        for ci, card in enumerate(INSIGHT_CARD_TEMPLATES):
                            gr.Markdown(f"#### {card['icon']} {card['title']}")
                            md = gr.Markdown("*Click 'Generate All Cards' to populate*")
                            st_cards.append(md)

                def _st_generate(portfolio_choice, prompt):
                    """Generator — yields one card at a time so the UI updates progressively."""
                    pid = _parse_portfolio_choice(portfolio_choice)
                    results = []
                    total = len(INSIGHT_CARD_TEMPLATES)
                    for i, card in enumerate(INSIGHT_CARD_TEMPLATES):
                        q = _portfolio_question(card["question"], pid)
                        try:
                            resp = _query_custom(q, prompt)
                        except Exception as e:
                            resp = f"Error: {e}"
                        _pg_cards[card["id"]] = resp
                        results.append(resp)
                        # Yield partial results — completed cards + "generating..." for remaining
                        partial = list(results)
                        for remaining in range(total - len(results)):
                            partial.append(f"*Generating card {len(results) + remaining + 1} of {total}...*")
                        yield partial

                def _st_disable_btns():
                    return (
                        gr.update(value="Generating...", interactive=False),
                        gr.update(interactive=False),
                    ) + tuple(f"*Waiting...*" for _ in st_cards)

                def _st_enable_btns():
                    return (
                        gr.update(value="🔄 Generate All Cards", interactive=True),
                        gr.update(value="💾 Save & Generate", interactive=True),
                    )

                btn_outputs = [st_gen, st_save] + st_cards

                st_gen.click(
                    _st_disable_btns, outputs=btn_outputs,
                ).then(
                    _st_generate, [sb_portfolio, st_prompt], st_cards,
                ).then(
                    _st_enable_btns, outputs=[st_gen, st_save],
                )
                st_save.click(
                    _st_disable_btns, outputs=btn_outputs,
                ).then(
                    _st_generate, [sb_portfolio, st_prompt], st_cards,
                ).then(
                    _st_enable_btns, outputs=[st_gen, st_save],
                )
                st_reset.click(lambda: DEFAULT_PROMPT, outputs=[st_prompt])

            # =============================================================
            # TAB 3 — A/B Testing
            # =============================================================
            with gr.Tab("🔬 A/B Testing"):

                # Data source — load from feedback dataset
                with gr.Row():
                    with gr.Column(scale=5):
                        ab_source_md = gr.Markdown("Click **Load** to pull evaluation items from assessed traces")
                    with gr.Column(scale=2):
                        ab_load_dataset_btn = gr.Button("🔄 Load from assessed traces", variant="primary", size="sm")

                ab_progress_md = gr.Markdown("*Load the feedback dataset to begin*")
                ab_question_md = gr.Textbox(
                    value="",
                    label="Question being evaluated",
                    lines=3, interactive=False,
                )

                ab_compare_btn = gr.Button("Compare ▶", variant="primary")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 🏆 Champion")
                        ab_champ_out = gr.Markdown("*Run comparison to see response*")
                        ab_champ_btn = gr.Button("🏆 Champion Wins", interactive=False)
                    with gr.Column():
                        gr.Markdown("### ✏️ Custom Prompt")
                        ab_cust_out = gr.Markdown("*Run comparison to see response*")
                        ab_cust_btn = gr.Button("✏️ Custom Wins", interactive=False)

                ab_neither_btn = gr.Button("🤝 Neither — both need improvement", interactive=False)

                # Feedback section — appears after voting
                with gr.Group(visible=False) as ab_feedback_group:
                    gr.Markdown("### 💬 What should the ideal response look like?")
                    ab_feedback_text = gr.Textbox(
                        placeholder="Describe what the ideal response should include (e.g., 'Should cite specific exposure amounts and risk tiers without recommending actions')...",
                        lines=3, show_label=False,
                    )
                    with gr.Row():
                        ab_feedback_submit = gr.Button("Save to eval dataset", variant="primary", size="sm")
                        ab_feedback_skip = gr.Button("Skip", variant="secondary", size="sm")
                    ab_feedback_status = gr.Markdown("")

                gr.Markdown("---")
                with gr.Row():
                    ab_prev = gr.Button("← Previous")
                    ab_status = gr.Markdown("")
                    ab_next = gr.Button("Next →")

                # ── A/B event handlers ──

                def _ab_disable():
                    return (
                        gr.update(value="Comparing...", interactive=False),  # ab_compare_btn
                        "*Querying champion...*",                            # ab_champ_out
                        "*Querying custom prompt...*",                       # ab_cust_out
                    )

                def _ab_compare():
                    idx = _ab_index[0]
                    card = AB_EVAL_SET[idx]
                    champ = _query_endpoint(card["question"])
                    cust = _query_custom(card["question"], DEFAULT_PROMPT)
                    _ab_responses[card["id"]] = {"champion": champ, "candidate": cust}
                    _ab_trace_ids[card["id"]] = _log_ab_traces(card["id"], card["question"], champ, cust)
                    progress = f"**{idx + 1} of {len(AB_EVAL_SET)}** — {card['icon']} **{card['title']}** — {len(_ab_results)} reviewed"
                    return (
                        champ, cust,
                        gr.update(interactive=True), gr.update(interactive=True), gr.update(interactive=True),
                        progress,
                    )

                def _ab_enable_compare():
                    return gr.update(value="Compare ▶", interactive=True)

                ab_compare_btn.click(
                    _ab_disable,
                    outputs=[ab_compare_btn, ab_champ_out, ab_cust_out],
                ).then(
                    _ab_compare,
                    outputs=[ab_champ_out, ab_cust_out, ab_champ_btn, ab_cust_btn, ab_neither_btn, ab_progress_md],
                ).then(
                    _ab_enable_compare,
                    outputs=[ab_compare_btn],
                )

                _last_vote: dict[str, str] = {}  # tracks current vote for feedback submit

                def _ab_vote(winner: str):
                    """Record vote, show feedback section (don't advance yet)."""
                    idx = _ab_index[0]
                    _ab_results[idx] = winner
                    if winner == "custom":
                        _votes["candidate"]["up"] += 1
                    else:
                        _votes["candidate"]["down"] += 1
                    card = AB_EVAL_SET[idx]
                    tids = _ab_trace_ids.get(card["id"], {})
                    if tids:
                        _log_vote_feedback(tids, winner, card["title"])
                    _last_vote["winner"] = winner
                    _last_vote["question"] = card["question"]
                    _last_vote["idx"] = idx
                    gate = _gate_md()
                    winner_label = "✏️ Custom" if winner == "custom" else ("🏆 Champion" if winner == "champion" else "🤝 Neither")
                    return (
                        gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False),
                        gate,
                        gr.update(visible=True),  # show feedback group
                        "",                        # clear feedback text
                        f"You picked **{winner_label}**. What should the ideal response include?",
                    )

                ab_vote_outputs = [ab_champ_btn, ab_cust_btn, ab_neither_btn, sb_gate_md, ab_feedback_group, ab_feedback_text, ab_feedback_status]
                for btn, winner in [(ab_champ_btn, "champion"), (ab_cust_btn, "custom"), (ab_neither_btn, "neither")]:
                    btn.click(
                        lambda w=winner: _ab_vote(w),
                        outputs=ab_vote_outputs,
                    )

                def _ab_advance():
                    """Advance to the next card — called after feedback submit or skip."""
                    idx = _ab_index[0]
                    if idx < len(AB_EVAL_SET) - 1:
                        _ab_index[0] = idx + 1
                    new_card = AB_EVAL_SET[_ab_index[0]]
                    progress = f"**{_ab_index[0] + 1} of {len(AB_EVAL_SET)}** — {new_card['icon']} **{new_card['title']}** — {len(_ab_results)} reviewed"
                    question = new_card["question"]
                    return (
                        "*Run comparison to see response*",
                        "*Run comparison to see response*",
                        progress, question,
                        gr.update(visible=False),  # hide feedback group
                        "",                         # clear feedback status
                    )

                ab_advance_outputs = [ab_champ_out, ab_cust_out, ab_progress_md, ab_question_md, ab_feedback_group, ab_feedback_status]

                def _ab_submit_feedback(comment: str):
                    """Log expected response as expectation on the trace, then advance."""
                    idx = _last_vote.get("idx", 0)
                    winner = _last_vote.get("winner", "")
                    # Get the trace ID for the winning variant
                    card = AB_EVAL_SET[idx] if idx < len(AB_EVAL_SET) else {}
                    trace_ids = _ab_trace_ids.get(card.get("id", ""), {})
                    # Log expectation on the candidate trace (custom prompt response)
                    tid = trace_ids.get("candidate", trace_ids.get("champion", ""))
                    if comment.strip() and tid:
                        status = _save_feedback_on_trace(tid, comment.strip())
                    else:
                        status = "Skipped (no comment or no trace)"
                    return status

                ab_feedback_submit.click(
                    _ab_submit_feedback, [ab_feedback_text], [ab_feedback_status],
                ).then(
                    _ab_advance, outputs=ab_advance_outputs,
                )
                ab_feedback_skip.click(
                    _ab_advance, outputs=ab_advance_outputs,
                )

                def _ab_nav(direction: int):
                    _ab_index[0] = max(0, min(len(AB_EVAL_SET) - 1, _ab_index[0] + direction))
                    card = AB_EVAL_SET[_ab_index[0]]
                    resp = _ab_responses.get(card["id"], {})
                    progress = f"**{_ab_index[0] + 1} of {len(AB_EVAL_SET)}** — {card['icon']} **{card['title']}** — {len(_ab_results)} reviewed"
                    question = card["question"]
                    already_voted = _ab_index[0] in _ab_results
                    return (
                        resp.get("champion", "*Run comparison to see response*"),
                        resp.get("candidate", "*Run comparison to see response*"),
                        gr.update(interactive=not already_voted and bool(resp)),
                        gr.update(interactive=not already_voted and bool(resp)),
                        gr.update(interactive=not already_voted and bool(resp)),
                        progress, question,
                    )

                ab_nav_outputs = [ab_champ_out, ab_cust_out, ab_champ_btn, ab_cust_btn, ab_neither_btn, ab_progress_md, ab_question_md]
                ab_prev.click(lambda: _ab_nav(-1), outputs=ab_nav_outputs)
                ab_next.click(lambda: _ab_nav(1), outputs=ab_nav_outputs)

                # Load eval set from feedback dataset
                def _ab_load_from_dataset():
                    status = _refresh_ab_eval_set()
                    if AB_EVAL_SET:
                        first = AB_EVAL_SET[0]
                        progress = f"**1 of {len(AB_EVAL_SET)}** — {first['icon']} **{first['title']}** — 0 reviewed"
                        question = first["question"]
                    else:
                        progress = "No items loaded"
                        question = ""
                    return (
                        status,
                        progress, question,
                        "*Run comparison to see response*",
                        "*Run comparison to see response*",
                        gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False),
                        _gate_md(),
                        gr.update(visible=False), "",
                    )

                ab_load_outputs = [
                    ab_source_md, ab_progress_md, ab_question_md,
                    ab_champ_out, ab_cust_out,
                    ab_champ_btn, ab_cust_btn, ab_neither_btn,
                    sb_gate_md,
                    ab_feedback_group, ab_feedback_status,
                ]
                ab_load_dataset_btn.click(_ab_load_from_dataset, outputs=ab_load_outputs)

            # =============================================================
            # TAB 4 — Data
            # =============================================================
            with gr.Tab("📊 Data"):
                gr.Markdown("### Assessed Traces")
                gr.Markdown("Traces with human feedback from A/B Testing — the source of truth for evaluation datasets.")

                def _data_table():
                    items = _load_assessed_traces()
                    if not items:
                        err = _last_load_error[0] if _last_load_error else "No assessed traces found"
                        return (
                            f"**No assessed traces yet.**\n\n"
                            f"Debug: {err}\n\n"
                            f"Go to **A/B Testing** → Compare → Vote → Submit feedback to create assessed traces."
                        )
                    lines = ["| # | Question | Winner | Has Expected Response |", "|---|----------|--------|---------------------|"]
                    for i, item in enumerate(items):
                        q = item["question"][:55] + ("..." if len(item["question"]) > 55 else "")
                        winner = item.get("winner", "—")
                        has_exp = "✓" if item.get("expected_response") else "—"
                        lines.append(f"| {i + 1} | {q} | {winner} | {has_exp} |")
                    with_exp = sum(1 for it in items if it.get("expected_response"))
                    lines.append(f"\n**{len(items)} traces** with human feedback, **{with_exp}** with expected responses")
                    return "\n".join(lines)

                data_table_md = gr.Markdown("Loading...")
                with gr.Row():
                    data_refresh = gr.Button("🔄 Refresh traces")
                    data_build_btn = gr.Button("📦 Build Eval Dataset", variant="primary")
                data_refresh.click(_data_table, outputs=[data_table_md])
                app.load(_data_table, outputs=[data_table_md])

                data_build_status = gr.Markdown("")

                def _on_build_dataset():
                    return _build_dataset_from_traces()

                data_build_btn.click(_on_build_dataset, outputs=[data_build_status])

                gr.Markdown("---")
                gr.Markdown("### How feedback flows")
                gr.Markdown(
                    "1. **A/B Testing** — compare Champion vs Custom, vote on winners → feedback logged on **traces**\n"
                    "2. **Submit comment** — describe the ideal response → logged as **expectation** on the trace\n"
                    "3. **This tab** — shows all traces with human assessments\n"
                    "4. **Build Eval Dataset** — merges assessed traces into MLflow **Dataset** (visible in Evaluation > Datasets)\n"
                    "5. **Register** (sidebar) — runs `mlflow.genai.evaluate()` against the dataset"
                )

        # ── Sidebar button handlers (defined after tabs so outputs exist) ──
        def _run_register():
            """Run the Automated Gate: evaluate custom prompt vs champion on feedback dataset."""
            if not _can_register():
                return _gate_md()

            items = _load_eval_set_from_dataset()
            if not items:
                return "No feedback dataset to evaluate against. Submit feedback in A/B Testing first."

            try:
                host, headers = _dataset_auth_headers()
                results = {"champion_correct": 0, "custom_correct": 0, "total": 0}

                for item in items:
                    q = item["question"]
                    expected = item.get("expected_response", "")
                    if not expected:
                        continue

                    # Query champion
                    champ_resp = _query_endpoint(q)
                    # Query custom (uses DEFAULT_PROMPT — the candidate prompt)
                    custom_resp = _query_custom(q, DEFAULT_PROMPT)

                    # Score both with a simple judge call
                    for label, resp in [("champion", champ_resp), ("custom", custom_resp)]:
                        judge_prompt = (
                            f"You are a judge. Is this response correct and complete?\n\n"
                            f"Question: {q}\n"
                            f"Expected: {expected}\n"
                            f"Response: {resp}\n\n"
                            f"Answer ONLY 'yes' or 'no'."
                        )
                        try:
                            judge_resp = http_requests.post(
                                f"{host}/serving-endpoints/{ENDPOINT_NAME}/invocations",
                                headers=headers,
                                json={"dataframe_records": [{"messages": [
                                    {"role": "system", "content": "You are a strict evaluator. Answer only yes or no."},
                                    {"role": "user", "content": judge_prompt},
                                ]}]},
                                timeout=60,
                            )
                            preds = judge_resp.json().get("predictions", [])
                            answer = ""
                            if isinstance(preds, list) and preds:
                                first = preds[0]
                                answer = (first.get("content", str(first)) if isinstance(first, dict) else str(first)).lower()
                            if "yes" in answer:
                                results[f"{label}_correct"] += 1
                        except Exception:
                            pass
                    results["total"] += 1

                if results["total"] == 0:
                    return "No questions with expected responses to evaluate."

                champ_pct = results["champion_correct"] / results["total"] * 100
                custom_pct = results["custom_correct"] / results["total"] * 100
                passed = custom_pct > champ_pct

                status = (
                    f"### Automated Gate Results\n\n"
                    f"| Variant | Correct | Score |\n"
                    f"|---------|---------|-------|\n"
                    f"| Champion | {results['champion_correct']}/{results['total']} | {champ_pct:.0f}% |\n"
                    f"| Custom | {results['custom_correct']}/{results['total']} | {custom_pct:.0f}% |\n\n"
                )

                if passed:
                    status += "**PASSED** — Custom beats Champion. Ready for `mlflow.register_model()` via CLI."
                else:
                    status += f"**FAILED** — Custom ({custom_pct:.0f}%) did not beat Champion ({champ_pct:.0f}%). Iterate on the prompt."

                return status

            except Exception as e:
                return f"Evaluation error: {e}"

        def _disable_register():
            return gr.update(value="Evaluating...", interactive=False)

        def _enable_register(result):
            return gr.update(value="📋 Register", interactive=True), result

        sb_reg_btn.click(
            _disable_register, outputs=[sb_reg_btn],
        ).then(
            _run_register, outputs=[sb_gate_md],
        ).then(
            lambda result: gr.update(value="📋 Register", interactive=True),
            [sb_gate_md], [sb_reg_btn],
        )

        sb_dspy_btn.click(
            lambda: "⬜ DSPy — trigger from CLI: `uv run python -m risk_agent.optimize`",
            outputs=[sb_gate_md],
        )

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger.info("Starting Coliseum Playground...")
    try:
        import gradio as _gr
        logger.info("Gradio version: %s", _gr.__version__)
    except Exception:
        pass
    app = build_app()
    port = int(os.environ.get("APP_PORT", 8000))
    logger.info("Launching on port %d", port)
    app.launch(server_name="0.0.0.0", server_port=port)
