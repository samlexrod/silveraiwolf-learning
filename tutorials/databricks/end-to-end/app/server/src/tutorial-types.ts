// Shared TypeScript types for the tutorial config JSON schema.
// The JSON Schema lives at server/data/tutorial.schema.json — keep both in sync.

export interface TutorialConfig {
  id: string;
  name: string;
  description?: string;
  platform?: string;
  tags?: string[];
  stages: StageConfig[];
}

export interface StageConfig {
  id: string;
  phase: string;
  label: string;
  icon: string;
  title: string;
  /** "connect" → render the built-in connect/setup UI instead of StageView */
  special?: "connect";
  content?: StageContent;
  /** Named React widgets rendered after the content sections */
  widgets?: WidgetId[];
  verify?: VerifyConfig;
}

export type WidgetId = "table-browser" | "live-feed";

export interface StageContent {
  callout?: Callout;
  sections: Section[];
}

export interface Callout {
  icon: string;
  /** Markdown — bold, inline code, lists all work */
  body: string;
}

export interface Section {
  heading: string;
  /** Markdown — fenced code blocks, tables, lists */
  body: string;
}

// ── Verify ────────────────────────────────────────────────────────────────────

export interface VerifyConfig {
  checks: CheckDef[];
}

export type CheckDef =
  | SqlCheck
  | PgCheck
  | PgEachCheck
  | PgOrRestCheck
  | RestCheck
  | StateCheck;

interface BaseCheck {
  name: string;
  errorHint: string;
  successTemplate?: string;
}

/** Run a SQL statement on the Databricks warehouse (Delta / metric views) */
export interface SqlCheck extends BaseCheck {
  type: "sql";
  statement: string;
  condition: RowsGte | CountGt | AllInColumn;
}

/** Run a query on the Lakebase Postgres pool */
export interface PgCheck extends BaseCheck {
  type: "pg";
  query: string;
  condition: RowsGte | CountGt;
}

/** One PG count check per table — expands at runtime (seed's 9-table pattern) */
export interface PgEachCheck {
  type: "pg_each";
  /** Template: use {table} → replaced with each table name */
  name_template: string;
  /** Template: use {table} → replaced with each table name */
  query_template: string;
  tables: string[];
  condition: CountGt;
  successTemplate?: string;
  /** Template: use {table} */
  errorHint_template: string;
}

/** Try the PG pool first; fall back to a REST list if pool is not ready */
export interface PgOrRestCheck extends BaseCheck {
  type: "pg_or_rest";
  pg_query: string;
  rest_fn: "listProjects";
}

/** Call a named Databricks REST helper; find a matching item */
export interface RestCheck extends BaseCheck {
  type: "rest";
  fn: "listDashboards" | "listGenieSpaces";
  condition: FindMatch;
  /** Error to surface when the REST endpoint returns 404 */
  on_404?: string;
}

/** Assert a named in-memory server state value */
export interface StateCheck extends BaseCheck {
  type: "state";
  key: "isListening";
}

// ── Conditions ────────────────────────────────────────────────────────────────

/** SQL result has at least n rows */
export interface RowsGte { op: "rows_gte"; n: number }

/** Parse first column of first row as int; assert > n */
export interface CountGt { op: "count_gt"; n: number }

/** All expected values appear in the given column index */
export interface AllInColumn { op: "all_in_column"; column: number; values: string[] }

/** Find an item whose field(s) match a regex pattern */
export interface FindMatch {
  op: "find_match";
  /** Try each field in order until one matches */
  fields: string[];
  pattern: string;
  flags?: string;
}
