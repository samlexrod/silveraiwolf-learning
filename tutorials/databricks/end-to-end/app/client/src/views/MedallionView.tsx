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
      <TutorialGuide title="What to do in stage 08 — three ways to build silver + gold">
        <ol>
          <li>
            Run <strong><code>08.1_build_ddl</code></strong> — defines empty <code>silver_*</code> and{" "}
            <code>gold_*_nb</code> tables (structure only, no data yet).
          </li>
          <li>
            Run <strong><code>08.2_build_dbt</code></strong> — creates and runs a Databricks Job with a
            native <code>dbt task</code>. dbt reads <code>dbt_project/</code> and outputs canonical{" "}
            <code>gold_segment_portfolio</code> and <code>gold_contract_aging</code>.
          </li>
          <li>
            Run <strong><code>08.3_build_sdp</code></strong> — creates and runs a Lakeflow/SDP declarative
            pipeline from <code>sdp_project/</code>. Uses <code>@dlt.table</code> +{" "}
            <code>@dlt.expect_or_drop</code> quality checks → <code>*_sdp</code> tables.
          </li>
          <li>
            Run <strong><code>08.4_build_notebook</code></strong> — runs a Workflow Job that{" "}
            <code>INSERT OVERWRITE</code>s the <code>_nb</code> tables defined in step 1 — the
            notebook/ELT approach.
          </li>
          <li>
            Run <strong><code>08.5_parity</code></strong> — compares all three gold outputs side-by-side
            with symmetric <code>EXCEPT</code> diffs. All diffs = 0 → identical results.
          </li>
        </ol>

        <table>
          <thead>
            <tr>
              <th>Approach</th>
              <th>Tool</th>
              <th>Key trade-off</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["Notebook (_nb)", "Workflows", "Most control, schedule it yourself"],
              ["dbt (canonical)", "dbt + Job", "Best portability + docs/tests"],
              ["SDP/Lakeflow (_sdp)", "Declarative", "Managed quality, least code to operate"],
            ].map(([approach, tool, tradeoff]) => (
              <tr key={approach}>
                <td>{approach}</td>
                <td>{tool}</td>
                <td>{tradeoff}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p style={{ marginTop: 8 }}>
          Each layer is a <strong>Delta Lake</strong> table — ACID transactions, time travel (
          <code>VERSION AS OF N</code>), and lineage tracked automatically in Unity Catalog.
        </p>
      </TutorialGuide>
    </div>
  );
}
