import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

export default function SemanticView() {
  return (
    <div className="stack">
      <Callout icon="📐">
        <p>
          <code>gold_segment_portfolio</code> answers one question (portfolio by segment). A{" "}
          <strong>Metric View</strong> answers <em>every</em> slice of the same governed billing
          measures — by region, credit rating, contract type, month — from one definition.
        </p>
        <p>
          <code>MEASURE()</code> functions define KPIs <em>once</em> so they can't drift between
          dashboards, notebooks, and Genie. When Genie answers "total billed by region" it uses
          the same <code>MEASURE(total_billed)</code> as the chart tile — they can never disagree.
        </p>
      </Callout>

      <TutorialGuide title="What to do in stage 11 — create the Metric View">
        <ol>
          <li>
            Open <code>sql/portfolio_metrics.sql</code> in the repo — review the measures (
            <code>total_billed</code>, <code>invoice_count</code>, <code>overdue_amount</code>,{" "}
            <code>overdue_ratio</code>) and dimensions (<code>segment</code>, <code>region</code>,{" "}
            <code>credit_rating</code>, <code>contract_type</code>, <code>status</code>,{" "}
            <code>invoice_date</code>).
          </li>
          <li>
            Paste the full SQL into the <strong>Databricks SQL editor</strong> and run. The{" "}
            <code>WITH METRICS</code> YAML block is finicky over the CLI — use the editor.
          </li>
          <li>
            Query the metric view — one definition, any slice:
            <pre className="erd">{`-- By segment:
SELECT segment, MEASURE(total_billed) AS total_billed
FROM silverline.gold.portfolio_metrics GROUP BY segment;

-- By region and contract type (no new SQL logic, just a different GROUP BY):
SELECT region, contract_type, MEASURE(overdue_ratio) AS overdue_ratio
FROM silverline.gold.portfolio_metrics GROUP BY region, contract_type;`}</pre>
          </li>
          <li>
            Verify the metric view matches the physical gold total:
            <pre className="erd">{`WITH m AS (SELECT MEASURE(total_billed) tb FROM silverline.gold.portfolio_metrics),
     g AS (SELECT sum(total_billed)     tb FROM silverline.gold.gold_contract_aging)
SELECT (SELECT tb FROM m) AS metric_view_billed,
       (SELECT tb FROM g) AS gold_billed,
       CASE WHEN (SELECT tb FROM m) <=> (SELECT tb FROM g)
            THEN 'MATCH' ELSE 'DRIFT' END`}</pre>
            Expect: <strong>MATCH</strong>
          </li>
          <li>
            <em>Optional:</em> run <code>11.2_why_metrics</code> notebook to see the "average of
            averages" trap — a hand-rolled overdue ratio can be 7.5× wrong vs the governed{" "}
            <code>MEASURE()</code>.
          </li>
        </ol>
      </TutorialGuide>
    </div>
  );
}
