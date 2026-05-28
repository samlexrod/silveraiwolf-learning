---
description: "[Stage 2] Create a ResponsesAgent with predict() and predict_stream(), test locally with mlflow.models.predict()"
---

# Author Agent — ResponsesAgent Architecture

Walk through the ResponsesAgent architecture, understand the predict() and predict_stream() contracts, and test the agent locally before adding tools or tracing.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 1 (scaffold-setup), the learner has:
- Project scaffolded with all source code
- Dependencies installed (mlflow, databricks-sdk)
- Databricks credentials configured and authenticated
- Gold tables populated (batch pipeline or bootstrap)

The agent code exists in the scaffold but hasn't been examined or tested yet.

---

## Instructions

---

### Step 1 — Explain Agent Approaches

Before diving into code, explain WHY `ResponsesAgent` is the recommended approach. Present a comparison table:

| Approach | Era | Status | Key Trait |
|----------|-----|--------|-----------|
| **ResponsesAgent** | 2025+ | **Recommended** | Built on OpenAI Responses API format. Native tool calling, structured outputs, streaming. Minimal boilerplate — Databricks handles the execution loop. |
| **ChatAgent** | 2023–2024 | **Deprecated** | Built on Chat Completions API. You manage the tool execution loop yourself. More code, more bugs, same result. |
| **PythonModel** | 2022–2023 | **Legacy** | Raw MLflow model. No agent abstractions at all — you implement everything from scratch. Maximum flexibility, maximum pain. |

**Why ResponsesAgent wins:**
- Databricks manages the tool execution loop (LLM calls tool -> executes -> feeds result back -> LLM responds). You don't write that loop.
- Native streaming support via `predict_stream()` — no extra work.
- Parameterized via `model_config.yaml` — swap LLMs, change temperatures, update system prompts without touching code.
- Direct integration with Unity Catalog functions as governed tools.

Use `AskUserQuestion` to check if the learner has questions about the agent landscape before continuing.

---

### Step 2 — Walk Through agent.py

Read the `src/risk_agent/agent.py` file from the scaffolded project and display it. Walk through each section:

**Section 1: Class Definition**
```python
class RiskAgent(ResponsesAgent):
```
- Inherits from `mlflow.pyfunc.ResponsesAgent` — this is the base class that provides the predict/predict_stream contract.
- MLflow knows how to serve, evaluate, and trace anything that extends this class.

**Section 2: `__init__` and Configuration Loading**
```python
def __init__(self):
    config = mlflow.models.ModelConfig()
```
- `ModelConfig()` reads `model_config.yaml` at load time. This is the key to parameterization — the agent's behavior is driven by config, not hardcoded values.
- The config includes: LLM endpoint name, temperature, system prompt, max tokens.

**Section 3: `predict()` Contract**
```python
def predict(self, context, request: ChatCompletionRequest) -> ChatCompletionResponse:
```
- Input: `ChatCompletionRequest` — contains `messages` (the conversation history).
- Output: `ChatCompletionResponse` — the agent's response, including any tool calls and final text.
- This is the synchronous path — the full response is returned at once.

**Section 4: `predict_stream()` Contract**
```python
def predict_stream(self, context, request: ChatCompletionRequest) -> Generator[ChatCompletionChunk]:
```
- Same input, but yields `ChatCompletionChunk` objects as they arrive.
- The Databricks serving endpoint uses this for real-time streaming to the UI.
- You get streaming "for free" by implementing this method — the framework handles chunking.

**Key insight:** The agent at this stage has NO tools. It can only respond using the LLM's built-in knowledge. It cannot query Gold tables yet — that comes in Stage 3.

Use `AskUserQuestion` to pause and check for questions about the agent architecture.

---

### Step 3 — Understand model_config.yaml (The Separation of Behavior from Code)

