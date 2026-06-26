import pg from "pg";
import * as dbx from "./databricks.js";
import { pubsub, ROW_CHANGED } from "./pubsub.js";

type Conn = {
  host: string; // workspace URL
  token: string; // PAT (in memory only)
  user: string;
  warehouseId: string;
  ep: string;
  lakebaseHost: string;
};

let conn: Conn | null = null;
let pool: pg.Pool | null = null;
let listenClient: pg.Client | null = null;
let credCache: { token: string; exp: number } | null = null;

export function status() {
  return conn
    ? {
        connected: true,
        user: conn.user,
        workspace: conn.host,
        warehouseId: conn.warehouseId,
        lakebaseHost: conn.lakebaseHost,
      }
    : { connected: false, user: null, workspace: null, warehouseId: null, lakebaseHost: null };
}

export function requirePool(): pg.Pool {
  if (!pool) throw new Error("Not connected — configure the workspace first (Setup step).");
  return pool;
}

export function isListening(): boolean {
  return listenClient !== null;
}

export function warehouse() {
  if (!conn) throw new Error("Not connected.");
  return { host: conn.host, token: conn.token, id: conn.warehouseId };
}

async function pgPassword(): Promise<string> {
  if (!conn) throw new Error("Not connected.");
  const now = Date.now();
  if (credCache && credCache.exp > now + 60_000) return credCache.token;
  const t = await dbx.mintPgCredential(conn.host, conn.token, conn.ep);
  credCache = { token: t, exp: now + 50 * 60_000 };
  return t;
}

async function startListener() {
  if (!conn) return;
  const client = new pg.Client({
    host: conn.lakebaseHost,
    port: 5432,
    database: "databricks_postgres",
    user: conn.user,
    password: await pgPassword(),
    ssl: { rejectUnauthorized: false },
  });
  client.on("error", (e) => console.error("listen error:", e.message));
  await client.connect();
  await client.query("LISTEN silverline_changes");
  client.on("notification", (msg) => {
    if (!msg.payload) return;
    try {
      pubsub.publish(ROW_CHANGED, { rowChanged: JSON.parse(msg.payload) });
    } catch {
      /* ignore */
    }
  });
  listenClient = client;
  console.log("👂 LISTEN silverline_changes");
}

/** Configure from a workspace URL + PAT: validate, auto-discover, build the pool, start LISTEN. */
export async function configure(rawHost: string, token: string) {
  const host = rawHost.trim().replace(/\/+$/, "");
  if (!/^https?:\/\//.test(host)) throw new Error("Workspace URL must start with https://");

  const user = await dbx.whoami(host, token); // also validates the PAT

  const whs = await dbx.listWarehouses(host, token);
  const wh = whs.find((w) => /serverless|starter/i.test(w.name)) ?? whs[0];
  if (!wh) throw new Error("No SQL warehouse found in this workspace.");

  const projects = await dbx.listProjects(host, token);
  const proj = projects.find((p) => /silverline-oltp/.test(p.name)) ?? projects[0];
  if (!proj) throw new Error("No Lakebase project found — run the tutorial's provision + seed stages first.");
  const ep = `${proj.name}/branches/production/endpoints/primary`;
  const lakebaseHost = await dbx.endpointHost(host, token, ep);
  if (!lakebaseHost) throw new Error("Lakebase endpoint has no host yet (still provisioning?).");

  // tear down any previous connection
  if (listenClient) await listenClient.end().catch(() => {});
  if (pool) await pool.end().catch(() => {});
  listenClient = null;
  credCache = null;

  conn = { host, token, user, warehouseId: wh.id, ep, lakebaseHost };
  pool = new pg.Pool({
    host: lakebaseHost,
    port: 5432,
    database: "databricks_postgres",
    user,
    password: pgPassword,
    ssl: { rejectUnauthorized: false },
    max: 5,
  });
  await pool.query("SELECT 1"); // prove it connects
  await startListener();
  console.log(`✅ configured for ${user} (warehouse ${wh.id})`);
  return status();
}
