---
description: "[Stage 4] Add MLflow tracing with @mlflow.trace and start_span() for full observability of agent invocations"
---

# Add Tracing — MLflow Observability for Agent Invocations

Add MLflow tracing to the agent so every invocation is fully observable: which tools were called, how long each step took, how many tokens were used, and whether the response was grounded in tool results.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 3 (add-tools), the learner has:
- A working ResponsesAgent with 3 UC function tools
- Data-backed responses from Gold tables
- No observability — if a response is wrong, there's no way to diagnose WHY

This stage adds the instrumentation that makes debugging and evaluation possible.

---

## Instructions

---

### Step 1 — Explain MLflow Tracing

**What are traces and spans?**

A **trace** is the end-to-end record of a single agent invocation — from the user's question to the final response. A **span** is one operation within that trace.

```
Trace: "What is the risk tier for Acme Corp?"
│
├── Span: parse_request (0.2ms)
│   └── Extracted: counterparty="Acme Corp"
│
├── Span: llm_call_1 — tool selection (450ms, 320 tokens)
│   └── Selected: get_risk_exposure(counterparty="Acme Corp")
│
├── Span: tool_execution — get_risk_exposure (120ms)
│   └── Result: {risk_tier: "Medium", exposure: 2500000, var_95: 180000}
│
├── Span: llm_call_2 — summarization (380ms, 280 tokens)
│   └── Generated: "Acme Corp is classified as Medium risk..."
│
└── Span: total (952ms, 600 tokens)
```

**Why trace?**
- **Debugging**: Response wrong? Check which tool was called and what data came back.
- **Performance**: Which span is the bottleneck — LLM latency or tool execution?
- **Cost**: How many tokens per invocation? Which questions are expensive?
- **Evaluation**: Traces feed directly into `mlflow.evaluate()` in Stage 5 — the judges inspect trace data to score groundedness.

Present the span types:

| Span Type | What It Captures | Example |
|-----------|-----------------|---------|
| LLM | Model call, prompt, completion, token count | Tool selection call (450ms, 320 tokens) |
| TOOL | Tool name, input params, output, latency | get_risk_exposure("Acme Corp") → 120ms |
| CHAIN | Orchestration logic, routing decisions | predict() overall flow |
| RETRIEVER | Data retrieval operations | Not used here (we use tools, not RAG) |

Use `AskUserQuestion` to confirm the learner understands the trace/span model before seeing code.

---

### Step 2 — Add Tracing to Agent

Read and display the tracing additions in the agent code. Walk through each instrumentation point:

**Level 1: `@mlflow.trace` on predict()**

```python
@mlflow.trace
def predict(self, context, request):
    ...
```

This automatically creates a root trace for every invocation. MLflow captures: input messages, output response, total duration, and any child spans.

**Level 2: `start_span()` for Tool Execution**

```python
with mlflow.start_span(name="tool_execution", span_type="TOOL") as span:
    span.set_attribute("tool_name", tool_call.name)
    span.set_attribute("tool_input", json.dumps(tool_call.arguments))
    result = execute_uc_function(tool_call.name, tool_call.arguments)
    span.set_attribute("tool_output", str(result))
```

Each tool call gets its own span with: tool name, input parameters, output data, and execution time.

**Level 3: Custom Attributes**

```python
span.set_attribute("token_count", response.usage.total_tokens)
span.set_attribute("latency_ms", elapsed_ms)
span.set_attribute("model_name", self.config.llm_endpoint)
```

Custom attributes let you filter and aggregate in the MLflow UI — find all invocations that used more than 1000 tokens, or all calls to a specific tool.

**Key insight:** Tracing is additive — it doesn't change the agent's behavior. The same predict() function runs the same way, but now every step is recorded.

Use `AskUserQuestion` to confirm the learner understands each tracing level.

---

### Step 3 — Run Agent with Tracing

Set the MLflow experiment and run several queries to generate traces:

```bash
cd <project-dir>
uv run python -c "
import mlflow

# Set the experiment so traces are grouped together
mlflow.set_experiment('/Shared/risk-agent')

# Query 1: Requires get_risk_exposure
result = mlflow.models.predict(
    'src/risk_agent',
    model_input={
        'messages': [{'role': 'user', 'content': 'What is the risk tier for Acme Corp?'}]
    }
)
print('Query 1:', result)

# Query 2: Requires get_financial_ratios
result = mlflow.models.predict(
    'src/risk_agent',
    model_input={
        'messages': [{'role': 'user', 'content': 'What are the financial ratios for Global Trading Inc?'}]
    }
)
print('Query 2:', result)

# Query 3: Requires get_portfolio_summary
result = mlflow.models.predict(
    'src/risk_agent',
    model_input={
        'messages': [{'role': 'user', 'content': 'Give me a portfolio risk overview'}]
    }
)
print('Query 3:', result)
"
```

