import { gql } from "@apollo/client";
import { useSubscription, useMutation } from "@apollo/client/react";
import { useEffect, useState } from "react";
import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

const ROW_CHANGED = gql`
  subscription RowChanged {
    rowChanged {
      table
      op
      ts
      row
    }
  }
`;

const SIMULATE = gql`
  mutation Simulate {
    simulateChange
  }
`;

type Change = { table: string; op: string; ts: number; row: Record<string, unknown> };
type SubResult = { rowChanged: Change };

export default function LiveView() {
  const { data, error } = useSubscription<SubResult>(ROW_CHANGED);
  const [feed, setFeed] = useState<Change[]>([]);
  const [simulate, { loading: simulating }] = useMutation(SIMULATE);

  const rc = data?.rowChanged;
  useEffect(() => {
    if (rc) setFeed((f) => [rc, ...f].slice(0, 50));
  }, [rc]);

  return (
    <div className="stack">
      <div className="live-head">
        <span className="dot" /> Listening on <code>silverline_changes</code> (LISTEN/NOTIFY)
        <button className="sim" onClick={() => simulate()} disabled={simulating}>
          {simulating ? "Simulating…" : "⚡ Simulate a change"}
        </button>
      </div>
      {error && <p className="err">Subscription error: {error.message}</p>}
      <Callout icon="⚡">
        <p>
          <strong>Postgres LISTEN/NOTIFY</strong> is a built-in pub-sub channel. Three database triggers on{" "}
          <code>customers</code>, <code>contracts</code>, and <code>invoices</code> call{" "}
          <code>pg_notify('silverline_changes', …)</code> on every INSERT, UPDATE, or DELETE. The server
          holds a dedicated connection that called <code>LISTEN silverline_changes</code> at startup — so
          changes arrive in microseconds with no polling.
        </p>
        <p>
          Those events are forwarded to the browser as a <strong>GraphQL subscription over WebSocket</strong>,
          which is why they appear here instantly. Hit <strong>Simulate a change</strong> to watch an INSERT →
          UPDATE → DELETE sequence land in real time.
        </p>
      </Callout>

      <TutorialGuide title="What you're seeing — stage 09 (Refresh)">
        <p>
          <strong>Stage 09</strong> of the tutorial applied a deterministic change-set to the Lakebase
          source, then re-ingested the changed tables into bronze Delta and re-ran the dbt medallion
          pipeline to prove the change propagated all the way to gold. This view shows the real-time
          half of that story — the moment a row changes in Postgres, you see it here.
        </p>
        <p>How the pipeline works end to end:</p>
        <ol>
          <li>
            A database trigger on <code>customers</code>, <code>contracts</code>, or{" "}
            <code>invoices</code> fires on every INSERT / UPDATE / DELETE and calls{" "}
            <code>pg_notify('silverline_changes', payload_json)</code>.
          </li>
          <li>
            The server's dedicated Postgres connection (held open via <code>LISTEN silverline_changes</code>)
            receives the event in milliseconds — no polling, no cron.
          </li>
          <li>
            The event is published to a GraphQL PubSub channel and pushed to this browser tab over
            a persistent <strong>WebSocket</strong> (the same connection the GraphQL subscription runs on).
          </li>
          <li>
            In the full tutorial, after changes land you re-run the batch ingest{" "}
            (<code>CREATE OR REPLACE TABLE bronze.* AS SELECT * FROM lakebase…</code>) and dbt to rebuild
            silver and gold — proving end-to-end lineage on a real source edit.
          </li>
        </ol>
        <p style={{ marginTop: 8 }}>
          Click <strong>⚡ Simulate a change</strong> above to INSERT a test invoice, UPDATE its status,
          then DELETE it — watch all three events arrive in order.
        </p>
      </TutorialGuide>

      {feed.length === 0 ? (
        <p className="muted">Waiting for changes…</p>
      ) : (
        <ul className="feed">
          {feed.map((c, i) => (
            <li key={i} className={`evt ${c.op}`}>
              <span className={`tag ${c.op}`}>{c.op}</span>
              <b>{c.table}</b>
              <code>{JSON.stringify(c.row)}</code>
              <time>{new Date(c.ts * 1000).toLocaleTimeString()}</time>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
