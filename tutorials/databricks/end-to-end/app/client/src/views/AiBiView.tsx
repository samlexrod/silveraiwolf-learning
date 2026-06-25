import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

export default function AiBiView() {
  return (
    <div className="stack">
      <Callout icon="🤖">
        <p>
          <strong>AI/BI dashboards and Genie</strong> both read the same{" "}
          <code>portfolio_metrics</code> Metric View — so a chart tile and a Genie answer for
          "total billed" can never disagree. Genie translates plain English into SQL using the
          governed <code>MEASURE()</code> definitions, not guessed <code>SUM()</code> joins.
        </p>
        <p>
          This is the payoff of the whole pipeline: a non-technical user asks a question in plain
          English and gets back an exact, governed answer that matches the dashboard — because both
          are powered by the same semantic layer you built in stage 11.
        </p>
      </Callout>

      <TutorialGuide title="What to do in stage 12 — AI/BI dashboard + Genie">
        <ol>
          <li>
            Create the <strong>AI/BI dashboard</strong> from{" "}
            <code>dashboards/portfolio_dashboard.lvdash.json</code>:
            <pre className="erd">{`databricks lakeview create \\
  --display-name "Silverline Capital — Portfolio (governed metrics)" \\
  --warehouse-id "$DATABRICKS_WAREHOUSE_ID" \\
  --serialized-dashboard "$(cat dashboards/portfolio_dashboard.lvdash.json)"

databricks lakeview publish <dashboard_id> \\
  --warehouse-id "$DATABRICKS_WAREHOUSE_ID" --embed-credentials`}</pre>
            Open it in the UI and confirm three tiles: billed by segment, billed by contract type,
            overdue ratio by region — all using <code>MEASURE(...)</code>.
          </li>
          <li>
            Create the <strong>Genie space</strong> from{" "}
            <code>dashboards/genie_space.json</code>:
            <pre className="erd">{`databricks genie create-space "$DATABRICKS_WAREHOUSE_ID" \\
  "$(cat dashboards/genie_space.json)" \\
  --title "Silverline Capital — Portfolio Genie"`}</pre>
          </li>
          <li>
            Open the Genie space and ask in natural language:
            <ul>
              <li>
                <em>"What is the total billed by segment?"</em> → expect{" "}
                <code>MEASURE(total_billed) GROUP BY segment</code>
              </li>
              <li>
                <em>"Which region has the highest overdue ratio?"</em> → expect{" "}
                <code>MEASURE(overdue_ratio) GROUP BY region</code>
              </li>
            </ul>
          </li>
          <li>
            Run <code>12.2_genie_programmatic</code> notebook — Genie as a programmatic service:
            SDK (<code>w.genie.start_conversation_and_wait</code>), multi-turn, CLI (
            <code>databricks genie start-conversation</code>), and an <code>ai_query()</code> call
            against a credit memo.
          </li>
        </ol>

        <table>
          <thead>
            <tr>
              <th>Without semantic layer</th>
              <th>With Metric View + Genie</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Genie guesses <code>SUM()</code> / joins → can be wrong</td>
              <td>Uses <code>MEASURE(total_billed)</code> → exact, governed</td>
            </tr>
            <tr>
              <td>Dashboard SQL + Genie SQL can drift</td>
              <td>Both reference the same measure definition</td>
            </tr>
            <tr>
              <td>"Overdue ratio" reimplemented per consumer</td>
              <td>One definition → dashboard == Genie == gold</td>
            </tr>
          </tbody>
        </table>
      </TutorialGuide>
    </div>
  );
}
