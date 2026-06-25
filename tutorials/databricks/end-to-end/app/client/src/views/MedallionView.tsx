import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

export default function MedallionView() {
  return (
    <div className="stack">
      <Callout icon="🏗️">
        <p>
          The <strong>medallion architecture</strong> is the standard Lakehouse data quality pattern. Raw data
          from Lakebase lands in <strong>Bronze</strong> as-is — append-only, no transforms. A dbt pipeline
          then cleans, de-dupes, and joins it into <strong>Silver</strong> (conformed types, nulls handled).
          Another pass aggregates it into <strong>Gold</strong>: business-level tables like{" "}
          <code>gold_segment_portfolio</code> that BI tools and ML models query directly.
        </p>
        <p>
          Each layer is a <strong>Delta Lake</strong> table in the Databricks SQL warehouse — a different
          store from Lakebase Postgres. Delta gives you ACID transactions, time travel, and incremental
          processing on top of cloud object storage.
        </p>
      </Callout>
      <div className="flow">
        <div className="layer bronze"><b>bronze</b><span>raw / ingested</span></div>
        <span className="arrow">→</span>
        <div className="layer silver"><b>silver</b><span>cleaned / conformed</span></div>
        <span className="arrow">→</span>
        <div className="layer gold"><b>gold</b><span>business / serving</span></div>
      </div>
      <TutorialGuide title="What stages 07–08 did in the tutorial">
        <p>
          <strong>Stage 07 (Ingest)</strong> registered the Lakebase Postgres database in Unity Catalog
          as a <em>native catalog</em> (<code>lakebase_silverline_oltp</code>). That made its tables
          queryable directly from the SQL warehouse as if they were Delta tables — no ETL pipeline, no
          copy yet. Then it ran <strong>CTAS</strong> (Create Table As Select) to snapshot all 9 tables
          into Delta as <code>silverline.bronze.*</code>:
        </p>
        <pre className="erd">{`CREATE OR REPLACE TABLE silverline.bronze.customers
  AS SELECT * FROM lakebase_silverline_oltp.public.customers;
-- … repeated for all 9 tables`}</pre>
        <p>
          <strong>Stage 08 (Medallion)</strong> ran <strong>dbt</strong> models that transform bronze
          into silver and gold. dbt is a SQL-first transformation tool: each model is a{" "}
          <code>.sql</code> file that becomes a table or view, with dependencies tracked as a DAG.
        </p>
        <table>
          <thead><tr><th>Layer</th><th>Tables built</th><th>What changed</th></tr></thead>
          <tbody>
            <tr>
              <td><strong>Silver</strong></td>
              <td><code>silver_customers · silver_contracts · silver_invoices · …</code></td>
              <td>Nulls handled, types cast, FK joins applied, status pipelines conformed</td>
            </tr>
            <tr>
              <td><strong>Gold</strong></td>
              <td><code>gold_segment_portfolio · gold_contract_aging</code></td>
              <td>Business aggregates — portfolio value by segment, aging buckets per contract</td>
            </tr>
          </tbody>
        </table>
        <p style={{ marginTop: 8 }}>
          Each layer is a <strong>Delta Lake</strong> table — ACID transactions, time travel (
          <code>VERSION AS OF N</code>), and lineage tracked automatically in Unity Catalog.
        </p>
      </TutorialGuide>

      <div className="soon-panel">
        <h3>🏗️ Wiring this up next</h3>
        <p className="muted">
          The medallion tables (<code>silver_*</code>, <code>gold_*</code>) are Delta tables in the
          <b> Databricks SQL warehouse</b> — a different store than Lakebase Postgres. I'm adding that as a
          second data source on the server, then this view will show each layer's tables and counts lighting
          up as the medallion builds.
        </p>
      </div>
    </div>
  );
}
