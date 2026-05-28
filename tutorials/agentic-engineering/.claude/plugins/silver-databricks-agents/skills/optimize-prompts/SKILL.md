---
description: "[Stage 6] Optimize agent prompts with DSPy — compile with BootstrapFewShot and MIPROv2, evaluate variants, pick the best"
---

# Optimize Prompts — DSPy Compilation for Data-Driven Prompt Engineering

Learn how DSPy uses the judges from Stage 5 to automatically optimize prompts. In this stage you run DSPy locally to understand the mechanics. In production, domain experts trigger DSPy as a Databricks Job from the Coliseum Playground (Stage 11) to boost their custom prompt's score on the Automated Gate.

This is an **interactive walkthrough** — pause after each section and wait for the user to confirm before moving on.

## Context

After Stage 5 (evaluate-agent), the learner has:
- A working agent with tools, tracing, and evaluation
- Baseline evaluation scores (correctness, groundedness, relevance)
- Experience with manual prompt iteration — it works but doesn't scale

This stage automates prompt optimization with DSPy.

> **Where DSPy fits in the Coliseum:** Domain experts write custom prompts in the Playground and vote on quality (Candidate Gate). If the prompt passes the Candidate Gate but needs a higher score on the Automated Gate, they click "Optimize" — which triggers a Databricks Job running DSPy with the same judges. DSPy takes their prompt as a starting point, improves it, and returns the optimized version to the Playground. Manual prompt engineering provides the domain intent; DSPy refines it programmatically.

---

## Instructions

---

### Step 1 — Explain DSPy

**What is DSPy?**

DSPy is a framework for programmatic prompt optimization. Instead of manually writing and tweaking prompts, you define what the program should do (typed I/O contracts) and let DSPy find the best prompt through compilation.

| Approach | Method | Effort | Quality |
|----------|--------|--------|---------|
| **Manual prompt engineering** | Write → test → tweak → repeat | High (hours) | Depends on your intuition |
| **Few-shot examples** | Add input/output examples to the prompt | Medium | Better, but examples are hand-picked |
| **DSPy BootstrapFewShot** | Automatically finds the best examples from training data | Low (minutes) | Data-driven selection, no intuition needed |
| **DSPy MIPROv2** | Optimizes the instruction text itself (rewrites your system prompt) | Low (minutes) | Finds phrasings you'd never think of |

**The mental model:**

```
Traditional: Human writes prompt → hope it works
DSPy:        Human defines I/O contract → DSPy compiles the best prompt

    ┌────────────────────────────────────────┐
    │  Signature (typed I/O contract)         │
    │  "question: str → answer: str"          │
    │                                          │
    │  Module (composable program)             │
    │  ChainOfThought(RiskAnswerer)            │
    │                                          │
    │  Optimizer (compilation strategy)        │
    │  BootstrapFewShot / MIPROv2              │
    │                                          │
    │  Training Data (from eval set)           │
    │  + Metric (from Stage 5 judges)          │
    └────────────────────────────────────────┘
              ↓ compile()
    ┌────────────────────────────────────────┐
    │  Optimized Prompt                       │
    │  (better instructions + examples)       │
    └────────────────────────────────────────┘
```

**Key insight:** DSPy doesn't change your agent code. It changes the PROMPT that drives the agent — the system instruction and few-shot examples in `model_config.yaml`. The ResponsesAgent, tools, and tracing all stay the same.

Use `AskUserQuestion` to confirm the learner understands the DSPy concept before seeing code.

---

### Step 2 — Define DSPy Signatures

Read and display the `optimize/optimize.py` file. Walk through the key components:

**Signature — The I/O Contract:**

```python
class RiskAnswerer(dspy.Signature):
    """Answer financial risk questions using tool results."""
    
    question: str = dspy.InputField(desc="The user's financial risk question")
    context: str = dspy.InputField(desc="Tool results from UC functions")
    answer: str = dspy.OutputField(desc="A grounded, accurate answer based on the context")
```

A Signature is a typed contract — it tells DSPy what goes in and what comes out. The docstring becomes part of the prompt instruction. The field descriptions guide the LLM on what each field means.

**Module — The Composable Program:**

```python
class RiskAgent(dspy.Module):
    def __init__(self):
        self.answer = dspy.ChainOfThought(RiskAnswerer)
    
    def forward(self, question, context):
        return self.answer(question=question, context=context)
```

- `ChainOfThought` wraps the signature and adds a reasoning step — the LLM explains its thinking before producing the answer. This often improves accuracy.
- The module is composable — you can chain multiple signatures together for multi-step reasoning.

**Why this structure matters:**
- The Signature defines WHAT the program does (contract)
- The Module defines HOW it's structured (composition)
- The Optimizer decides the exact PROMPT that implements it (compilation)

