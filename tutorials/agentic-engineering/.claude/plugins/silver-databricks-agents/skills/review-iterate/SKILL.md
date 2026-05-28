---
description: "[Stage 9] Enable the Review App, collect domain expert feedback, and run the Human Gate — approve or reject challenger promotion to champion"
---

# Review & Iterate (Human Gate)

Enable the Databricks Review App to collect domain expert feedback on agent responses. Then run the **Human Gate** — the final approval step where a human decides whether the challenger is ready to become champion. No automated process can make this decision.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Instructions

---

### Step 1 — Explain the Human Gate

Present this to the user:

```
┌──────────────────────────────────────────────────────────────────┐
│  WHY THE HUMAN GATE?                                             │
│                                                                  │
│  Automated metrics (Stage 7) catch:                              │
│  ✓ Regressions in correctness                                    │
│  ✓ Drops in groundedness                                         │
│  ✓ Relevance score declines                                      │
│                                                                  │
│  But they MISS:                                                  │
│  ✗ Tone and communication quality                                │
│  ✗ Domain-specific appropriateness                               │
│  ✗ Edge cases the eval set doesn't cover                         │
│  ✗ "Feels wrong" responses that score well on metrics            │
│  ✗ Business context only domain experts understand               │
│                                                                  │
│  The Human Gate ensures production quality by requiring          │
│  explicit domain expert approval before promotion.               │
│  This is non-negotiable for production AI systems.               │
└──────────────────────────────────────────────────────────────────┘
```

Pause and ask the user if they'd like to continue.

---

### Step 2 — Enable the Review App + Create Labeling Session

Run the following to enable the Review App and create an MLflow labeling session:

```python
from databricks import agents
import mlflow
from risk_agent.evaluate import create_ab_labeling_session

# Enable review app for the serving endpoint
agents.enable_trace_reviews(
    model_name="main.financial_risk.risk_agent",
    request_config=agents.ReviewRequestConfig(
        sample_rate=1.0,  # Review 100% of requests during evaluation
    )
)
```

Then create a **labeling session** to organize the human review. This uses the label schemas created in Stage 5:

```python
# Create a labeling session — visible in MLflow Evaluation > Labeling Sessions
session = create_ab_labeling_session(
    name="human-gate-review-v1",
    assigned_users=["<your-email@company.com>"],
)

print(f"Labeling session: {session.name}")
print(f"Review URL: {session.url}")
```

Explain:
- The **Review App** is a Databricks web UI where domain experts submit queries and see responses
- The **Labeling Session** organizes those reviews in MLflow's Evaluation tab with the `risk_winner` and `risk_rationale` schemas from Stage 5
- `sample_rate=1.0` means every request is available for review (use lower rates in production)
- Feedback is stored as structured MLflow assessments on traces — used by MemAlign in Stage 10

Guide the user to both URLs:
1. **Review App URL** — for submitting queries and reviewing responses
2. **MLflow Evaluation tab > Labeling Sessions** — for seeing the organized review queue

Show both URLs to the user.

---

### Step 3 — Walk Through the Review App

Guide the user to open the Review App in their browser. Walk them through submitting test queries:

**Query 1**: "What is the risk tier for Acme Corp?"
- After the response appears, show how to provide feedback:
  - Thumbs up / thumbs down
  - Written comment explaining why (e.g., "Correct risk tier but missing concentration percentage")
- Explain: the written rationale is gold for MemAlign — it extracts generalizable principles from these comments

**Query 2**: "Which counterparties have CRITICAL risk exposure?"
- Provide feedback. If the response is good, give thumbs up with a note about what made it good.

**Query 3**: "Summarize the portfolio concentration by sector"
- Provide feedback. Note any missing details or formatting issues.

**Query 4**: "What's the net exposure for our top 5 counterparties?"
- This may be a harder question. Note how the agent handles it.

**Query 5**: "Should we reduce our exposure to Acme Corp?"
- This is an opinion question — the agent should stick to data, not give financial advice. Note if it handles this boundary correctly.

After all 5 queries, pause and let the user review what they've submitted.

---

### Step 4 — Query Feedback Programmatically

Show how to access the feedback data:

```python
import mlflow

# Search for traces with human assessments
all_traces = mlflow.search_traces(
    experiment_ids=["<experiment_id>"],
    return_type="list"
)

# Filter to traces with feedback
reviewed_traces = [
    t for t in all_traces
    if t.info.assessments and len(t.info.assessments) > 0
]

print(f"Total traces: {len(all_traces)}")
print(f"Reviewed traces: {len(reviewed_traces)}")
```

Display the feedback as a table:

