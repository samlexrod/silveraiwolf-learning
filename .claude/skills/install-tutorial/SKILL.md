---
name: install-tutorial
description: "[Start here] Install the Databricks Free Edition end-to-end tutorial as a Claude Code plugin — one install, then 12 ordered stages. Claude performs the install via the `claude plugin` CLI. Trigger on 'install tutorial', 'set up the databricks tutorial', 'start the databricks free edition tutorial', 'how do I install this', '/install-tutorial', or any request to install or begin the Databricks Free Edition tutorial."
---

# Install the Databricks End-to-End Tutorial (Free Edition)

This repo ships its tutorials as **Claude Code plugins**, listed in the repo-level **`silveraiwolf`**
marketplace (`.claude-plugin/marketplace.json`). The first tutorial is **Databricks end-to-end** (Free
Edition) at `tutorials/databricks/end-to-end/.claude/`. Install it once, then walk **12 ordered stages**
(setup → lakebase → lakehouse → analytics).

> ✅ **Claude can install this for you.** The interactive `/plugin …` slash commands can't be driven by
> Claude, but the **`claude plugin …` CLI can** (run via Bash). So this skill *performs* the install.

## Instructions

### 1. Confirm the marketplace + check current state

```bash
cat .claude-plugin/marketplace.json     # repo-level "silveraiwolf" marketplace + plugins[]
claude plugin marketplace list          # already registered?
claude plugin list                      # already installed?
```

Expected: marketplace **`silveraiwolf`** listing plugin **`silver-databricks-end-to-end`**. Use whatever the
file says if it differs. If it's already installed, skip to step 4 (just remind them to reload/restart).

### 2. Ask the user what to install

**Always ask first** with `AskUserQuestion`; never install blind.

1. From `plugins[]`, list the installable plugin(s). One → name it; several → ask which (multiSelect).
2. Ask the **install source**:
   - **Local (this clone)** — works right now, no commit/push. Recommended while developing/pre-publish.
   - **GitHub** — only after the repo is committed + pushed. Check `git ls-remote --exit-code origin <branch>`;
     if not pushed, steer to Local.

### 3. Perform the install (Claude runs these via Bash)

Both sources use the repo-level **`silveraiwolf`** marketplace → install spec `silver-databricks-end-to-end@silveraiwolf`.

**Local source** — ⚠️ **use the ABSOLUTE repo-root path** (a relative path is misread as a GitHub repo):

```bash
ROOT="$(git rev-parse --show-toplevel)"
claude plugin marketplace add "$ROOT"
claude plugin install silver-databricks-end-to-end@silveraiwolf
claude plugin list | grep -A2 silver-databricks-end-to-end   # confirm: Status ✔ enabled
```

**GitHub source** (after commit + push):

```bash
claude plugin marketplace add samlexrod/silveraiwolf-learning
claude plugin install silver-databricks-end-to-end@silveraiwolf
```

If the marketplace is already registered, `add` errors with "already exists" — fine, proceed to `install`.
Use **one source, not both** (same marketplace name `silveraiwolf` → collision); to switch, first
`claude plugin marketplace remove silveraiwolf`.

### 4. Tell them what happens next

1. **Run `/reload-skills`** to surface the plugin's commands in the **current** session (no restart). If they
   still don't show, start a fresh Claude session.
2. Run **`/silver-databricks-end-to-end:start`** — the Stage 0 roadmap listing all 12 stages.
3. Walk the stages in order: `connect → landing-zone → project → provision → seed → data-api → ingest →
   medallion → refresh → business-layer → semantic → ai-bi`. Each names its precondition + "Next:".
4. Each stage is interactive: Claude runs the CLI/plumbing; the learner runs the notebooks in their own Free
   Edition workspace and reports results.

## Developing this tutorial (important)

A directory-source install **copies files into `~/.claude/plugins/cache/`** — it does NOT live-load from the
repo. After editing any stage/command/manifest, reinstall (`claude plugin update` no-ops when the version is
unchanged):

```bash
claude plugin uninstall silver-databricks-end-to-end@silveraiwolf \
  && claude plugin install silver-databricks-end-to-end@silveraiwolf
```

Then run **`/reload-skills`**. Validate manifests before installing:
`claude plugin validate tutorials/databricks/end-to-end/.claude`.

## Marketplace layout (FYI)

Two `marketplace.json` files exist:
- **`.claude-plugin/marketplace.json`** (repo root, name **`silveraiwolf`**) — the canonical, repo-level
  marketplace that lists every tutorial plugin; used for both local and GitHub installs. `source` for this
  tutorial is `./tutorials/databricks/end-to-end/.claude/plugins/silver-databricks-end-to-end`.
- **`tutorials/databricks/end-to-end/.claude/.claude-plugin/marketplace.json`** (name
  **`silver-databricks-end-to-end`**) — keeps the tutorial dir self-contained for isolated local dev
  (`claude plugin marketplace add "$ROOT/tutorials/databricks/end-to-end/.claude"` →
  `silver-databricks-end-to-end@silver-databricks-end-to-end`).

Both are force-tracked despite the repo's broad `*.json` gitignore (negations: `!**/.claude-plugin/marketplace.json`,
`!**/.claude-plugin/plugin.json`). If a manifest doesn't show up in a clone, check those negations are present.

## Adding more tutorials

Future tutorials add one entry to the repo-level `silveraiwolf` marketplace (`plugins[]`) and live under
`tutorials/<track>/<name>/.claude/plugins/<plugin>/`. This skill installs whichever plugin the user picks.

## Notes
- Primary install spec: `silver-databricks-end-to-end@silveraiwolf` (repo-level marketplace).
- Remove later: `claude plugin uninstall silver-databricks-end-to-end@silveraiwolf`, then
  `claude plugin marketplace remove silveraiwolf`.
