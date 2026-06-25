import { gql } from "@apollo/client";
import { useMutation } from "@apollo/client/react";
import { useState } from "react";
import Callout from "../Callout";

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

type Conn = { connected: boolean; user?: string; workspace?: string; warehouseId?: string; lakebaseHost?: string };

export default function SetupView({ conn, onConnected }: { conn?: Conn; onConnected: () => void }) {
  const [url, setUrl] = useState(conn?.workspace ?? "");
  const [token, setToken] = useState("");
  const [configure, { loading, error }] = useMutation(CONFIGURE);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await configure({ variables: { workspaceUrl: url, token } });
    if ((res.data as { configure: Conn } | null | undefined)?.configure?.connected) {
      setToken("");
      onConnected();
    }
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
        <p className="muted">All set — use the steps on the left. They unlock in order.</p>
      </div>
    );
  }

  return (
    <div className="stack">
      <Callout icon="🔑">
        <p>
          <strong>Personal Access Tokens (PATs)</strong> are how external tools authenticate to Databricks —
          the same mechanism the CLI, dbt, and any REST caller use. Once you paste yours, this app calls
          the Databricks REST API to confirm your identity, then <em>auto-discovers</em> your serverless
          warehouse and Lakebase endpoint — no copy-pasting IDs.
        </p>
        <p>Your token is held in the server process only. It is never written to disk or sent anywhere else.</p>
      </Callout>
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
