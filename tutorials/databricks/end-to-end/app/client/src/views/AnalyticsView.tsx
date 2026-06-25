import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

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
      <TutorialGuide title="What stages 10–12 cover in the tutorial">
        <p>
          <strong>Stage 10 (Business layer)</strong> runs the final dbt models that produce the governed
          gold tables. These are the agreed-upon, single-source-of-truth aggregates the whole business
          queries — not ad-hoc SQL written per dashboard.
        </p>
        <p>
          <strong>Stage 11 (Semantic / Metric View)</strong> creates a{" "}
          <strong>Metric View</strong> over the gold tables. A Metric View is a SQL object with{" "}
          <code>MEASURE()</code> functions that define each KPI once:
        </p>
        <pre className="erd">{`CREATE METRIC VIEW silverline.gold.silverline_metrics
  PRIMARY KEY (contract_id)
  DIMENSIONS (customer_id, contract_type, region, segment)
  MEASURES (
    total_billed   AS SUM(total_due),
    total_paid     AS SUM(paid_amount),
    overdue_amount AS SUM(overdue_amount)
  );`}</pre>
        <p>
          Every downstream tool — SQL queries, dashboards, Genie — uses the exact same{" "}
          <code>MEASURE()</code> definition. No more diverging numbers across teams.
        </p>
        <p>
          <strong>Stage 12 (AI/BI + Genie)</strong> builds a dashboard on the Metric View and enables{" "}
          <strong>Genie</strong> — Databricks' natural-language interface. A non-technical user can type
          "what's the overdue balance by customer segment?" and Genie translates it into the correct SQL
          against the governed metrics. No raw table access, no ad-hoc definitions leaking out.
        </p>
      </TutorialGuide>

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
