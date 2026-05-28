---
description: "[Stage 11] Deploy the Coliseum Playground — the hub for democratized prompt engineering with comparison, voting, DSPy optimization, and three-gate promotion"
---

# Coliseum Playground (Databricks App)

Deploy a Databricks App that democratizes prompt engineering. Domain experts — not just ML engineers — write custom prompts, test them side-by-side against the champion, vote on quality, optionally trigger DSPy to boost their prompt, and push through the three-gate Coliseum promotion pipeline. Everything from Stages 5-10 converges here.

This is the **capstone stage** of the tutorial — the Playground is the hub for all subsequent iterations.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Instructions

---

### Step 1 — Explain Databricks Apps vs Model Serving

Present this to the user:

```
┌──────────────────────────────────────────────────────────────────┐
│  WHY A DATABRICKS APP?                                           │
│                                                                  │
│  Stage 8 deployed a Serving Endpoint:                            │
│    → REST API for programmatic consumers                         │
│    → No UI — just JSON in / JSON out                             │
│    → Great for notebooks, pipelines, other services              │
│                                                                  │
│  This stage deploys a Databricks App:                            │
│    → Web UI for human interaction                                │
│    → Side-by-side model comparison                               │
│    → Voting, feedback, and promotion — all in one place          │
│    → The human-facing interface to the Coliseum pipeline         │
│                                                                  │
│  Most production agents need BOTH:                               │
│    Serving Endpoint for machines, App for humans.                │
└──────────────────────────────────────────────────────────────────┘
```

Pause and ask the user if they'd like to continue.

---

### Step 2 — Walk Through app.py

Read and display `src/risk_agent/app.py` from the project. Walk through the Gradio app structure — it has **4 tabs**:

```
┌──────────────────────────────────────────────────────────────────┐
│  ⚔️ Coliseum — Portfolio Risk Dashboard                          │
│  🟢 READY | main.financial_risk.risk_agent v7                    │
├─────────────┬──────────────┬─────────────┬───────────────────────┤
│ 💬 Multi-   │ ⚔️ Single-   │ 🔬 A/B      │ 📊 Data              │
│    Turn     │    Turn      │    Testing  │                       │
└─────────────┴──────────────┴─────────────┴───────────────────────┘
```

**Tab 1 — Multi-Turn Playground**: Free-form chat about a portfolio. Portfolio dropdown, quick question buttons, `gr.Chatbot` with follow-up suggestions.

**Tab 2 — Single-Turn Playground**: Prompt editor on the left, 6 insight cards on the right (Risk Overview, High-Risk Alerts, Top Exposures, Sector Concentration, Financial Health, Default Risk). "Generate All Cards" runs the custom prompt against the selected portfolio.

**Tab 3 — A/B Testing**: Step-by-step comparison of Champion vs Custom prompt. 8 eval items across 4 portfolios. Pick a winner for each, then check the Candidate Gate status.

**Tab 4 — Data**: View A/B results table, export to MLflow labeling session.

Key architecture:
- **Both Champion + Custom columns call the same serving endpoint** — Custom sends the custom system prompt as the first message, the agent detects it and uses it instead of the default
- **Portfolio selector** with 4 portfolios (Alpha Growth, Meridian Income, Global Balanced, Emerging Markets)
- **A/B eval set** has portfolio context baked into each question — tests different insight cards on different portfolios
- **Candidate Gate** requires ≥80% custom wins on 3+ comparisons before registration is enabled

Pause for questions.

---

### Step 3 — Deploy as Databricks App

**Step A — Create the app:**
```bash
databricks apps create risk-agent-playground --description "Coliseum Playground"
```

**Step B — Prepare workspace files.** The app needs 3 files uploaded to a workspace directory:

1. `app.py` — the Gradio app (from `src/risk_agent/app.py`)
2. `app.yaml` — tells Databricks how to run it:
   ```yaml
   command:
     - python
     - app.py
   ```
3. `requirements.txt` — dependencies:
   ```
   gradio>=4.0
   requests
   databricks-sdk>=0.38
   ```

Upload all 3 to a workspace directory (e.g., `/Workspace/Users/<you>/risk-agent-app/`) using the REST API `workspace/import` with `format=AUTO`.

**Step C — Deploy:**
```bash
databricks apps deploy risk-agent-playground \
  --source-code-path /Workspace/Users/<you>/risk-agent-app \
  --no-wait
```

