import { pool } from "./db.js";

/**
 * One-time setup: a trigger function that pg_notify()s every INSERT/UPDATE/DELETE
 * on the demo tables onto the `silverline_changes` channel. The server LISTENs on
 * it (pubsub.ts) and turns each event into a GraphQL subscription push.
 * Idempotent — safe to re-run. (Verified: Lakebase PG17 supports LISTEN/NOTIFY.)
 */
const SQL = `
CREATE OR REPLACE FUNCTION silverline_notify() RETURNS trigger AS $$
DECLARE rec RECORD;
BEGIN
  rec := COALESCE(NEW, OLD);
  PERFORM pg_notify(
    'silverline_changes',
    json_build_object(
      'table', TG_TABLE_NAME,
      'op',    TG_OP,
      'ts',    extract(epoch from now()),
      'row',   row_to_json(rec)
    )::text
  );
  RETURN rec;
END;
$$ LANGUAGE plpgsql;
`;

const tables = ["customers", "contracts", "invoices"];

const client = await pool.connect();
try {
  await client.query(SQL);
  for (const t of tables) {
    await client.query(`DROP TRIGGER IF EXISTS trg_silverline_notify_${t} ON ${t}`);
    await client.query(
      `CREATE TRIGGER trg_silverline_notify_${t}
       AFTER INSERT OR UPDATE OR DELETE ON ${t}
       FOR EACH ROW EXECUTE FUNCTION silverline_notify()`,
    );
  }
  console.log(`✅ notify triggers installed on: ${tables.join(", ")}`);
} finally {
  client.release();
  await pool.end();
}
