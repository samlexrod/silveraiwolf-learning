---
description: "[Stage 10] Align LLM judges with human feedback using MemAlign's dual-memory system — improves the Automated Gate and DSPy optimization"
---

# Align Judges with MemAlign

Out-of-the-box LLM judges are generic — they don't understand your domain. MemAlign aligns judges with human feedback using a dual-memory system: **semantic memory** (general principles) and **episodic memory** (specific edge cases). Only 2-10 feedback examples are needed.

Since the judges are the **single evaluation backbone** (Stage 5) used by the Automated Gate (Stage 7) and DSPy optimization (Stage 6/Playground), aligning them improves everything downstream. Better judges → better Automated Gate decisions → better DSPy optimization → higher quality prompts from the Playground.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Instructions

---

### Step 1 — Explain the Problem

Present this to the user:

```
┌──────────────────────────────────────────────────────────────────┐
│  THE PROBLEM WITH GENERIC JUDGES                                 │
│                                                                  │
│  Generic LLM judge says:                                         │
│    "Is the response correct?"  → scores based on general         │
│    language understanding                                        │
│                                                                  │
│  What you NEED:                                                  │
│    "Is the risk tier classification correct given the            │
│     concentration thresholds in our risk framework?"             │
│    "Did the agent cite specific counterparty data                │
│     rather than giving generic financial advice?"                │
│    "Did the agent correctly distinguish between gross            │
│     and net exposure when asked about exposure?"                 │
│                                                                  │
│  Domain experts know these nuances. MemAlign captures them       │
│  from just a few examples of expert feedback.                    │
└──────────────────────────────────────────────────────────────────┘
```

Pause and ask the user if they'd like to continue.

---

### Step 2 — Explain MemAlign's Dual-Memory System

Present the architecture:

```
┌───────────────────────────────────────────────────────────────────┐
│                      MemAlign Architecture                        │
│                                                                   │
│  Human Feedback ──────────→ MemAlignOptimizer                     │
│  (2-10 examples)                   │                              │
│  with rationale                    │                              │
│                              ┌─────┴─────┐                       │
│                              │           │                        │
│                    Semantic Memory    Episodic Memory              │
│                    (principles)      (edge cases)                  │
│                                                                   │
│  Extracted rules:            Stored examples:                     │
│  • "Always verify risk       • "Q: FX exposure for Acme?         │
│    tier before quoting         A cited stale data from            │
│    concentration %"            wrong quarter → 👎"               │
│  • "Net exposure must        • "Q: Critical counterparties?      │
│    account for hedges,         Listed all, included risk          │
│    not just gross"             tier + concentration → 👍"        │
│                                                                   │
│                    ┌─────────┴─────────┐                          │
│                    │  Working Memory   │                          │
│                    │  (at inference)   │                          │
│                    │  Combines top-k   │                          │
│                    │  relevant from    │                          │
│                    │  both memories    │                          │
│                    └─────────┬─────────┘                          │
│                              │                                    │
│                       Aligned Judge                               │
│                    (domain-aware scoring)                          │
└───────────────────────────────────────────────────────────────────┘
```

Key points:
- **Semantic Memory** stores generalizable principles extracted from expert comments (e.g., "Always check risk tier before exposure %")
- **Episodic Memory** stores specific examples, especially edge cases where the judge stumbled
- **Working Memory** at inference time combines the most relevant principles and examples for the specific query being judged
- Only needs **2-10 feedback examples** with rationale — not hundreds of labels
- **100x faster** than DSPy optimizers for judge alignment (seconds, not minutes)

Pause for questions.

---

### Step 3 — Create Initial Judges

**Where the code lives:** All MemAlign logic is in `src/risk_agent/align.py`. Read and display this file. Walk through the key functions:

| Function | What it does | When it runs |
|----------|-------------|-------------|
| `create_judges()` | Creates 3 domain judges with `make_judge()` | Start of alignment |
| `create_alignment_traces()` | Runs agent on questions, attaches feedback + expectations | Step 4 |
| `align_judge()` | Runs `MemAlignOptimizer` on a judge + assessed traces | Step 5 |
| `compare_judges()` | Scores original vs aligned judge on test data | Step 6 |

Create three domain-specific judges using `make_judge()`. Use Databricks Foundation Models — no OpenAI key needed:

