import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

export default function IngestView() {
  return (
    <div className="stack">
      <Callout icon="📥">
        <p>
          <strong>Ingest</strong> is how OLTP data enters the Lakehouse. Lakebase is native to
          Databricks, so the first move is <strong>zero-ETL</strong>: register the project as a
          read-only Unity Catalog catalog and query live Postgres tables directly — no copy, no
          pipeline, no lag.
        </p>
        <p>
          When you want a governed Delta copy (with history and the medallion pipeline), you land
          into <code>silverline.bronze</code>. This stage shows four different patterns — from the
          simplest (zero-ETL) to the most complete (managed CDC).
        </p>
      </Callout>

      <TutorialGuide title="What to do in stage 07 — ingest Lakebase into the Lakehouse">
        <ol>
          <li>
            <strong>Register as a native UC catalog</strong> (Claude runs this CLI step via the
            connect stage):
            <pre className="erd">{`databricks --profile free api post \\
  "/api/2.0/postgres/catalogs?catalog_id=lakebase_silverline_oltp" \\
  --json '{"spec":{"postgres_database":"databricks_postgres","branch":"projects/silverline-oltp/branches/production"}}'`}</pre>
            Then verify:
            <pre className="erd">{`mise run sql 'SELECT count(*) FROM lakebase_silverline_oltp.public.customers'`}</pre>
            Expect <strong>60</strong>. This is zero-ETL: live Postgres rows, no copy.
          </li>
          <li>
            Run <code>07.1_native_catalog</code> — explores the live OLTP via SQL (counts, a segment
            join) with zero data movement.
          </li>
          <li>
            Run <code>07.2_ctas_snapshot</code>:
            <pre className="erd">{`CREATE OR REPLACE TABLE silverline.bronze.customers
  AS SELECT * FROM lakebase_silverline_oltp.public.customers;
-- … repeated for all 9 tables`}</pre>
            This is the bronze snapshot the medallion builds on.
          </li>
          <li>
            <em>Optional:</em> <code>07.3_watermark_cdc</code> (watermark-based incremental),{" "}
            <code>07.4_wal_cdc</code> (WAL logical decoding — delete-aware),{" "}
            <code>07.5_lakebase_cdf</code> (native managed CDC, requires external S3 — opt-in).
          </li>
        </ol>

        <table>
          <thead>
            <tr>
              <th>Pattern</th>
              <th>Notebook</th>
              <th>Handles Deletes?</th>
              <th>Needs Cloud?</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["Native query (zero-ETL)", "07.1", "n/a", "No"],
              ["Full CTAS snapshot", "07.2", "Yes (rewrite)", "No"],
              ["Watermark CDC", "07.3", "No", "No"],
              ["WAL logical-decoding CDC", "07.4", "Yes", "No"],
              ["Lakebase CDF (native managed)", "07.5", "Yes", "Yes (S3 for CDF destination)"],
            ].map(([pattern, nb, deletes, cloud]) => (
              <tr key={nb}>
                <td>{pattern}</td>
                <td>
                  <code>{nb}</code>
                </td>
                <td>{deletes}</td>
                <td>{cloud}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TutorialGuide>
    </div>
  );
}
