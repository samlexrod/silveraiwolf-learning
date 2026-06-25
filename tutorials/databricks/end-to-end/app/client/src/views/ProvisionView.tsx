import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

export default function ProvisionView() {
  return (
    <div className="stack">
      <Callout icon="🐘">
        <p>
          <strong>Lakebase</strong> is Databricks' serverless Postgres 17. An{" "}
          <strong>Autoscaling project</strong> auto-scales and idles to ~0 quota when unused — you pay
          (in quota) only for active connections. Auth uses <strong>short-lived OAuth tokens</strong>{" "}
          minted on demand as the Postgres password — nothing static is stored or committed.
        </p>
        <p>
          <strong>PG17 matters</strong> because Lakebase CDF (native CDC) requires it. Use{" "}
          <code>postgres create-project</code>, not <code>database create-database-instance</code> — the
          latter only gives PG16.
        </p>
      </Callout>

      <TutorialGuide title="What to do in stage 04 — provision the Lakebase project">
        <ol>
          <li>
            Create the PG17 Autoscaling project via the Databricks CLI:
            <pre className="erd">{`databricks --profile free postgres create-project silverline-oltp \\
  --json '{"spec":{"pg_version":17}}' --timeout 15m -o json`}</pre>
            Expect <code>pg_version: 17</code> in the output. This takes 1–2 minutes.
          </li>
          <li>
            Capture the endpoint host:
            <pre className="erd">{`EP=projects/silverline-oltp/branches/production/endpoints/primary
databricks --profile free postgres get-endpoint "$EP" -o json`}</pre>
            Copy the <code>status.hosts.host</code> value into your <code>.env</code> as{" "}
            <code>LAKEBASE_HOST</code>.
          </li>
          <li>
            Mint a credential and verify connectivity:
            <pre className="erd">{`TOKEN=$(databricks --profile free postgres generate-database-credential "$EP" \\
  -o json | jq -r '.token')
# then connect with psql and run:
SELECT version();
# expect: PostgreSQL 17.x over SSL`}</pre>
          </li>
          <li>
            Add to <code>.env</code>:
            <pre className="erd">{`LAKEBASE_DB=databricks_postgres
LAKEBASE_USER=<your-databricks-email>`}</pre>
          </li>
        </ol>
      </TutorialGuide>
    </div>
  );
}