**Step D — Grant the app's service principal permission to query the serving endpoint:**
```bash
# Get the endpoint ID
ENDPOINT_ID=$(databricks serving-endpoints get risk-agent-endpoint --output json | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

# Get the app's SP client ID (from databricks apps get output)
SP_ID="<app-service-principal-client-id>"

# Grant CAN_QUERY
curl -X PATCH "$DATABRICKS_HOST/api/2.0/permissions/serving-endpoints/$ENDPOINT_ID" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -d '{"access_control_list": [{"service_principal_name": "'$SP_ID'", "permission_level": "CAN_QUERY"}]}'
```

**Important deployment notes:**
- The app uses `APP_PORT` env var (defaults to 8000) — Databricks routes traffic to this port
- The app authenticates via `WorkspaceClient()` which auto-authenticates as the app's service principal
- Both Champion and Custom Prompt columns call the **same serving endpoint** — Custom sends the custom system prompt as the first message, the agent detects it and uses it instead of the default
- Each re-deploy after editing `app.py`: upload the file, then run `databricks apps deploy`

Wait for the app to deploy. Show the app URL when ready.

---

### Step 4 — Test the Coliseum Playground

Guide the user to open the app in their browser. Walk them through:

1. **Enter a query**: "What is the risk tier for Acme Corp?"
   - Observe all three columns populate (Custom will be empty until they write a prompt)
   - Champion and Challenger show their respective model versions

2. **Write a custom prompt**: In the Custom column, edit the system prompt. For example, change it to be more concise:
   ```
   You are a risk analyst. Answer using data from Gold tables.
   Be concise — use bullet points, not paragraphs.
   Always cite the specific data source.
   ```

3. **Run again**: Same query, now all three columns have responses

4. **Vote**: Give thumbs up/down on each response based on quality

5. **Try more queries**: "Which counterparties are CRITICAL risk?" and "Summarize portfolio concentration"

---

### Step 5 — Candidate Gate Walkthrough

Now demonstrate the Candidate Gate:

```
┌──────────────────────────────────────────────────────────────┐
│  CANDIDATE GATE                                              │
│                                                              │
│  The "Register as Candidate" button stays DISABLED until     │
│  your custom prompt achieves ≥80% approval on 5+ queries.    │
│                                                              │
│  This prevents low-quality prompts from entering the         │
│  Coliseum pipeline. Every vote is logged as a MemAlign       │
│  trace regardless of whether registration is unlocked.       │
└──────────────────────────────────────────────────────────────┘
```

Guide the user:

1. Submit **5 queries** with their custom prompt
2. Vote on each response (thumbs up if good, thumbs down if not)
3. Watch the approval rate update in real-time:

```
Query 1: "Risk tier for Acme Corp?"          👍  (1/1 = 100%)
Query 2: "FX exposure summary?"              👍  (2/2 = 100%)
Query 3: "Critical risk counterparties?"     👎  (2/3 = 67%)
Query 4: "Portfolio concentration?"          👍  (3/4 = 75%)
Query 5: "Net exposure for sector X?"        👍  (4/5 = 80%) ✓ GATE PASSED
```

When the rate hits ≥80%:
- The "Register as Candidate" button becomes **enabled**
- The "Optimize with DSPy" button also becomes **enabled**

Ask the user: do they want to register directly, or boost the prompt first with DSPy?

**Option A — Register directly:**
```
✓ Custom prompt registered as candidate
  Model: main.financial_risk.risk_agent
  Version: v4
  Alias: @candidate
```

**Option B — Boost with DSPy first:**
```
⏳ DSPy optimization job triggered...
   Using judges from Stage 5 as the optimization metric
   Starting from your custom prompt as the baseline
   Running BootstrapFewShot + MIPROv2...

✓ DSPy job complete — optimized prompt returned
  Original Candidate Gate score: 80%
  Optimized prompt loaded in Custom column — test it now
```