**Goal:** Understand why the agent's behavior is driven by a YAML config file instead of hardcoded values — and how this single design decision unlocks DSPy optimization, A/B testing, and the entire Coliseum promotion pipeline later.

Read and display the `model_config.yaml` file. Walk through each field, explaining not just *what* it does but *why it matters for what comes later*:

```yaml
llm_endpoint: "databricks-meta-llama-3-3-70b-instruct"  # Which LLM to use
temperature: 0.1                                          # Low = deterministic, high = creative
max_tokens: 1024                                          # Response length limit
system_prompt: |                                          # The agent's personality and instructions
  You are a financial risk analyst assistant...
```

Field-by-field breakdown:

| Field | What it controls | Who changes it later |
|-------|-----------------|---------------------|
| `llm_endpoint` | Which Foundation Model the agent calls | **You** — swap Llama → DBRX → GPT-4 by editing this line. Stage 7 registers different versions with different models. |
| `temperature` | Randomness of responses (0.1 = near-deterministic) | **DSPy** (Stage 6) — the optimizer tunes this automatically. No code change needed to test `0.05` vs `0.15`. |
| `max_tokens` | Response length cap | **You** — different use cases need different lengths (chat UI vs. report generation). |
| `system_prompt` | The agent's persona, rules, and response format | **DSPy** (Stage 6) rewrites this field with optimized prompts. **Domain experts** (Stage 11) write competing prompts here via the Coliseum Playground. The entire promotion pipeline depends on this field living in config, not code. |

**How it works — trace the path from YAML to running agent:**

Read and display `src/risk_agent/config.py` from the scaffolded project. Then walk through the chain step by step:

1. **`model_config.yaml`** holds the values (you just saw this file)
2. **`config.py` → `load_model_config()`** reads the YAML and returns a dict:
   ```python
   # config.py
   mc = ModelConfig(development_config="model_config.yaml")
   config = mc.to_dict()  # {"llm_endpoint": "databricks-meta-...", "system_prompt": "You are a...", ...}
   ```
3. **`agent.py` → `__init__()`** calls `load_model_config()` and stores the values:
   ```python
   # agent.py
   self.config = load_model_config()
   self.model = self.config["llm_endpoint"]       # ← from YAML
   self.system_prompt = self.config["system_prompt"]  # ← from YAML
   self.temperature = self.config.get("temperature", 0.1)  # ← from YAML
   ```
4. **`predict()`** uses those stored values when it calls the LLM — no hardcoded strings anywhere.

```
  model_config.yaml          config.py               agent.py
 ┌───────────────────┐     ┌─────────────────┐     ┌─────────────────────┐
 │ llm_endpoint: ... │────>│ load_model_     │────>│ self.model = ...    │
 │ temperature: 0.1  │     │   config()      │     │ self.system_prompt  │
 │ system_prompt: ...│     │ returns dict    │     │ self.temperature    │
 └───────────────────┘     └─────────────────┘     └─────────────────────┘
   Edit this file             Reads at startup        Uses the values
   to change behavior         (no code changes)       in predict()
```

**Why this matters:** Because `agent.py` never hardcodes the LLM name or prompt — it always reads from config — you can change *what the agent does* by editing one YAML file. The code stays frozen after Stage 2. Everything that changes flows through this config. That's what makes it possible for:
- **DSPy** to optimize prompts programmatically (Stage 6) — it writes a new `system_prompt` to this file
- **The Coliseum** to register competing prompt variants as model versions (Stage 7) — each version has a different config
- **Domain experts** to write and test custom prompts without touching code (Stage 11) — they edit prompts in the Playground UI, which produces a new config

Use `AskUserQuestion` to confirm understanding before testing.

---

### Step 4 — Test Locally

Run the agent locally using `mlflow.models.predict()`. This is the standard way to test an MLflow agent without deploying it:

```bash
cd <project-dir>
uv run python -c "
import mlflow
result = mlflow.models.predict(
    'src/risk_agent',
    model_input={
        'messages': [
            {'role': 'user', 'content': 'What financial risk tools do you have?'}
        ]
    }
)
print(result)
"
```

