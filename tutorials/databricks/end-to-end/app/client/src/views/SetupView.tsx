import { gql } from "@apollo/client";
import { useMutation } from "@apollo/client/react";
import { useState } from "react";
import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

const CONFIGURE = gql`
  mutation Configure($workspaceUrl: String!, $token: String!) {
    configure(workspaceUrl: $workspaceUrl, token: $token) {
      connected
      user
      workspace
      warehouseId
      lakebaseHost
    }
  }
`;

const URL_KEY = "silverline.workspaceUrl";
const PAT_KEY = "silverline.pat";

type Conn = { connected: boolean; user?: string; workspace?: string; warehouseId?: string; lakebaseHost?: string };

export default function SetupView({
  conn,
  onRefresh,
  onContinue,
}: {
  conn?: Conn;
  onRefresh: () => void;
  onContinue: () => void;
}) {
  const [url, setUrl] = useState(() => localStorage.getItem(URL_KEY) ?? conn?.workspace ?? "");
  const [token, setToken] = useState(() => localStorage.getItem(PAT_KEY) ?? "");
  const [autoErr, setAutoErr] = useState("");
  const [configure, { loading, error }] = useMutation(CONFIGURE);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAutoErr("");
    const res = await configure({ variables: { workspaceUrl: url, token } });
    if ((res.data as { configure: Conn } | null | undefined)?.configure?.connected) {
      localStorage.setItem(URL_KEY, url);
      localStorage.setItem(PAT_KEY, token);
      setToken("");
      onRefresh();
    }
  };

  const disconnect = () => {
    localStorage.removeItem(URL_KEY);
    localStorage.removeItem(PAT_KEY);
    setUrl("");
    setToken("");
  };

  if (conn?.connected) {
    return (
      <div className="stack">
        <div className="card good">
          <span className="status" />
          <div>
            <span className="muted">Connected</span>
            <b>{conn.user}</b>
          </div>
        </div>
        <table>
          <tbody>
            <tr><th>Workspace</th><td>{conn.workspace}</td></tr>
            <tr><th>Warehouse</th><td>{conn.warehouseId}</td></tr>
            <tr><th>Lakebase host</th><td>{conn.lakebaseHost}</td></tr>
          </tbody>
        </table>
        <p className="muted">Workspace verified — click Continue to start the tutorial.</p>
        <button className="form-continue" onClick={onContinue}>
          Continue → Landing Zone
        </button>
        <p className="muted" style={{ fontSize: 12 }}>
          Your credentials are saved in this browser and will reconnect automatically on restart.{" "}
          <button className="link" style={{ fontSize: 12 }} onClick={disconnect}>
            Clear saved credentials
          </button>
        </p>
      </div>
    );
  }

  return (
    <div className="stack">
      {autoErr && <p className="err">{autoErr}</p>}
      <Callout icon="🔑">
        <p>
          <strong>Personal Access Tokens (PATs)</strong> are how external tools authenticate to Databricks —
          the same mechanism the CLI, dbt, and any REST caller use. Once you paste yours, this app calls
          the Databricks REST API to confirm your identity, then <em>auto-discovers</em> your serverless
          warehouse and Lakebase endpoint — no copy-pasting IDs.
        </p>
        <p>
          Your workspace URL and token are saved in <strong>this browser's localStorage</strong> so the app
          reconnects automatically when the server restarts — you won't need to re-enter them. They are
          never sent anywhere other than your own Databricks workspace.
        </p>
      </Callout>
      <TutorialGuide title="How to get your credentials">
        <ol>
          <li>
            Sign in to your <strong>Databricks Free Edition</strong> workspace (
            <code>https://dbc-xxxxxxxx.cloud.databricks.com</code>). Copy that URL from the browser
            address bar — you'll need it below.
          </li>
          <li>
            Click your profile icon (top-right of the workspace) → <strong>Settings</strong>.
          </li>
          <li>
            Open <strong>Developer</strong> → <strong>Access tokens</strong> → click{" "}
            <strong>Generate new token</strong>. Give it a name (e.g. <em>Silverline app</em>) and an
            expiry of your choice.
          </li>
          <li>
            Copy the token immediately — it starts with <code>dapi…</code> and will not be shown again.
          </li>
          <li>
            Paste the workspace URL and the token into the form below and click <strong>Connect</strong>.
            The app will verify your identity and automatically find your Starter Warehouse and Lakebase
            endpoint — no IDs to copy.
          </li>
        </ol>
        <p style={{ marginTop: 10 }}>
          <strong>No workspace yet?</strong> Go to{" "}
          <code>databricks.com/learn/free-edition</code> → <em>Get started</em> and sign up with
          Google, Microsoft, or email OTP. It's $0.
        </p>
      </TutorialGuide>
      <form className="form" onSubmit={submit}>
        <label>
          Workspace URL
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://dbc-xxxxxxxx.cloud.databricks.com"
            required
          />
        </label>
        <label>
          Personal Access Token
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="dapi…"
            required
          />
          <small className="muted">User Settings → Developer → Access tokens → Generate new token</small>
        </label>
        <button type="submit" disabled={loading || !url || !token}>
          {loading ? "Connecting…" : "Connect"}
        </button>
        {error && <p className="err">{error.message}</p>}
      </form>
    </div>
  );
}