Use `AskUserQuestion` to confirm the learner understands signatures and modules.

---

### Step 3 — Prepare Training Data

Convert the evaluation set from Stage 5 into DSPy training examples:

```bash
cd <project-dir>
uv run python -c "
import json
import dspy

# Load the evaluation set
with open('evaluation/evaluation_set.json') as f:
    eval_data = json.load(f)

# Convert to DSPy examples
train_examples = []
for item in eval_data:
    example = dspy.Example(
        question=item['request']['messages'][-1]['content'],
        context='',  # Will be filled by tool execution during compilation
        answer=item['expected_response']
    ).with_inputs('question', 'context')
    train_examples.append(example)

print(f'Prepared {len(train_examples)} training examples')
for ex in train_examples[:3]:
    print(f'  Q: {ex.question[:60]}...')
    print(f'  A: {ex.answer[:60]}...')
    print()
"
```

**Teaching moment:** The training examples come directly from the evaluation set we built in Stage 5. The expected answers are grounded in Gold table data — this is what makes DSPy optimization reliable. If your training data is wrong, DSPy will optimize for wrong answers.

Use `AskUserQuestion` to confirm the data preparation looks correct.

---

### Step 4 — Run BootstrapFewShot

Compile with the BootstrapFewShot optimizer. This finds the best few-shot examples from the training data:

```bash
cd <project-dir>
uv run python -c "
import dspy
import mlflow
from optimize.optimize import RiskAgent, RiskAnswerer

mlflow.set_experiment('/Shared/risk-agent')

# Configure the LLM
lm = dspy.LM('databricks-meta-llama-3-3-70b-instruct')
dspy.configure(lm=lm)

# Load training data
# ... (load from evaluation_set.json as in Step 3)

# Define the metric (uses Stage 5 judges)
def risk_metric(example, prediction, trace=None):
    # Score based on correctness and groundedness
    # Returns a float between 0 and 1
    ...

# Compile with BootstrapFewShot
optimizer = dspy.BootstrapFewShot(
    metric=risk_metric,
    max_bootstrapped_demos=3,
    max_labeled_demos=3,
)

compiled_agent = optimizer.compile(
    RiskAgent(),
    trainset=train_examples,
)

# Log to MLflow
with mlflow.start_run(run_name='bootstrap-fewshot'):
    # Save the compiled program
    compiled_agent.save('optimized_bootstrap.json')
    mlflow.log_artifact('optimized_bootstrap.json')
    mlflow.log_param('optimizer', 'BootstrapFewShot')
    mlflow.log_param('max_demos', 3)

print('BootstrapFewShot compilation complete')
print('Optimized prompt saved to optimized_bootstrap.json')
"
```

**What BootstrapFewShot does:**
1. Runs the agent on each training example
2. Checks which examples the agent gets right (using the metric)
3. Selects the best-performing examples as few-shot demonstrations
4. Inserts them into the prompt as "here's how to answer similar questions"

The result is a prompt that includes curated examples — not random ones, but the ones that most improve the agent's accuracy.

Use `AskUserQuestion` to confirm the compilation completed. Show the selected few-shot examples.

---

### Step 5 — Run MIPROv2

Compile with the MIPROv2 optimizer. This optimizes the instruction text itself:

```bash
cd <project-dir>
uv run python -c "
import dspy
import mlflow
from optimize.optimize import RiskAgent, RiskAnswerer

mlflow.set_experiment('/Shared/risk-agent')

# Configure the LLM
lm = dspy.LM('databricks-meta-llama-3-3-70b-instruct')
dspy.configure(lm=lm)

# Load training data (same as Step 4)
# ...

# Compile with MIPROv2
optimizer = dspy.MIPROv2(
    metric=risk_metric,
    num_candidates=5,
    init_temperature=1.0,
)

compiled_agent = optimizer.compile(
    RiskAgent(),
    trainset=train_examples,
)

# Log to MLflow
with mlflow.start_run(run_name='miprov2'):
    compiled_agent.save('optimized_miprov2.json')
    mlflow.log_artifact('optimized_miprov2.json')
    mlflow.log_param('optimizer', 'MIPROv2')
    mlflow.log_param('num_candidates', 5)

print('MIPROv2 compilation complete')
print('Optimized prompt saved to optimized_miprov2.json')
"
```

**What MIPROv2 does differently from BootstrapFewShot:**
- BootstrapFewShot keeps your instruction and adds examples
- MIPROv2 **rewrites the instruction itself** — it generates candidate instructions, evaluates each one, and picks the best

This often produces system prompts with phrasings you'd never think of — more precise, more constrained, better aligned with the evaluation metric.

