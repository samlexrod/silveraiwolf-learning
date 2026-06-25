export default function MedallionView() {
  return (
    <div className="stack">
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