After DSPy returns, the user tests the optimized prompt, votes again (it should still be ≥80% since it's an improvement), and registers:

```
✓ DSPy-optimized prompt registered as candidate
  Model: main.financial_risk.risk_agent
  Version: v5
  Alias: @candidate
```

---

### Step 6 — End-to-End Promotion Walkthrough

This is the capstone of the entire tutorial. Walk the learner through the full promotion lifecycle from within the app:

**Step A — Candidate Registered**

```
┌──────────────────────────────────────────────────────────┐
│  ✓ Step A: Custom prompt registered as candidate         │
│     Model version: v4                                    │
│     Alias: @candidate                                    │
│     Source: Custom prompt from Coliseum Playground        │
└──────────────────────────────────────────────────────────┘
```

**Step B — Automated Gate**

Click "Run Automated Gate" in the app. This triggers `mlflow.evaluate()` on the candidate vs champion:

```
┌──────────────────────────────────────────────────────────┐
│  AUTOMATED GATE: Candidate (v4) vs Champion (v2)         │
├──────────────────┬────────────┬────────────┬─────────────┤
│  Metric          │ Candidate  │ Champion   │ Result      │
├──────────────────┼────────────┼────────────┼─────────────┤
│  Correctness     │  83%       │  78%       │ ✓ +5%       │
│  Groundedness    │  79%       │  74%       │ ✓ +5%       │
│  Relevance       │  88%       │  80%       │ ✓ +8%       │
├──────────────────┴────────────┴────────────┴─────────────┤
│  RESULT: Candidate beats champion on all metrics         │
│  → Auto-promoted to @challenger                          │
└──────────────────────────────────────────────────────────┘
```

If the candidate wins, it's automatically promoted to `@challenger`. Show the status update in the app.

If the candidate loses, show the rejection and explain what metrics it fell short on.

**Step C — Human Gate**

Click "Run Human Gate" in the app. This presents challenger vs champion side-by-side for 3-5 queries:

```
┌──────────────────────────────────────────────────────────┐
│  HUMAN GATE: Challenger (v4) vs Champion (v2)            │
│                                                          │
│  Review the responses below and decide:                  │
│                                                          │
│  Q1: "Risk tier for Acme Corp?"                          │
│   Champion: "Acme Corp has MEDIUM risk tier"             │
│   Challenger: "Acme Corp: MEDIUM tier, 7.2% conc."      │
│                                                          │
│  Q2: "CRITICAL counterparties?"                          │
│   Champion: "The following counterparties..."            │
│   Challenger: "3 counterparties are CRITICAL: ..."       │
│                                                          │
│  Q3: "Portfolio concentration by sector?"                │
│   Champion: "Technology: 34%, Finance: 28%..."           │
│   Challenger: "• Technology: 34% (↑2% QoQ)..."           │
│                                                          │
│  [Approve — Promote to Champion]                         │
│  [Reject — Keep Current Champion]                        │
└──────────────────────────────────────────────────────────┘
```

Use `AskUserQuestion` with Approve / Reject options.

If **Approved**:
```
✓ v4 promoted to champion — now serving live traffic!
  Previous champion (v2) is still available for rollback.
  Serving endpoint automatically updated via alias routing.
```

**Step D — Verify**

After promotion, refresh the app:
- Champion column now shows v4 responses
- Custom column is empty (ready for next experiment)
- Serving endpoint automatically serves the new champion

```
┌──────────────────────────────────────────────────────────┐
│  ✓ COMPLETE: Custom Prompt → Champion                    │
│                                                          │
│  Step A: Registered as candidate (v4)          ✓         │
│  Step B: Automated Gate — beat champion         ✓         │
│  Step C: Human Gate — approved by reviewer      ✓         │
│  Step D: Serving live traffic as champion       ✓         │
│                                                          │
│  From writing a prompt to serving it in production,      │
│  through automated evaluation and human approval.        │
│  This is the Coliseum Promotion Pipeline.                │
└──────────────────────────────────────────────────────────┘
```

---

### Step 7 — Swap to Streamlit Version

After the learner has tested the Gradio app, introduce Streamlit as an alternative. Both apps have the same 4-page structure and features — comparing them teaches the learner both frameworks.

Present the comparison:

```
┌──────────────────────────────────────────────────────────────────┐
│  GRADIO vs STREAMLIT — same features, different paradigms        │
│                                                                  │
│  Gradio (app.py):                                                │
│  • Callback-based (React-like): gr.Button().click(fn, ...)       │
│  • Module-level state: _votes dict (shared across all users)     │
│  • Tab layout: gr.Tabs() with gr.Tab() blocks                   │
│  • ~400 lines                                                    │
│                                                                  │
│  Streamlit (app_streamlit.py):                                   │
│  • Top-to-bottom script: re-runs on every interaction            │
│  • Per-user state: st.session_state (isolated, persistent)       │
│  • Sidebar navigation: st.sidebar + page routing                 │
│  • ~770 lines (more features: MLflow traces, DSPy trigger)       │
│                                                                  │
│  Free edition allows one app at a time — we'll stop Gradio       │
│  and deploy Streamlit in its place.                              │
└──────────────────────────────────────────────────────────────────┘
```

Walk through the `app_streamlit.py` file from the scaffold. Highlight the key differences:

1. **State**: `st.session_state.votes` — per-user, survives re-runs. vs Gradio's module-level `_votes` dict (shared)
2. **Navigation**: Sidebar with 4 pages (Multi-Turn, Single-Turn, A/B Testing, Data) vs Gradio's `gr.Tabs`
3. **Chat**: `st.chat_message` + `st.chat_input` built-in chat UI vs Gradio's `gr.Chatbot`
4. **Progress bar**: `st.progress(pct / 80)` for the Candidate Gate vs Gradio's markdown
5. **Spinner**: `st.spinner("Querying...")` loading feedback vs Gradio's no-feedback-during-load
6. **MLflow integration**: Logs A/B traces + exports labeling sessions. DSPy trigger from UI.

**Deploy Streamlit — swap steps:**

1. Stop the Gradio app:
   ```bash
   databricks apps stop risk-agent-playground
   ```

2. Upload 3 files to the workspace directory:
   - `app_streamlit.py` from `src/risk_agent/app_streamlit.py`
   - Updated `app.yaml`:
     ```yaml
     command:
       - streamlit
       - run
       - app_streamlit.py
       - --server.port
       - "8000"
     env:
       - name: APP_PORT
         value: "8000"
     ```
   - Updated `requirements.txt`:
     ```
     streamlit>=1.30
     requests
     databricks-sdk>=0.38
     mlflow>=2.18
     ```

3. Wait for app to reach ACTIVE state, then deploy:
   ```bash
   databricks apps deploy risk-agent-playground \
     --source-code-path /Workspace/Users/<you>/risk-agent-app \
     --no-wait
   ```

After deployment, test the same queries. The learner should observe:
- Same Champion and Custom Prompt responses (same serving endpoint)
- Per-user vote state (open in two browser tabs to verify)
- Sidebar navigation between 4 pages
- Progress bar for the Candidate Gate
- Multi-turn chat with follow-up suggestions

Use `AskUserQuestion` to ask which framework the learner prefers and why.

---

### Step 8 — Summary

Display the stage summary:

```
┌──────────────────────────────────────────────────────────────┐
│  Stage 11 Complete: Coliseum Playground                      │
├──────────────────────────────────────────────────────────────┤
│  ✓ Gradio version deployed and tested (app.py)               │
│  ✓ Streamlit version deployed and tested (app_streamlit.py)  │
│  ✓ Three-column comparison (Champion/Challenger/Custom)      │
│  ✓ Candidate Gate walkthrough (≥80% approval)                │
│  ✓ Both frameworks compared — learner chose preference       │
│                                                              │
│  This is the capstone of the tutorial. You've seen:          │
│  • ResponsesAgent authoring (Stage 2)                        │
│  • UC function tools (Stage 3)                               │
│  • MLflow tracing (Stage 4)                                  │
│  • LLM-as-judge evaluation (Stage 5)                         │
│  • DSPy prompt optimization (Stage 6)                        │
│  • Coliseum promotion pipeline (Stages 7, 9, 11)            │
│  • Serving endpoint deployment (Stage 8)                     │
│  • MemAlign judge alignment (Stage 10)                       │
│                                                              │
│  All connected through the Playground:                        │
│  Domain expert writes prompt → votes (Candidate Gate)         │
│  → optional DSPy boost → Automated Gate (judges)              │
│  → Human Gate → @champion serving live traffic                │
│                                                              │
│  MemAlign improves judges from Playground feedback            │
│  → better judges → better DSPy → better Automated Gate       │
│                                                              │
│  Next: Stage 12 — Cleanup                                    │
│  Delete all Databricks resources when you're done.           │
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
| 10 | align-judges | ✓ |
| 11 | deploy-app | ✓ |
| 12 | cleanup | ← next |

---

After presenting the summary, use `AskUserQuestion` to offer the next stage:

- **"Continue to Stage 12 — Cleanup" (Recommended)** — description: "Run `/silver-databricks-agents:cleanup` now"
- **"Stop here"** — description: "I'll continue later"

If the user chooses to continue, invoke the next skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:cleanup" })`.
