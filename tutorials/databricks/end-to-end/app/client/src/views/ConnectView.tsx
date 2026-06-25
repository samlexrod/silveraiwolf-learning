import { gql } from "@apollo/client";
import { useQuery } from "@apollo/client/react";

const HEALTH = gql`
  query Health {
    health
    counts {
      customers
      contracts
      invoices
    }
  }
`;

type R = { health: string; counts: { customers: number; contracts: number; invoices: number } };

export default function ConnectView() {
  const { data, loading, error } = useQuery<R>(HEALTH, { pollInterval: 5000 });
  const ok = !loading && !error && data?.health === "ok";

  return (
    <div className="stack">
      <p className="muted">
        Stage 1 of the tutorial: prove the platform is reachable. This panel polls the GraphQL server
        (which holds a live OAuth connection to Lakebase) every 5 seconds.
      </p>
      <div className="cards">
        <div className={`card ${loading ? "" : error ? "bad" : "good"}`}>
          <span className="status" />
          <div><span className="muted">GraphQL server</span><b>{loading ? "checking…" : error ? "down" : "connected"}</b></div>
        </div>
        <div className={`card ${ok ? "good" : "bad"}`}>
          <span className="status" />
          <div><span className="muted">Lakebase · Postgres 17</span><b>{ok ? "reachable" : "—"}</b></div>
        </div>
      </div>
      {error && <p className="err">{error.message}</p>}
      {ok && (
        <div className="counts">
          <div className="stat"><b>{data!.counts.customers}</b><span>customers</span></div>
          <div className="stat"><b>{data!.counts.contracts}</b><span>contracts</span></div>
          <div className="stat"><b>{data!.counts.invoices}</b><span>invoices</span></div>
        </div>
      )}
    </div>
  );
}
