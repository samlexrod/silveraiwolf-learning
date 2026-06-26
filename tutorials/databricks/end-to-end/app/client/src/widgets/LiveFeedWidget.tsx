import { gql } from "@apollo/client";
import { useSubscription, useMutation } from "@apollo/client/react";
import { useEffect, useState } from "react";

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

export default function LiveFeedWidget() {
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
