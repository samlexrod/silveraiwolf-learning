# Authoring conventions

Shared conventions for every tutorial in this repo. A tutorial's own `CLAUDE.md` may layer specifics on top.

## The shape of a tutorial

- **One plugin, one command, ordered stages.** The plugin exposes a single `commands/start.md` orchestrator.
  It resolves paths, loads/creates `PROGRESS.md`, shows where the learner is, and walks **one stage at a
  time**, advancing only on explicit confirmation. Stages are plain markdown under `stages/NN-<name>.md` —
  **not** invokable skills (that keeps the command menu clean).
- **Resumable state.** Progress is persisted to a human-readable `PROGRESS.md` in the tutorial dir
  (gitignored). A fresh chat re-reads it and resumes at the current stage.

## Stage-doc conventions

1. Start each stage with the **explain-then-start gate** (copy the `<!-- gate:explain-then-start -->` block
   from an existing stage): explain what the stage does/provisions and its cost, then an `AskUserQuestion`
   ("Start the stage, or keep asking?"). Only proceed on **Start**.
2. **Open with cost framing that matches the platform.** Free-tier tutorials state cost as fair-use
   **quota**, never $. Any real-money step (a learner's own cloud account) is an explicit **opt-in** callout.
3. `## Section N — <title>` interactive steps; end each with **`Pause.`** + an `AskUserQuestion`.
4. End with a `## Recap`. The orchestrator (`commands/start.md`) owns progression and the `Next:` prompts —
   stage docs don't chain themselves.
5. Reference sibling stages by bare name (e.g. "the `seed` stage"), not as slash-commands.

## Build/verify model

- **Claude authors** stages, scripts, notebooks, manifests. **Claude runs the CLI/local plumbing** (auth,
  provisioning, headless verification) so the learner doesn't paste output back.
- **The learner runs the hands-on workload** — notebooks in their own workspace, browser-only UI actions —
  and reports results.
- **Provision via CLI/code, never the UI** — production is automation. The UI is for awareness only.
- **Deliver data workloads as notebooks** the learner runs (that's where the learning happens); keep infra
  as CLI/code.
- **No-faith rule:** a stage is "done" only after a live check passes. Verify the platform mechanic
  in-workspace before committing an approach — docs lag.

## Naming

- Plugin + command: `silver-<topic>-<name>` → `/silver-<topic>-<name>:start`.
- Keep catalog names aligned across tutorials so skills/lessons transfer.