```python
from mlflow.genai.judges import make_judge

# Use Databricks-hosted models (no external API keys needed)
# Format: "databricks:/<endpoint-name>" (colon + slash)
JUDGE_MODEL = "databricks:/databricks-meta-llama-3-3-70b-instruct"

# Judge 1: Correctness — Is the answer factually correct?
correctness_judge = make_judge(
    name="risk_correctness",
    instructions="""Evaluate if the agent's response correctly answers
    the financial risk question using data from the Gold tables.

    Question: {{ inputs }}
    Response: {{ outputs }}
    Expected: {{ expectations }}

    Return True if the response is factually correct, False otherwise.""",
    feedback_value_type=bool,
    model=JUDGE_MODEL,
)

# Judge 2: Groundedness — Is it based on tool results?
groundedness_judge = make_judge(
    name="risk_groundedness",
    instructions="""Evaluate if the agent's response is grounded in the
    tool results (data from Gold tables) rather than hallucinated.

    Question: {{ inputs }}
    Response: {{ outputs }}

    Return True if the response cites specific data from tools, False
    if it makes claims not supported by tool results.""",
    feedback_value_type=bool,
    model=JUDGE_MODEL,
)

# Judge 3: Domain Relevance — Does it answer the risk question?
relevance_judge = make_judge(
    name="risk_relevance",
    instructions="""Evaluate if the agent's response appropriately addresses
    the financial risk question. Consider: Does it provide actionable risk
    information? Does it stay within the data rather than giving advice?

    Question: {{ inputs }}
    Response: {{ outputs }}

    Return True if the response is relevant and appropriate, False otherwise.""",
    feedback_value_type=bool,
    model=JUDGE_MODEL,
)
```

**Important API notes:**
- Model URI format is `databricks:/<endpoint-name>` (colon + slash)
- Template variables use `{{ inputs }}`, `{{ outputs }}`, `{{ expectations }}` (not `{{ targets }}`)
- `expectations` must be passed as a dict, not a string: `judge.run(inputs=q, outputs=r, expectations={"expected_response": exp})`
- `feedback_value_type=bool` means the judge returns True/False

Run a **baseline evaluation** with unaligned judges against the eval set from Stage 5. Show scores as a table. These are the baseline — after alignment, we'll compare.

---

### Step 4 — Create Alignment Traces with Human Feedback

**What we're about to do and why:**

The baseline judges from Step 3 work, but they use generic criteria. To teach them domain-specific rules, we need to show them examples of expert feedback — "this response was good because X" and "this response was bad because Y." MemAlign reads these examples and distills generalizable guidelines from the rationale text.

