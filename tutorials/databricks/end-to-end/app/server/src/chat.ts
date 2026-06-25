import type { Request, Response } from "express";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import Anthropic from "@anthropic-ai/sdk";
import { status } from "./session.js";

const pexec = promisify(execFile);
const ANT_BIN = process.env.ANT_BIN ?? "ant";
const onWin = process.platform === "win32";

// OAuth access token minted by `ant auth login` (cached ~50 min; refreshed via the CLI).
let oauth: { token: string; exp: number } | null = null;

async function antToken(): Promise<string> {
  const { stdout } = await pexec(ANT_BIN, ["auth", "print-credentials", "--access-token"], {
    shell: onWin,
    maxBuffer: 1024 * 1024,
  });
  return stdout.trim();
}

/** Build an Anthropic client: explicit key › OAuth (ant) › ambient env/profile. */
async function clientFor(key?: string): Promise<Anthropic> {
  if (key) return new Anthropic({ apiKey: key });
  if (oauth) {
    if (oauth.exp < Date.now() + 60_000) oauth = { token: await antToken(), exp: Date.now() + 50 * 60_000 };
    return new Anthropic({ authToken: oauth.token, defaultHeaders: { "anthropic-beta": "oauth-2025-04-20" } });
  }
  return new Anthropic(); // ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / ant profile from the environment
}

const SYSTEM = `You are a **read-only Q&A assistant** embedded in the Silverline Lakehouse Explorer — a guided
companion to the "Databricks Free Edition end-to-end" tutorial. Your ONLY job is to answer the learner's
questions about this tutorial and the concepts it teaches.

The tutorial is 12 ordered stages in 4 phases: Setup (connect · landing-zone · project), Lakebase (provision ·
seed · data-api), Lakehouse (ingest · medallion · refresh), Analytics (business-layer · semantic · ai-bi). It
uses a serverless **Lakebase (Postgres 17)** OLTP for a fictional equipment lease/loan company, "Silverline
Capital" — tables: customers, vendors, equipment, applications, contracts, contract_assets, payment_schedule,
invoices, payments — taken through a **medallion** (bronze→silver→gold) and a governed **Metric View** in the
Databricks SQL warehouse, then AI/BI + Genie.

STRICT SCOPE — only answer questions about: the tutorial's stages and what each does; Databricks Free Edition,
Lakebase, Unity Catalog, the medallion architecture, dbt, SQL, Metric Views, AI/BI / Genie; and general
data-engineering concepts **as they relate to this guide**; and the Silverline sample data model. If a
question is outside this scope — general knowledge, unrelated coding help, personal tasks, opinions, anything
not about this tutorial — politely decline in one sentence and point the learner back to the guide. Do not
answer off-topic questions even if you know the answer.

You CANNOT take any actions. You have no tools, no code execution, and no access to the database, workspace,
files, or the internet. You cannot run, query, deploy, modify, or fetch anything — you only explain. If asked
to run code, execute SQL, change settings, or perform a task, say you can't (you're a read-only explainer) and
describe what the learner would do in the tutorial instead. Any code or SQL you show is illustrative only, for
the learner to read and run themselves.

Be concise and practical. Cost on Free Edition is always fair-use **quota**, never dollars.`;

type ChatMsg = { role: "user" | "assistant"; content: string };

// Allowlist — the user picks one in the UI; default to the most capable.
const MODELS = new Set(["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5", "claude-opus-4-7"]);
const DEFAULT_MODEL = "claude-opus-4-8";

// The app condenses the 12-stage tutorial into a few guided views; map each one
// back to the underlying stages so Claude can answer precisely about where they are.
type StepCtx = {
  id?: string;
  phase?: string;
  label?: string;
  title?: string;
  index?: number;
  total?: number;
  status?: "done" | "current" | "locked";
};
const VIEW_STAGES: Record<string, string> = {
  connect: "the connect stage (01)",
  source: "the Lakebase stages — provision · seed · data-api (04–06)",
  refresh: "the refresh stage + live change-data streaming (09)",
  medallion: "the lakehouse stages — ingest · medallion (07–08)",
  analytics: "the analytics stages — business-layer · semantic · ai-bi (10–12)",
};
const clip = (s: unknown, n = 120) => (typeof s === "string" ? s.slice(0, n) : "");

/** One-line "where the learner is" context: workspace connection + the current app view. */
function liveContext(step?: StepCtx): string {
  const conn = status();
  const out: string[] = [];
  out.push(
    conn.connected
      ? `The learner is connected as ${conn.user} (workspace ${conn.workspace}).`
      : `The learner has NOT connected their workspace yet (still on the Connect step).`,
  );
  if (step?.phase && step?.label) {
    const where = step.index && step.total ? ` (view ${step.index} of ${step.total})` : "";
    out.push(`In the visual app they are on the "${clip(step.label)}" view in the ${clip(step.phase)} phase${where}: ${clip(step.title)}.`);
    const stages = step.id && VIEW_STAGES[step.id];
    if (stages) out.push(`That view maps to ${stages} in the full 12-stage tutorial.`);
    if (step.status === "done") out.push(`They have already completed this step and are reviewing it.`);
    else out.push(`This is the step they're actively on — tailor your answer to it unless they ask about something else.`);
  }
  return out.join(" ");
}

export async function chatHandler(req: Request, res: Response): Promise<void> {
  const key = req.header("x-anthropic-key") || (req.body?.apiKey as string | undefined);
  const messages = (req.body?.messages ?? []) as ChatMsg[];
  if (!messages.length) {
    res.status(400).json({ error: "No messages" });
    return;
  }

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders?.();

  // give Claude the live connection state + the step they're on so it can tailor answers
  const sys = `${SYSTEM}\n\nLive context: ${liveContext(req.body?.step as StepCtx | undefined)}`;

  const model = MODELS.has(req.body?.model) ? (req.body.model as string) : DEFAULT_MODEL;

  const client = await clientFor(key);
  try {
    // Plain text Q&A ONLY — no `tools`, so the model cannot execute code, run SQL,
    // touch the DB/workspace, or take any action. Do not add tools here.
    const stream = client.messages.stream({
      model,
      max_tokens: 2048,
      system: sys,
      messages,
    });
    stream.on("text", (t) => res.write(`data: ${JSON.stringify({ text: t })}\n\n`));
    await stream.finalMessage();
    res.write(`data: ${JSON.stringify({ done: true })}\n\n`);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    res.write(`data: ${JSON.stringify({ error: msg })}\n\n`);
  } finally {
    res.end();
  }
}

/** Reports whether the server can authenticate with no user-supplied key, and if the `ant` CLI is present. */
export async function authStatusHandler(_req: Request, res: Response): Promise<void> {
  let antAvailable = false;
  try {
    await pexec(ANT_BIN, ["--version"], { shell: onWin });
    antAvailable = true;
  } catch {
    /* ant not installed */
  }
  if (oauth) {
    res.json({ ambient: true, method: "oauth", antAvailable });
    return;
  }
  try {
    await new Anthropic().models.list({ limit: 1 });
    res.json({ ambient: true, method: "env", antAvailable });
  } catch {
    res.json({ ambient: false, antAvailable });
  }
}

/** "Sign in with Claude" — runs `ant auth login` (browser OAuth), then caches the access token. */
export async function loginHandler(_req: Request, res: Response): Promise<void> {
  try {
    await pexec(ANT_BIN, ["auth", "login"], { shell: onWin, maxBuffer: 1024 * 1024 });
    oauth = { token: await antToken(), exp: Date.now() + 50 * 60_000 };
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ ok: false, error: e instanceof Error ? e.message : String(e) });
  }
}