After running, confirm traces were recorded:

```bash
uv run python -c "
import mlflow
mlflow.set_experiment('/Shared/risk-agent')
traces = mlflow.search_traces(experiment_names=['/Shared/risk-agent'])
print(f'Total traces: {len(traces)}')
print(traces[['request_id', 'status', 'execution_time_ms']].to_string())
"
```

Present the trace summary:

| Trace # | Question | Status | Duration (ms) | Tools Called |
|---------|----------|--------|---------------|-------------|
| 1 | Risk tier for Acme Corp | OK | ~950 | get_risk_exposure |
| 2 | Financial ratios for Global Trading | OK | ~900 | get_financial_ratios |
| 3 | Portfolio overview | OK | ~850 | get_portfolio_summary |

Use `AskUserQuestion` to confirm traces are being captured.

---

### Step 4 — View Traces in MLflow UI

Guide the user to the MLflow experiment page:

1. Open the Databricks workspace in a browser
2. Navigate to **Experiments** > `/Shared/risk-agent`
3. Click on any trace to see the **waterfall view**

**What to look for in the waterfall:**

```
┌─ predict() ──────────────────────────────── 952ms ──┐
│                                                      │
│  ┌─ llm_call_1 (tool selection) ─── 450ms ─┐       │
│  └──────────────────────────────────────────┘       │
│                                                      │
│  ┌─ tool_execution ──────────────── 120ms ─┐        │
│  │  tool: get_risk_exposure                 │        │
│  │  input: {counterparty: "Acme Corp"}     │        │
│  │  output: {risk_tier: "Medium", ...}     │        │
│  └──────────────────────────────────────────┘       │
│                                                      │
│  ┌─ llm_call_2 (summarization) ──── 380ms ─┐       │
│  └──────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────┘
```

**Teaching moment — where is the time spent?**
- LLM calls dominate (~85% of total time). Tool execution is fast because UC functions run on the SQL warehouse.
- If you see slow tool execution, the SQL warehouse may be cold-starting.
- Token counts help estimate serving costs — more tokens = more cost per invocation.

**If the MLflow UI is not available locally**, show traces programmatically:

```bash
uv run python -c "
import mlflow
mlflow.set_experiment('/Shared/risk-agent')
traces = mlflow.search_traces(experiment_names=['/Shared/risk-agent'])
for _, trace in traces.iterrows():
    print(f'Request: {trace.request_id}')
    print(f'  Duration: {trace.execution_time_ms}ms')
    print(f'  Status: {trace.status}')
    print()
"
```

Use `AskUserQuestion` to confirm the learner can navigate the trace data.

---

### Step 5 — Summary

| Component | Status | Details |
|-----------|--------|---------|
| @mlflow.trace decorator | ✓ Added | Root trace on predict() |
| start_span() for tools | ✓ Added | Individual spans per tool call |
| Custom attributes | ✓ Added | token_count, latency_ms, tool_name |
| MLflow experiment | ✓ Created | `/Shared/risk-agent` with 3+ traces |
| Waterfall view | ✓ Reviewed | LLM calls dominate latency |

**What the agent has now:**
- Full observability for every invocation
- Trace waterfall showing timing breakdown
- Token counts for cost estimation
- Tool call audit trail (which tool, what input, what output)

**Why this matters for the next stages:**
- **Stage 5 (Evaluation):** `mlflow.evaluate()` uses traces to judge groundedness — it checks if the LLM's response matches the tool output in the trace
- **Stage 6 (Optimization):** DSPy uses evaluation scores (which depend on traces) to find better prompts

Without tracing, evaluation is blind — you'd be scoring responses without knowing what data the agent actually retrieved.

**Next:** Run `/silver-databricks-agents:evaluate-agent` to generate a synthetic evaluation set and run `mlflow.evaluate()` with LLM judges for correctness, groundedness, and relevance.

---

After presenting the summary, use `AskUserQuestion` to offer the next stage:

- **"Continue to Stage 5 — Evaluate Agent" (Recommended)** — description: "Run `/silver-databricks-agents:evaluate-agent` now"
- **"Stop here"** — description: "I'll continue later"

If the user chooses to continue, invoke the next skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:evaluate-agent" })`.