The process has 3 parts:
1. **Generate traces** — run the agent on 5 questions so we have trace objects to attach feedback to
2. **Attach human feedback** — log yes/no + written rationale on each trace (this is the domain expertise MemAlign learns from)
3. **Attach expectations** — log the ideal answer on each trace (MemAlign's judge template needs this to compare against)

**Why the same experiment (`/Shared/risk-agent`)?**

Alignment traces live in the same experiment as production evaluation — this matches the [official MLflow judge workflow](https://mlflow.org/docs/latest/genai/eval-monitor/scorers/llm-judge/workflow/). MemAlign's `.align()` method receives trace objects directly (not an experiment name), so separation isn't needed. You distinguish alignment traces from evaluation traces by filtering on assessment name — traces with human feedback assessments (e.g., `risk_correctness` from a `HUMAN` source) are alignment data; traces scored by LLM judges are evaluation data.

**What you'll see in the MLflow UI after this step:**

Navigate to **Experiments → /Shared/risk-agent → Traces tab**. Each trace will show:
- The agent's input (question) and output (response) in the span tree
- An **Assessments** section with two entries per trace:
  - `risk_correctness` (feedback) — True/False + the expert's written rationale
  - `expected_response` (expectation) — the ideal answer

This is the data MemAlign reads in Step 5 to distill guidelines.

---

Each trace needs **two types** of assessments:
1. **Feedback** (`mlflow.log_feedback`) — the human yes/no + rationale (what the expert thinks)
2. **Expectation** (`mlflow.log_expectation`) — the expected answer (what the ideal response looks like)

MemAlign requires BOTH. Without expectations, it fails with `"Missing required expectations in trace"`.

**Important:** The feedback name must match the judge name (e.g., `risk_correctness`) for MemAlign to find it.

```python
import mlflow
import time
from mlflow.entities.assessment import AssessmentSource

# Same experiment as evaluation — alignment traces are distinguished by assessment name
mlflow.set_experiment("/Shared/risk-agent")

# Each example needs: question, expected answer, feedback (True/False), and rationale
alignment_data = [
    {"question": "What is the risk tier for Pinnacle Industries?",
     "expected": "Pinnacle Industries: CRITICAL risk, $5.1M exposure, B+ rating, 9.8% default probability.",
     "feedback": True,
     "rationale": "Correctly identified CRITICAL risk with specific exposure and credit rating. Cited default probability."},
    {"question": "Which counterparties have CRITICAL risk?",
     "expected": "Oceanic Trading and Pinnacle Industries have CRITICAL risk with specific exposure and default probability.",
     "feedback": False,
     "rationale": "Only found counterparties in one portfolio. Should query all counterparties, not just one portfolio."},
    # ... 3-5 more examples with rationale from Stage 9
]

# Step A: Run queries to generate traces
trace_ids = []
for item in alignment_data:
    result = agent.predict(model_input={"messages": [{"role": "user", "content": item["question"]}]})
    trace_ids.append(mlflow.get_last_active_trace_id())

# Step B: Wait for async trace export (important!)
time.sleep(15)

# Step C: Log FEEDBACK (human assessment — True/False + rationale)
#   Name MUST match the judge name!
for trace_id, item in zip(trace_ids, alignment_data):
    mlflow.log_feedback(
        trace_id=trace_id,
        name="risk_correctness",  # Must match judge name!
        value=item["feedback"],
        rationale=item["rationale"],
        source=AssessmentSource(source_type="HUMAN", source_id="domain_expert"),
    )

# Step D: Log EXPECTATIONS (the ideal answer)
#   MemAlign reads these via trace.search_assessments(type="expectation")
#   WITHOUT expectations, MemAlign fails with "Missing required expectations"
for trace_id, item in zip(trace_ids, alignment_data):
    mlflow.log_expectation(
        trace_id=trace_id,
        name="expected_response",
        value=item["expected"],
    )

# Step E: Retrieve Trace objects for alignment
time.sleep(5)  # Wait for expectations to sync
client = mlflow.MlflowClient()
alignment_traces = [client.get_trace(tid) for tid in trace_ids]
```

**Why two different logging calls?**

| Call | Assessment Type | What MemAlign Uses It For |
|------|----------------|--------------------------|
| `mlflow.log_feedback()` | `type="feedback"` | The human judgment: was this response good or bad, and why? MemAlign extracts guidelines from the rationale. |
| `mlflow.log_expectation()` | `type="expectation"` | The ideal answer. MemAlign's judge template uses `{{ expectations }}` — without this, the template variable is empty and alignment fails. |

Key points:
- **Both feedback AND expectations required** — feedback alone causes `"Missing required expectations"` error
- **Feedback name must match judge name** — MemAlign filters by `name="risk_correctness"` to find relevant feedback
- **Wait for async export** before logging — traces are exported asynchronously to Databricks (`time.sleep(15)`)
- **Written rationale matters most** — "Correct but missing concentration %" teaches more than a bare thumbs-down
- **Mix positive and negative examples** — both teach the judge what good/bad looks like
- Only **5 examples** with rationale is typically enough

---

### Step 5 — Align Judges with MemAlign

Run the MemAlignOptimizer. Use Databricks-hosted models for both the reflection LM and embedding model — no OpenAI key needed:

```python
from mlflow.genai.judges.optimizers import MemAlignOptimizer

# Initialize optimizer — all Databricks-native, no external API keys
optimizer = MemAlignOptimizer(
    reflection_lm="databricks:/databricks-meta-llama-3-3-70b-instruct",
    embedding_model="databricks:/databricks-gte-large-en",  # Databricks embedding endpoint
    retrieval_k=3,  # Top-3 relevant examples from episodic memory
)

# Align — pass the judge and the assessed traces
aligned_correctness = correctness_judge.align(
    traces=alignment_traces,
    optimizer=optimizer
)
```

**Important API notes:**
- `reflection_lm` uses format `databricks:/<endpoint-name>` (same as make_judge model)
- `embedding_model` uses `databricks:databricks-gte-large-en` — a Databricks-hosted embedding endpoint, available in all workspaces. This avoids needing an OpenAI API key.
- `retrieval_k=3` means the episodic memory retrieves the 3 most similar examples at inference time

After alignment, inspect the learned guidelines:

```python
print("=== Aligned Correctness Judge ===")
print(aligned_correctness.instructions)
```

Show the full output to the user. The aligned judge's instructions now contain the original instruction PLUS distilled guidelines appended at the end. For example:

```
ORIGINAL INSTRUCTION (unchanged):
  Evaluate if the agent response correctly answers the financial
  risk question.
  Question: {{ inputs }}
  Response: {{ outputs }}
  Expected: {{ expectations }}
  Return True if the response is factually correct, False otherwise.

APPENDED BY MEMALIGN — "Distilled Guidelines (N)":
  - The agent should present data and let the user decide,
    not suggest actions or provide investment advice.
  - The agent should query all counterparties, not just
    those in one portfolio.
  - The agent's response should include specific data such as
    risk tier, exposure amounts, and credit ratings.
```

**What just happened mechanically:**
1. MemAlign's reflection LM read each human rationale (e.g., "borderline gave investment advice")
2. It generalized the rationale into a rule (e.g., "should present data and let the user decide")
3. It deduplicated and ranked the rules
4. It appended them as "Distilled Guidelines" to the judge's instruction prompt

**Why this matters:** The aligned judge now checks domain-specific rules that the generic judge never knew about. When this judge scores a response that suggests reducing exposure (financial advice), it will mark it as incorrect — because guideline #1 says agents should present data, not suggest actions.

The guidelines live in the judge's `instructions` field — they're just text appended to the prompt. No model fine-tuning, no training data, no GPU time. This is why MemAlign is 100x faster than DSPy for judge alignment.

Repeat alignment for the other two judges (groundedness and relevance). Each judge needs its own alignment traces with matching assessment names (e.g., `risk_groundedness` feedback for the groundedness judge).

**How aligned judges make the agent better — the concrete connection:**

The aligned judges don't change the agent directly. They change how the agent is *evaluated*, which changes what gets promoted and what DSPy optimizes for. Here's the chain:

```
  align.py                    evaluate.py                  optimize.py
  align_judge()               run_automated_gate()         DSPy metric
       │                            │                           │
       │  aligned judges            │  scorers= parameter       │  same scorers
       │  replace generic           │  accepts aligned judges   │  used as metric
       │  ones                      │  instead of get_scorers() │  for optimization
       ▼                            ▼                           ▼
  aligned_correctness ──────→ scorers=[aligned_correctness, ...]
                                     │
                              candidate must beat champion
                              on ALIGNED criteria
                                     │
                              result: stricter gate
                              → only promotes agents that
                                follow domain rules
```

In `evaluate.py`, the `run_automated_gate()` function accepts a `scorers` parameter (line 256). By default it uses `get_scorers()` (the generic built-in scorers). To use aligned judges instead, pass them as scorers:

```python
# Before alignment: generic gate
gate_result = run_automated_gate(candidate, champion)  # uses get_scorers()

# After alignment: domain-aware gate
gate_result = run_automated_gate(
    candidate, champion,
    scorers=[aligned_correctness, aligned_groundedness, aligned_relevance],
)
```

The same aligned judges can be passed to DSPy's metric function in `optimize.py`, so DSPy optimizes prompts to satisfy domain-specific criteria — not just generic correctness.

**In the Coliseum Playground (Stage 11):** The app passes aligned judges to both the Automated Gate and the DSPy optimization job. Domain experts provide feedback → MemAlign improves judges → judges make the gate stricter → DSPy finds prompts that pass the stricter gate → agent quality improves.

---

### Step 6 — Compare Before/After Alignment

Re-evaluate the agent with aligned judges using `evaluate_from_traces()` from the evaluation module. The aligned judges replace the built-in scorers for domain-specific accuracy:

```python
import mlflow
from risk_agent.evaluate import evaluate_from_traces

mlflow.set_experiment("/Shared/risk-agent")

# Evaluate with aligned judges as scorers
result = mlflow.genai.evaluate(
    data=mlflow.search_traces(experiment_ids=[exp.experiment_id]),
    scorers=[aligned_correctness, aligned_groundedness, aligned_relevance],
)
```

Present the comparison:

```
┌──────────────────────────────────────────────────────────────────┐
│  JUDGE ALIGNMENT COMPARISON                                      │
├──────────────────┬────────────┬────────────┬─────────────────────┤
│  Judge           │ Unaligned  │  Aligned   │  Delta              │
├──────────────────┼────────────┼────────────┼─────────────────────┤
│  Correctness     │  78%       │  71%       │  -7% (stricter!)    │
│  Groundedness    │  82%       │  74%       │  -8% (stricter!)    │
│  Domain Relevance│  85%       │  80%       │  -5% (stricter!)    │
└──────────────────┴────────────┴────────────┴─────────────────────┘

Note: Lower scores after alignment often mean the judge is now
MORE ACCURATE — it's catching issues the generic judge missed.
```

Explain the counterintuitive result: **lower scores after alignment can mean better evaluation**. The unaligned judge was too lenient — it scored responses as "correct" when they were missing domain-specific details. The aligned judge now understands what a good financial risk answer looks like.

Pause and let the user absorb this.

---

### Step 7 — The Full Optimization Loop

Explain how everything connects:

```
┌──────────────────────────────────────────────────────────────────┐
│  THE OPTIMIZATION FLYWHEEL                                       │
│                                                                  │
│  1. Agent responds to queries                    (Stages 2-4)    │
│  2. LLM judges evaluate responses                (Stage 5)       │
│  3. DSPy optimizes agent prompts                 (Stage 6)       │
│  4. Coliseum gates promotion                     (Stage 7)       │
│  5. Agent serves live traffic                    (Stage 8)       │
│  6. Humans review and provide feedback           (Stage 9)       │
│  7. MemAlign aligns judges with feedback   ──→   (Stage 10) ←── │
│  8. Better judges reveal new weaknesses                          │
│  9. Go back to step 3 (DSPy) to fix them                        │
│                                                                  │
│  DSPy improves the AGENT. MemAlign improves the JUDGES.          │
│  Together, they form a self-improving system.                    │
└──────────────────────────────────────────────────────────────────┘
```

If the aligned evaluation reveals significant new weaknesses, tell the user they can:
1. Return to Stage 6 (DSPy) to re-optimize with the new insights
2. Register the improved agent as a new candidate (Stage 7)
3. The aligned judges will evaluate the new candidate more accurately
4. Better agent + better judges = compounding improvement

Ask the user if they want to run another optimization cycle or proceed to Stage 11.

---

### Step 8 — Summary

Display the stage summary:

```
┌──────────────────────────────────────────────────────────────────┐
│  Stage 10 Complete: Align Judges (MemAlign)                      │
├──────────────────────────────────────────────────────────────────┤
│  ✓ Three domain-specific judges created                          │
│  ✓ Judges aligned with human feedback from Stage 9               │
│  ✓ Semantic principles extracted automatically                   │
│  ✓ Before/after comparison shows more accurate scoring           │
│                                                                  │
│  Key insight: MemAlign needs only 2-10 examples.                 │
│  DSPy optimizes the agent. MemAlign optimizes the judges.        │
│  Together they form the optimization flywheel.                   │
│                                                                  │
│  Aligned judges can replace built-in scorers in evaluate.py      │
│  for domain-specific evaluation in the Automated Gate.           │
│                                                                  │
│  Next: Stage 11 — Coliseum Playground (App)                      │
│  Deploy the full-featured Databricks App where users can         │
│  compare models, test custom prompts, and drive promotion.       │
└──────────────────────────────────────────────────────────────────┘
```

Show the tutorial progress tracker:

### Tutorial Progress
| Stage | Skill | Status |
|-------|-------|--------|
| 1 | scaffold-setup | ✓ |
| 2 | author-agent | ✓ |
| 3 | add-tools | ✓ |
| 4 | add-tracing | ✓ |
| 5 | evaluate-agent | ✓ |
| 6 | optimize-prompts | ✓ |
| 7 | register-agent | ✓ |
| 8 | deploy-agent | ✓ |
| 9 | review-iterate | ✓ |
| 10 | align-judges | ✓ |
| 11 | deploy-app | ← next |
| 12 | cleanup | |

---

After presenting the summary, use `AskUserQuestion` to offer the next stage:

- **"Continue to Stage 11 — Coliseum Playground" (Recommended)** — description: "Run `/silver-databricks-agents:deploy-app` now"
- **"Stop here"** — description: "I'll continue later"

If the user chooses to continue, invoke the next skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:deploy-app" })`.