**Show the full response** to the user in a quoted block (e.g., `> Agent: "I have access to the following tools: ..."`). Label it clearly as **Test 1 — General Question**. Explain: the agent responds with general LLM knowledge about its tools, but it CANNOT query the Gold tables yet.

Then try a second question that would require real data. Label it as **Test 2 — Data Question (requires tools)**:

```bash
uv run python -c "
import mlflow
result = mlflow.models.predict(
    'src/risk_agent',
    model_input={
        'messages': [
            {'role': 'user', 'content': 'What is the risk tier for Acme Corp?'}
        ]
    }
)
print(result)
"
```

**Show the full output** — including the error or hallucinated response — in a quoted block. Explain what happened: the LLM tried to call `get_risk_exposure` (the right tool!), but the tool execution failed because the SDK wrappers aren't wired to the SQL warehouse yet.

After showing both raw outputs, present the comparison table:

| Question | Result | Why |
|----------|--------|-----|
| "What financial risk tools do you have?" | ✅ Answered | LLM reads the tool definitions |
| "What is the risk tier for Acme Corp?" | ❌ Failed (expected!) | LLM called `get_risk_exposure` → tool can't query yet |

Explain the key insight: the agent is architecturally sound — it correctly identifies which tool to use. It just can't execute the call yet. Stage 3 fixes this.

Then present the execution model diagram so the learner understands what ran where:

```
  Your machine                          Databricks cloud
 ┌──────────────┐                      ┌────────────────────────┐
 │ uv run python│                      │ Foundation Model       │
 │              │───── HTTPS ────────→│ (Llama 3.3 70B)       │
 │ agent.py     │                      │ /serving-endpoints/    │
 │ (PythonModel)│←──── JSON ──────────│                        │
 └──────────────┘                      └────────────────────────┘

 LOCAL:  agent.py, predict(), tool dispatch, config loading
 CLOUD:  the actual LLM inference (Foundation Model endpoint)
```

Explain:
- **uv run python** runs the agent code locally in the project's virtualenv
- **The LLM** runs on Databricks cloud — the agent calls it via the OpenAI-compatible API using `DATABRICKS_HOST` and `DATABRICKS_TOKEN` from `.env`
- **MLflow** provides the PythonModel base class and tracing — it structures the agent, not serves it
- When deployed in Stage 8, the *entire* agent moves to Databricks. But for development, local code + remote LLM is the fastest iteration loop.

Use `AskUserQuestion` to confirm the learner understands the execution model.

---

### Step 5 — Summary

Present what was built and what's next:

| Component | Status | Details |
|-----------|--------|---------|
| ResponsesAgent class | ✓ Reviewed | `src/risk_agent/agent.py` |
| predict() contract | ✓ Understood | Synchronous response path |
| predict_stream() contract | ✓ Understood | Streaming response path |
| model_config.yaml | ✓ Reviewed | Parameterized LLM settings |
| Local test (no tools) | ✓ Passed | Agent responds but cannot query data |

**What the agent can do now:**
- Respond to general questions using LLM knowledge
- Stream responses via predict_stream()
- Load configuration from model_config.yaml

**What the agent CANNOT do yet:**
- Query Gold tables for real financial data
- Execute governed UC functions
- Provide accurate, data-backed answers

**Next:** Run `/silver-databricks-agents:add-tools` to register Unity Catalog functions as governed tools and wire them into the agent. This is where the agent gets access to real data.

---

After presenting the summary, use `AskUserQuestion` to offer the next stage:

- **"Continue to Stage 3 — Add Tools" (Recommended)** — description: "Run `/silver-databricks-agents:add-tools` now"
- **"Stop here"** — description: "I'll continue later"

If the user chooses to continue, invoke the next skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:add-tools" })`.
