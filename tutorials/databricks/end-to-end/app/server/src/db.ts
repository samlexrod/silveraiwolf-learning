import "dotenv/config";
import pg from "pg";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const pexec = promisify(execFile);

const {
  LAKEBASE_HOST,
  LAKEBASE_PORT = "5432",
  LAKEBASE_DB = "databricks_postgres",
  LAKEBASE_USER,
  LAKEBASE_EP,
  DATABRICKS_PROFILE = "free",
  DATABRICKS_BIN = "databricks",
  DATABRICKS_HOST,
  SP_CLIENT_ID,
  SP_SECRET,
  LAKEBASE_TOKEN,
} = process.env;

/**
 * Two auth modes for the short-lived Lakebase token (used as the Postgres password):
 *  - "sp"  — service principal M2M (client_credentials). Headless → works in Docker / any machine.
 *            The pg user is the SP's applicationId.
 *  - "cli" — local dev: mint via the Databricks CLI (`free` profile / your user OAuth).
 * Set SP_CLIENT_ID + SP_SECRET (+ DATABRICKS_HOST) to use SP mode automatically.
 */
export const MODE: "sp" | "cli" = SP_CLIENT_ID && SP_SECRET ? "sp" : "cli";
export const PG_USER = MODE === "sp" ? SP_CLIENT_ID! : LAKEBASE_USER!;

let cached: { token: string; exp: number } | null = null;

async function mintSp(): Promise<string> {
  if (!DATABRICKS_HOST) throw new Error("DATABRICKS_HOST required for SP mode");
  const basic = Buffer.from(`${SP_CLIENT_ID}:${SP_SECRET}`).toString("base64");
  const res = await fetch(`${DATABRICKS_HOST}/oidc/v1/token`, {
    method: "POST",
    headers: { Authorization: `Basic ${basic}`, "Content-Type": "application/x-www-form-urlencoded" },
    body: "grant_type=client_credentials&scope=all-apis",
  });
  if (!res.ok) throw new Error(`SP token mint failed: ${res.status} ${await res.text()}`);
  return ((await res.json()) as { access_token: string }).access_token;
}

async function mintCli(): Promise<string> {
  if (!LAKEBASE_EP) throw new Error("LAKEBASE_EP required for CLI mode");
  const { stdout } = await pexec(
    DATABRICKS_BIN,
    ["--profile", DATABRICKS_PROFILE, "postgres", "generate-database-credential", LAKEBASE_EP, "-o", "json"],
    { shell: process.platform === "win32", maxBuffer: 1024 * 1024 },
  );
  return JSON.parse(stdout).token as string;
}

export async function getToken(): Promise<string> {
  if (LAKEBASE_TOKEN) return LAKEBASE_TOKEN;
  const now = Date.now();
  if (cached && cached.exp > now + 60_000) return cached.token;
  const token = MODE === "sp" ? await mintSp() : await mintCli();
  cached = { token, exp: now + 50 * 60_000 };
  console.log(`🔑 minted Lakebase token (${MODE})`);
  return token;
}

export function connConfig(password: string): pg.ClientConfig {
  return {
    host: LAKEBASE_HOST,
    port: Number(LAKEBASE_PORT),
    database: LAKEBASE_DB,
    user: PG_USER,
    password,
    ssl: { rejectUnauthorized: false },
  };
}

export const pool = new pg.Pool({
  host: LAKEBASE_HOST,
  port: Number(LAKEBASE_PORT),
  database: LAKEBASE_DB,
  user: PG_USER,
  password: getToken,
  ssl: { rejectUnauthorized: false },
  max: 5,
});
