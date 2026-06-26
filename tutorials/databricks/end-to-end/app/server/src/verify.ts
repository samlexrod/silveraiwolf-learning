import * as dbx from "./databricks.js";
import { isListening, requirePool, warehouse } from "./session.js";
import { defaultTutorial } from "./tutorial-loader.js";
import type {
  CheckDef, SqlCheck, PgCheck, PgEachCheck, PgOrRestCheck, RestCheck, StateCheck,
} from "./tutorial-types.js";

export type Check = { name: string; passed: boolean; detail: string };
export type VerifyResult = { passed: boolean; checks: Check[] };

// ── SQL helpers ───────────────────────────────────────────────────────────────

async function sql(statement: string): Promise<string[][]> {
  const wh = warehouse();
  const res = await dbx.runSql(wh.host, wh.token, wh.id, statement);
  if (res.status?.state === "FAILED") {
    throw new Error(res.status.error?.message ?? "SQL statement failed");
  }
  return (res.result?.data_array ?? []) as string[][];
}

// ── Condition evaluators ──────────────────────────────────────────────────────

type EvalResult = { passed: boolean; detail: string; count?: number; found?: string[] };

function evalSqlCondition(
  condition: SqlCheck["condition"],
  rows: string[][],
): EvalResult {
  switch (condition.op) {
    case "rows_gte":
      return { passed: rows.length >= condition.n, detail: `${rows.length} rows` };
    case "count_gt": {
      const n = parseInt(rows[0]?.[0] ?? "0", 10);
      return { passed: n > condition.n, detail: `${n} rows`, count: n };
    }
    case "all_in_column": {
      const found = rows.map((r) => r[condition.column]).filter(Boolean);
      const missing = condition.values.filter((v) => !found.includes(v));
      return {
        passed: missing.length === 0,
        detail: found.join(", "),
        found,
      };
    }
  }
}

function evalPgCondition(
  condition: PgCheck["condition"],
  rows: Record<string, unknown>[],
): EvalResult {
  switch (condition.op) {
    case "rows_gte":
      return { passed: rows.length >= condition.n, detail: `${rows.length} rows` };
    case "count_gt": {
      const n = Number(rows[0]?.c ?? rows[0]?.count ?? 0);
      return { passed: n > condition.n, detail: `${n} rows`, count: n };
    }
  }
}

function applyTemplate(
  template: string | undefined,
  fallback: string,
  vars: Record<string, unknown>,
): string {
  if (!template) return fallback;
  return template.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}

// ── Per-check executors ───────────────────────────────────────────────────────

async function execSql(check: SqlCheck): Promise<Check> {
  const rows = await sql(check.statement);
  const ev = evalSqlCondition(check.condition, rows);
  if (!ev.passed) throw new Error(check.errorHint);
  return {
    name: check.name,
    passed: true,
    detail: applyTemplate(check.successTemplate, ev.detail, { count: ev.count, found: ev.found?.join(", ") }),
  };
}

async function execPg(check: PgCheck): Promise<Check> {
  const pool = requirePool();
  const { rows } = await pool.query<Record<string, unknown>>(check.query);
  const ev = evalPgCondition(check.condition, rows);
  if (!ev.passed) throw new Error(check.errorHint);
  return {
    name: check.name,
    passed: true,
    detail: applyTemplate(check.successTemplate, ev.detail, { count: ev.count }),
  };
}

function expandPgEach(check: PgEachCheck): PgCheck[] {
  return check.tables.map((table) => ({
    type: "pg" as const,
    name: check.name_template.replace(/\{table\}/g, table),
    query: check.query_template.replace(/\{table\}/g, table),
    condition: check.condition,
    successTemplate: check.successTemplate?.replace(/\{table\}/g, table),
    errorHint: check.errorHint_template.replace(/\{table\}/g, table),
  }));
}

async function execPgOrRest(check: PgOrRestCheck): Promise<Check> {
  try {
    const pool = requirePool();
    const { rows } = await pool.query<{ version: string }>(check.pg_query);
    const ver = (rows[0]?.version ?? "").split(" ").slice(0, 2).join(" ");
    return { name: check.name, passed: true, detail: `connected — ${ver}` };
  } catch {
    const wh = warehouse();
    const projects: any[] = await dbx.listProjects(wh.host, wh.token);
    if (!projects.length) throw new Error(check.errorHint);
    const p = projects.find((p) => /silverline/i.test(p.name ?? "")) ?? projects[0];
    return { name: check.name, passed: true, detail: `${p.name} (${p.state ?? p.status ?? "unknown"})` };
  }
}

async function execRest(check: RestCheck): Promise<Check> {
  const wh = warehouse();
  let items: any[];
  try {
    items =
      check.fn === "listDashboards"
        ? await dbx.listDashboards(wh.host, wh.token)
        : await dbx.listGenieSpaces(wh.host, wh.token);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (/404|not found/i.test(msg) && check.on_404) throw new Error(check.on_404);
    throw e;
  }
  const { fields, pattern, flags } = check.condition;
  const regex = new RegExp(pattern, flags ?? "i");
  const item = items.find((item) => fields.some((f) => regex.test(item[f] ?? "")));
  if (!item) throw new Error(check.errorHint);
  return {
    name: check.name,
    passed: true,
    detail: applyTemplate(check.successTemplate, item[fields[0]] ?? "", item),
  };
}

function execState(check: StateCheck): Check {
  if (check.key === "isListening") {
    if (!isListening()) throw new Error(check.errorHint);
    return { name: check.name, passed: true, detail: check.successTemplate ?? "active" };
  }
  throw new Error(`unknown state key: ${check.key}`);
}

// ── Dispatcher ────────────────────────────────────────────────────────────────

async function safeExec(fn: () => Promise<Check> | Check): Promise<Check> {
  try {
    return await fn();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return { name: "check", passed: false, detail: msg };
  }
}

async function runCheck(check: CheckDef): Promise<Check[]> {
  if (check.type === "pg_each") {
    return Promise.all(expandPgEach(check).map((c) => safeExec(() => execPg(c)).then((r) => ({ ...r, name: c.name }))));
  }
  const result = await safeExec(() => {
    switch (check.type) {
      case "sql":      return execSql(check);
      case "pg":       return execPg(check);
      case "pg_or_rest": return execPgOrRest(check);
      case "rest":     return execRest(check);
      case "state":    return Promise.resolve(execState(check));
    }
  });
  return [{ ...result, name: check.name }];
}

// ── Public entry point ────────────────────────────────────────────────────────

export async function verifyStage(id: string): Promise<VerifyResult> {
  const config = defaultTutorial();
  const stage = config.stages.find((s) => s.id === id);

  if (!stage?.verify) {
    return {
      passed: true,
      checks: [{ name: "No automated checks for this stage", passed: true, detail: "Mark as done when you have completed the steps above." }],
    };
  }

  const checks = (await Promise.all(stage.verify.checks.map(runCheck))).flat();
  return { passed: checks.every((c) => c.passed), checks };
}