**Important:** MIPROv2 takes longer because it generates and evaluates multiple instruction candidates. This is normal.

Use `AskUserQuestion` to confirm the MIPROv2 compilation completed.

---

### Step 6 — Compare All Variants

Run evaluation on all three prompt variants using the same eval set and judges from Stage 5:

```bash
cd <project-dir>
uv run python -c "
import mlflow

mlflow.set_experiment('/Shared/risk-agent')

# Evaluate: Original prompt
# Evaluate: BootstrapFewShot optimized
# Evaluate: MIPROv2 optimized
# ... (run mlflow.evaluate() for each variant)

# Compare results
print('=== Variant Comparison ===')
"
```

Present the comparison as a table:

| Variant | Correctness | Groundedness | Relevance | Overall | Notes |
|---------|------------|-------------|-----------|---------|-------|
| **Original** (manual) | X/5 | X/5 | X/5 | X/5 | Baseline from Stage 5 |
| **BootstrapFewShot** | X/5 | X/5 | X/5 | X/5 | Best examples selected |
| **MIPROv2** | X/5 | X/5 | X/5 | X/5 | Instruction rewritten |

Highlight the winner. Explain WHY it won:
- If BootstrapFewShot won: the examples taught the LLM the right output format and level of detail
- If MIPROv2 won: the rewritten instruction gave clearer guidelines than the manual prompt
- If Original won: the eval set may be too small, or the manual prompt was already well-crafted

Show the actual optimized prompts so the learner can see what DSPy generated:

```bash
# Show the MIPROv2-generated instruction
cat optimized_miprov2.json | python3 -c "import sys,json; print(json.load(sys.stdin)['instruction'])"
```

Use `AskUserQuestion` to discuss the results. Ask: "Does the winning prompt make sense? Do you see why it scored higher?"

---

### Step 7 — Apply the Winner

Update `model_config.yaml` with the winning prompt:

```bash
# Show the before/after diff
diff <(grep -A 20 'system_prompt' model_config.yaml) <(echo "<new prompt>")
```

Write the winning prompt to the config file. Then verify the agent still works:

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

Confirm the response quality matches or exceeds the evaluation scores.

Use `AskUserQuestion` to confirm the updated agent works correctly.

---

### Step 8 — Summary

| Component | Status | Details |
|-----------|--------|---------|
| DSPy Signatures | ✓ Defined | RiskAnswerer with typed I/O contract |
| Training data | ✓ Prepared | Converted from Stage 5 eval set |
| BootstrapFewShot | ✓ Compiled | Best few-shot examples selected |
| MIPROv2 | ✓ Compiled | Instruction text optimized |
| Variant comparison | ✓ Complete | All three variants evaluated |
| Winning prompt | ✓ Applied | Updated model_config.yaml |

**What DSPy achieved:**

| Metric | Before (Manual) | After (DSPy Winner) | Improvement |
|--------|-----------------|--------------------|--------------| 
| Correctness | X/5 | Y/5 | +Z% |
| Groundedness | X/5 | Y/5 | +Z% |
| Relevance | X/5 | Y/5 | +Z% |

**Key takeaways:**
- DSPy replaces artisanal prompt engineering with data-driven compilation
- BootstrapFewShot finds the best examples; MIPROv2 rewrites the instructions
- All variants are logged to MLflow for reproducibility and comparison
- The winning prompt is applied to model_config.yaml — no code changes needed
- Manual prompt tuning before DSPy is a best practice — the domain expert provides intent, DSPy refines it
- DSPy works best with 50+ training examples and a strong metric (the LLM judges from Stage 5)

**Where DSPy runs in the production workflow:**
- **Here (Stage 6):** You ran DSPy locally to understand the mechanics
- **In production (Stage 11):** Domain experts trigger DSPy as a Databricks Job from the Coliseum Playground, after their custom prompt passes the Candidate Gate, to boost its score on the Automated Gate

**What the agent has now (Stages 1-6 complete):**
- ResponsesAgent with predict() and predict_stream()
- Three governed UC function tools
- Full MLflow tracing
- Quantitative evaluation with LLM judges (the quality backbone)
- DSPy optimization capability (reusable as a Playground job)

**Next:** Run `/silver-databricks-agents:register-agent` to register the agent in the MLflow Model Registry and run the Automated Gate — which uses the same judges to compare candidate vs champion.

---

After presenting the summary, use `AskUserQuestion` to offer the next stage:

- **"Continue to Stage 7 — Register Agent" (Recommended)** — description: "Run `/silver-databricks-agents:register-agent` now"
- **"Stop here"** — description: "I'll continue later"

If the user chooses to continue, invoke the next skill immediately using the Skill tool: `Skill({ skill: "silver-databricks-agents:register-agent" })`.
