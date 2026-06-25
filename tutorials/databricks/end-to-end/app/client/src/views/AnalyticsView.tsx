import Callout from "../Callout";

export default function AnalyticsView() {
  return (
    <div className="stack">
      <Callout icon="📈">
        <p>
          A <strong>Metric View</strong> is Databricks' governed semantic layer — a SQL object backed by
          gold tables that defines business metrics with <code>MEASURE()</code> functions <em>once</em>.
          Every downstream consumer (dashboards, notebooks, AI queries) uses the exact same calculation,
          so there's no "whose numbers are right?" debate across teams.
        </p>
        <p>
          <strong>Genie (AI/BI)</strong> sits on top: non-technical users ask natural-language questions
          and Databricks translates them into SQL against the governed Metric View — no raw table access,
          no ad-hoc definitions. Once the warehouse data source is wired in, this view will render the
          live governed numbers as interactive charts.
        </p>
      </Callout>
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
