import * as dbx from "./databricks.js";
import { isListening, requirePool, warehouse } from "./session.js";

export type Check = { name: string; passed: boolean; detail: string };
export type VerifyResult = { passed: boolean; checks: Check[] };

/** Run one SQL statement against the Databricks warehouse; returns data_array rows. */
async function sql(statement: string): Promise<string[][]> {
  const wh = warehouse();
  const res = await dbx.runSql(wh.host, wh.token, wh.id, statement);
  if (res.status?.state === "FAILED") {
    throw new Error(res.status.error?.message ?? "SQL statement failed");
  }
  return (res.result?.data_array ?? []) as string[][];
}

async function safeCheck(name: string, fn: () => Promise<string>): Promise<Check> {
  try {
    const detail = await fn();
    return { name, passed: true, detail };
  } catch (e) {
    return { name, passed: false, detail: e instanceof Error ? e.message : String(e) };
  }
}

// ─── stage-specific checks ────────────────────────────────────────────────────

const STAGE_CHECKS: Record<string, () => Promise<VerifyResult>> = {
  "landing-zone": async () => {
    const checks = await Promise.all([
      safeCheck("silverline catalog exists", async () => {
        const rows = await sql(`SHOW CATALOGS LIKE 'silverline'`);
        if (!rows.length) throw new Error("Catalog 'silverline' not found — run: databricks catalogs create silverline");
        return "catalog silverline found";
      }),
      safeCheck("bronze, silver, gold schemas present", async () => {
        const rows = await sql(
          `SELECT schema_name FROM silverline.information_schema.schemata
           WHERE schema_name IN ('bronze','silver','gold')
           ORDER BY schema_name`,
        );
        const found = rows.map((r) => r[0]).filter(Boolean);
        const missing = ["bronze", "silver", "gold"].filter((s) => !found.includes(s));
        if (missing.length) throw new Error(`Missing schemas: ${missing.join(", ")}`);
        return `schemas: ${found.join(", ")}`;
      }),
      safeCheck("managed volume in silverline.bronze", async () => {
        const rows = await sql(`SHOW VOLUMES IN silverline.bronze`);
        if (!rows.length) throw new Error("No volumes in silverline.bronze — run the landing-zone notebook");
        // SHOW VOLUMES cols: volume_catalog, volume_schema, volume_name, …
        const name = rows[0][2] ?? rows[0][0] ?? "volume";
        return `volume '${name}' found`;
      }),
    ]);
    return { passed: checks.every((c) => c.passed), checks };
  },

  "provision": async () => {
    const checks = await Promise.all([
      safeCheck("Lakebase project is provisioned and reachable", async () => {
        // Primary: if the pg pool is live, the project exists and is running.
        try {
          const pool = requirePool();
          const { rows } = await pool.query("SELECT version()");
          const ver = ((rows[0]?.version as string) ?? "").split(" ").slice(0, 2).join(" ");
          return `connected — ${ver}`;
        } catch {
          // Pool not ready yet: fall back to REST list — accept any Lakebase project.
          const wh = warehouse();
          const projects: any[] = await dbx.listProjects(wh.host, wh.token);
          if (!projects.length) {
            throw new Error("No Lakebase projects found — run: databricks postgres create-project silverline-oltp");
          }
          const p = projects.find((p) => /silverline/i.test(p.name ?? "")) ?? projects[0];
          const state = p.state ?? p.status ?? "unknown";
          return `${p.name} (${state})`;
        }
      }),
    ]);
    return { passed: checks.every((c) => c.passed), checks };
  },

  "seed": async () => {
    const TABLES = [
      "customers", "vendors", "equipment", "applications", "contracts",
      "contract_assets", "payment_schedule", "invoices", "payments",
    ];
    const pool = requirePool();
    const checks = await Promise.all(
      TABLES.map((t) =>
        safeCheck(`${t} has rows`, async () => {
          const { rows } = await pool.query(`SELECT count(*)::int AS c FROM ${t}`);
          const n = rows[0].c as number;
          if (n === 0) throw new Error(`Table '${t}' is empty — run the seed notebook`);
          return `${n} rows`;
        }),
      ),
    );
    return { passed: checks.every((c) => c.passed), checks };
  },

  "ingest": async () => {
    const checks = await Promise.all([
      safeCheck("bronze schema has Delta tables", async () => {
        const rows = await sql(`SHOW TABLES IN silverline.bronze`);
        // SHOW TABLES cols: namespace, tableName, isTemporary
        const tables = rows.filter((r) => r[2] !== "true");
        if (tables.length < 2) {
          throw new Error(`Only ${tables.length} table(s) in silverline.bronze — run the ingest notebook`);
        }
        const names = tables.slice(0, 4).map((r) => r[1]).join(", ");
        return `${tables.length} tables (${names}${tables.length > 4 ? "…" : ""})`;
      }),
      safeCheck("bronze.customers has rows", async () => {
        const rows = await sql(`SELECT count(*) FROM silverline.bronze.customers`);
        const n = parseInt(rows[0]?.[0] ?? "0", 10);
        if (n === 0) throw new Error("bronze.customers is empty");
        return `${n} rows`;
      }),
    ]);
    return { passed: checks.every((c) => c.passed), checks };
  },

  "medallion": async () => {
    const checks = await Promise.all([
      safeCheck("silver tables exist", async () => {
        const rows = await sql(`SHOW TABLES IN silverline.silver`);
        if (rows.length < 2) throw new Error("No silver tables found — run the medallion notebooks");
        return `${rows.length} silver tables`;
      }),
      safeCheck("gold_segment_portfolio has rows", async () => {
        const rows = await sql(`SELECT count(*) FROM silverline.gold.gold_segment_portfolio`);
        const n = parseInt(rows[0]?.[0] ?? "0", 10);
        if (n === 0) throw new Error("gold_segment_portfolio is empty");
        return `${n} rows`;
      }),
      safeCheck("gold_contract_aging has rows", async () => {
        const rows = await sql(`SELECT count(*) FROM silverline.gold.gold_contract_aging`);
        const n = parseInt(rows[0]?.[0] ?? "0", 10);
        if (n === 0) throw new Error("gold_contract_aging is empty");
        return `${n} rows`;
      }),
    ]);
    return { passed: checks.every((c) => c.passed), checks };
  },

  "refresh": async () => {
    const pool = requirePool();
    const checks = await Promise.all([
      safeCheck("pg_notify triggers exist on source tables", async () => {
        const { rows } = await pool.query<{ c: number }>(
          `SELECT count(*)::int AS c FROM pg_trigger
           WHERE tgrelid = ANY(ARRAY[
             'customers'::regclass,
             'contracts'::regclass,
             'invoices'::regclass
           ]::oid[])`,
        );
        const n = rows[0].c;
        if (n === 0) {
          throw new Error("No change-notification triggers found — complete the refresh notebook to add pg_notify triggers");
        }
        return `${n} trigger(s) on customers, contracts, invoices`;
      }),
      safeCheck("server is actively listening for changes", async () => {
        if (!isListening()) {
          throw new Error("LISTEN connection not active — reconnect via the Connect step to re-establish it");
        }
        return "LISTEN silverline_changes active";
      }),
      safeCheck("silver_invoices rebuilt after change-set", async () => {
        const rows = await sql(`SELECT count(*) FROM silverline.silver.silver_invoices`);
        const n = parseInt(rows[0]?.[0] ?? "0", 10);
        if (n === 0) throw new Error("silver_invoices is empty — re-run the dbt medallion after applying the change-set");
        return `${n} rows`;
      }),
      safeCheck("gold_contract_aging rebuilt after change-set", async () => {
        const rows = await sql(`SELECT count(*) FROM silverline.gold.gold_contract_aging`);
        const n = parseInt(rows[0]?.[0] ?? "0", 10);
        if (n === 0) throw new Error("gold_contract_aging is empty — re-run the dbt medallion after applying the change-set");
        return `${n} rows`;
      }),
    ]);
    return { passed: checks.every((c) => c.passed), checks };
  },

  "business-layer": async () => {
    const checks = await Promise.all([
      safeCheck("customer_360 view exists in silverline.gold", async () => {
        const rows = await sql(`SHOW VIEWS IN silverline.gold LIKE 'customer_360'`);
        if (!rows.length) throw new Error("customer_360 view not found — run the business-layer notebook");
        return "customer_360 view found";
      }),
      safeCheck("gold tables have COMMENT documentation", async () => {
        const rows = await sql(
          `SELECT count(*) FROM silverline.information_schema.tables
           WHERE table_schema = 'gold' AND comment IS NOT NULL AND comment != ''`,
        );
        const n = parseInt(rows[0]?.[0] ?? "0", 10);
        if (n === 0) throw new Error("No gold tables have COMMENTs yet — run the business-layer notebook");
        return `${n} documented table(s)`;
      }),
    ]);
    return { passed: checks.every((c) => c.passed), checks };
  },

  "semantic": async () => {
    const checks = await Promise.all([
      safeCheck("portfolio_metrics metric view exists", async () => {
        const rows = await sql(`SHOW TABLES IN silverline.gold LIKE 'portfolio_metrics'`);
        if (!rows.length) throw new Error("portfolio_metrics not found — run the semantic notebook");
        return "portfolio_metrics found";
      }),
      safeCheck("portfolio_metrics returns data", async () => {
        const rows = await sql(`SELECT count(*) FROM silverline.gold.portfolio_metrics`);
        const n = parseInt(rows[0]?.[0] ?? "0", 10);
        if (n === 0) throw new Error("portfolio_metrics returns no rows");
        return `${n} rows`;
      }),
    ]);
    return { passed: checks.every((c) => c.passed), checks };
  },

  "ai-bi": async () => {
    const wh = warehouse();
    const checks = await Promise.all([
      safeCheck("portfolio_metrics metric view has data", async () => {
        const rows = await sql(`SELECT count(*) FROM silverline.gold.portfolio_metrics`);
        const n = parseInt(rows[0]?.[0] ?? "0", 10);
        if (n === 0) throw new Error("portfolio_metrics is empty — check the semantic stage completed first");
        return `${n} rows`;
      }),
      safeCheck("Silverline AI/BI dashboard published", async () => {
        const dashboards = await dbx.listDashboards(wh.host, wh.token);
        const d = dashboards.find((d: any) => /silverline/i.test(d.display_name ?? ""));
        if (!d) {
          throw new Error("No Silverline dashboard found — run: databricks lakeview create --display-name \"Silverline Capital...\"");
        }
        return `"${d.display_name}" (${d.dashboard_id?.slice(0, 8)}…)`;
      }),
      safeCheck("Silverline Genie space created", async () => {
        let spaces: any[];
        try {
          spaces = await dbx.listGenieSpaces(wh.host, wh.token);
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          if (/404|not found/i.test(msg)) {
            throw new Error("Genie API not reachable — confirm your workspace has AI/BI Genie enabled");
          }
          throw e;
        }
        const s = spaces.find((s: any) => /silverline/i.test(s.title ?? s.name ?? ""));
        if (!s) {
          throw new Error("No Silverline Genie space found — run: databricks genie create-space ...");
        }
        return `"${s.title ?? s.name}" space found`;
      }),
    ]);
    return { passed: checks.every((c) => c.passed), checks };
  },
};

// ─── public entry point ───────────────────────────────────────────────────────

export async function verifyStage(id: string): Promise<VerifyResult> {
  const fn = STAGE_CHECKS[id];
  if (!fn) {
    return {
      passed: true,
      checks: [
        {
          name: "No automated checks for this stage",
          passed: true,
          detail: "Mark as done when you have completed the steps above.",
        },
      ],
    };
  }
  return fn();
}
