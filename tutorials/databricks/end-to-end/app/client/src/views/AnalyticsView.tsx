export default function AnalyticsView() {
  return (
    <div className="stack">
      <div className="soon-panel">
        <h3>📈 Wiring this up next</h3>
        <p className="muted">
          The governed gold metrics — <code>gold_segment_portfolio</code>, <code>gold_contract_aging</code>,
          and the <b>Metric View</b> — live in the Databricks SQL warehouse. Once the warehouse source is on
          the server, this view renders them as charts you can slice (by segment, region, contract type),
          showing the same governed <code>MEASURE()</code> numbers the tutorial proved.
        </p>
      </div>
    </div>
  );
}
