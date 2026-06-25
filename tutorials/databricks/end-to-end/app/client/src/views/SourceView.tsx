import { gql } from "@apollo/client";
import { useQuery, useLazyQuery } from "@apollo/client/react";
import { useState } from "react";
import Callout from "../Callout";

const TABLES = gql`
  query Tables {
    tables {
      name
      count
    }
  }
`;

const ROWS = gql`
  query Rows($name: String!) {
    tableRows(name: $name, limit: 12)
  }
`;

type Row = Record<string, unknown>;
const fmt = (v: unknown) =>
  v === null ? "∅" : typeof v === "object" ? JSON.stringify(v) : String(v);

export default function SourceView() {
  const { data, loading } = useQuery<{ tables: { name: string; count: number }[] }>(TABLES);
  const [sel, setSel] = useState<string | null>(null);
  const [loadRows, rowsRes] = useLazyQuery<{ tableRows: Row[] }>(ROWS);

  const pick = (name: string) => {
    setSel(name);
    loadRows({ variables: { name } });
  };

  const rows = rowsRes.data?.tableRows ?? [];
  const cols = rows[0] ? Object.keys(rows[0]) : [];

  return (
    <div className="stack">
      <Callout icon="🗃️">
        <p>
          <strong>Lakebase is Databricks' serverless Postgres 17</strong> — your OLTP (Online Transaction
          Processing) source. OLTP means it's built for fast, row-level reads and writes: the business
          records customers, creates contracts, logs payments here in real time.
        </p>
        <p>
          These 9 tables are Silverline Capital's operational data model. They're the raw source of truth
          that will be <em>ingested into the Lakehouse</em> and transformed bronze → silver → gold.
          Click any table to query live rows directly from Postgres via the server's connection pool.
        </p>
      </Callout>

      <div className="tablegrid">
        {loading
          ? <p className="muted">Loading…</p>
          : data?.tables.map((t) => (
              <button key={t.name} className={`tcard ${sel === t.name ? "on" : ""}`} onClick={() => pick(t.name)}>
                <b>{t.count.toLocaleString()}</b>
                <span>{t.name}</span>
              </button>
            ))}
      </div>

      {sel && (
        <div className="stack">
          <h3>{sel}</h3>
          {rowsRes.loading ? (
            <p className="muted">Loading rows…</p>
          ) : rows.length === 0 ? (
            <p className="muted">No rows.</p>
          ) : (
            <div className="scroll">
              <table>
                <thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i}>{cols.map((c) => <td key={c}>{fmt(r[c])}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