```
┌────┬──────────────────────────────────┬──────────┬──────────────────────┐
│  # │  Query                           │ Feedback │  Comment             │
├────┼──────────────────────────────────┼──────────┼──────────────────────┤
│  1 │  Risk tier for Acme Corp?        │  👍      │  Correct, detailed   │
│  2 │  CRITICAL risk counterparties?   │  👍      │  Good list           │
│  3 │  Portfolio concentration?         │  👎      │  Missing sector %    │
│  4 │  Top 5 net exposure?             │  👍      │  Well formatted      │
│  5 │  Should we reduce exposure?      │  👍      │  Stayed factual      │
└────┴──────────────────────────────────┴──────────┴──────────────────────┘
```

Explain: This feedback data will be used by MemAlign (Stage 10) to align the LLM judges with domain expert expectations.

---

### Step 5 — Human Gate Decision

Check if there's a challenger waiting for promotion:

```python
client = mlflow.tracking.MlflowClient()
model_name = "main.financial_risk.risk_agent"

try:
    challenger = client.get_model_version_by_alias(model_name, "challenger")
    champion = client.get_model_version_by_alias(model_name, "champion")
    print(f"Champion: v{champion.version}")
    print(f"Challenger: v{challenger.version}")
    has_challenger = True
except:
    print("No challenger waiting for promotion.")
    has_challenger = False
```

**If there IS a challenger**, present the Human Gate decision:

Show champion vs challenger responses side-by-side for the test queries from Step 3. Present as a comparison table:

```
┌──────────────────────────────────────────────────────────────────────┐
│  HUMAN GATE: Champion (v2) vs Challenger (v3)                        │
├──────────────────────┬──────────────────────┬────────────────────────┤
│  Query               │  Champion (v2)       │  Challenger (v3)       │
├──────────────────────┼──────────────────────┼────────────────────────┤
│  Risk tier for       │  "Acme Corp has      │  "Based on Gold risk   │
│  Acme Corp?          │   MEDIUM risk tier"  │   data, Acme Corp is   │
│                      │                      │   MEDIUM tier at 7.2%" │
├──────────────────────┼──────────────────────┼────────────────────────┤
│  CRITICAL risk       │  "The following      │  "3 counterparties     │
│  counterparties?     │   counterparties..." │   are CRITICAL: ..."   │
└──────────────────────┴──────────────────────┴────────────────────────┘
```

Then use `AskUserQuestion` with three options:

- **Approve — Promote challenger to champion**: "The challenger produces better responses. Promote it to champion and start serving it."
- **Reject — Keep current champion**: "The current champion is still better. Reject the challenger and keep the current version."
- **Request changes — Send back for optimization**: "The challenger has potential but needs more work. Send feedback back to the DSPy optimization loop (Stage 6)."

Execute the chosen action:

**If Approve**:
```python
client.set_registered_model_alias(model_name, "champion", challenger.version)
print(f"✓ v{challenger.version} promoted to champion — now serving live traffic")
```

**If Reject**:
```python
client.delete_registered_model_alias(model_name, "challenger")
print(f"✗ v{challenger.version} rejected — champion v{champion.version} continues serving")
```

**If Request Changes**:
Tell the user to return to Stage 6 (optimize-prompts) with the feedback from this session, then re-register and try again.

---

### Step 6 — After Promotion

If the challenger was promoted, verify the serving endpoint serves the new champion:

```bash
databricks serving-endpoints query risk-agent-endpoint \
  --input '{"messages": [{"role": "user", "content": "What is the risk tier for Acme Corp?"}]}'
```

Show the response. Explain: the endpoint automatically picked up the new champion via alias-based routing — no re-deploy needed.

Show the version change in UC:
```python
champion = client.get_model_version_by_alias(model_name, "champion")
print(f"Current champion: v{champion.version}")
```

---

### Step 7 — Summary

Display the stage summary:

```
┌──────────────────────────────────────────────────────────────┐
│  Stage 9 Complete: Review & Iterate (Human Gate)             │
├──────────────────────────────────────────────────────────────┤
│  ✓ Review App enabled                                        │
│  ✓ 5 queries reviewed with feedback                          │
│  ✓ Human Gate decision made                                  │
│  ✓ Feedback data ready for MemAlign (Stage 10)               │
│                                                              │
│  Key insight: Human approval is non-negotiable for           │
│  production AI systems. Automated metrics are necessary      │
│  but not sufficient.                                         │
│                                                              │
│  Next: Stage 10 — Align Judges (MemAlign)                    │
│  Use the human feedback to make evaluation judges smarter.   │
└──────────────────────────────────────────────────────────────┘
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
| 10 | align-judges | ← next |
| 11 | deploy-app | |
| 12 | cleanup | |

---

After presenting the summary, use `AskUserQuestion` to offer the next stage:

- **"Continue to Stage 10 — Align Judges" (Recommended)** — description: "Run `/silver-databricks-agents:align-judges` now"
- **"Stop here"** — description: "I'll continue later"

If the user chooses to continue, invoke the next skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:align-judges" })`.
