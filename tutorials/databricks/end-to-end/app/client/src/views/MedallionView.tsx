import Callout from "../Callout";

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
