import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

export default function ProjectView() {
  return (
    <div className="stack">
      <Callout icon="🛠️">
        <p>
          <strong>Local tooling</strong> is the "project" layer — <code>mise</code> (task runner),{" "}
          <code>uv</code> (Python package manager), and <code>dbt</code> (SQL transformations). Together
          they give you a reproducible, one-command dev environment for the whole tutorial.
        </p>
        <p>
          dbt uses <strong>OAuth</strong> to talk to the Starter Warehouse — no PAT or password stored
          in any config file. The <code>free</code> profile you authenticated in stage 01 is the only
          credential dbt needs.
        </p>
      </Callout>

      <TutorialGuide title="What to do in stage 03 — set up local tooling">
        <ol>
          <li>
            In the repo at <code>tutorials/databricks/end-to-end/</code>, copy{" "}
            <code>.env.sample</code> to <code>.env</code> and fill in your workspace URL and Starter
            Warehouse ID from stage 01.
          </li>
          <li>
            Run <code>mise run setup</code> — installs <code>dbt-databricks</code>,{" "}
            <code>databricks-sdk</code>, and <code>databricks-sql-connector</code> via uv into a
            local virtual environment.
          </li>
          <li>
            Run <code>mise run dbt:debug</code> — proves dbt can reach the warehouse and{" "}
            <code>silverline</code> catalog via OAuth.
            <br />
            Expect: <strong>All checks passed!</strong>
          </li>
          <li>
            Smoke test:
            <pre className="erd">{`mise run sql 'SELECT current_catalog(), current_user()'`}</pre>
            Expect: <code>silverline | &lt;your email&gt;</code>
          </li>
          <li>
            If <code>dbt debug</code> fails on auth, re-run{" "}
            <code>databricks auth login --profile free</code> — the cached OAuth token may have expired
            (they last ~50 minutes).
          </li>
        </ol>
      </TutorialGuide>
    </div>
  );
}
