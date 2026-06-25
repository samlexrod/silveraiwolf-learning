import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

export default function DataApiView() {
  return (
    <div className="stack">
      <Callout icon="🌐">
        <p>
          The <strong>Lakebase Data API</strong> exposes your Postgres tables as a REST endpoint
          (PostgREST-compatible) with zero backend code. The business — or an agent — can read
          customers, contracts, and overdue invoices over plain HTTPS.
        </p>
        <p>
          Auth uses <strong>M2M OAuth</strong> (service principal), not your user identity. The SP
          mints a short-lived token against your workspace and passes it as the Postgres password —
          same ephemeral-credential pattern as stage 04, but for non-human callers.
        </p>
      </Callout>

      <TutorialGuide title="What to do in stage 06 — enable the Data API">
        <ol>
          <li>
            <strong>Enable the Data API (UI-only — no CLI toggle exists for this):</strong> In your
            workspace, open <strong>Database</strong> (Lakebase) → click the{" "}
            <code>silverline-oltp</code> project → <strong>Data API</strong> page (under App Backend)
            → click <strong>Enable Data API</strong>.
          </li>
          <li>
            <strong>Create a Service Principal</strong> via the CLI:
            <pre className="erd">{`databricks --profile free service-principals create \\
  --display-name "silverline-data-api" -o json
# note the applicationId

databricks --profile free service-principal-secrets-proxy create <sp-id> -o json
# note the .secret (shown once)`}</pre>
          </li>
          <li>
            <strong>Store the SP credentials</strong> in a Databricks secret scope:
            <pre className="erd">{`databricks --profile free secrets create-scope silverline
databricks --profile free secrets put-secret silverline data_api_sp_client_id \\
  --string-value "<APP_ID>"
databricks --profile free secrets put-secret silverline data_api_sp_secret \\
  --string-value "<SECRET>"`}</pre>
          </li>
          <li>
            <strong>Grant the SP a Postgres role</strong> (run as the database owner in psql or
            psycopg):
            <pre className="erd">{`CREATE EXTENSION IF NOT EXISTS databricks_auth;
SELECT databricks_create_role('<APP_ID>', 'SERVICE_PRINCIPAL');
GRANT "<APP_ID>" TO authenticator;
GRANT USAGE ON SCHEMA public TO "<APP_ID>";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "<APP_ID>";`}</pre>
          </li>
          <li>
            <strong>Test a REST query:</strong> Run notebook{" "}
            <code>SilverAIWolf/06-data-api/06.1_data_api_demo</code> — it reads SP creds from the
            secret scope, mints an M2M token, and queries customers, overdue invoices, and active
            contracts via HTTPS. You should see JSON rows.
          </li>
        </ol>
      </TutorialGuide>
    </div>
  );
}
