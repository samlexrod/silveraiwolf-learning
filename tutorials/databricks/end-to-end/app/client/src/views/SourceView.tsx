import { gql } from "@apollo/client";
import { useQuery, useLazyQuery } from "@apollo/client/react";
import { useState } from "react";
import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

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

      <TutorialGuide title="What stages 04–06 built">
        <p>
          <strong>Stage 04 (Provision)</strong> created a Lakebase Autoscaling project{" "}
          <code>silverline-oltp</code> on PostgreSQL 17 via the CLI. Authentication uses a{" "}
          <em>short-lived OAuth token minted on demand</em> as the Postgres password — nothing static is
          stored or committed.
        </p>
        <p>
          <strong>Stage 05 (Seed)</strong> loaded Silverline Capital's full 9-table OLTP from a notebook
          (deterministic, idempotent, seed=42). Expected counts:{" "}
          <code>customers=60 · vendors=15 · equipment=220 · applications=140 · contracts=85 ·
          contract_assets=180 · payment_schedule=2,904 · invoices=1,452 · payments=1,291</code>.
        </p>
        <p>
          <strong>Stage 06 (Data API)</strong> created a Service Principal and demonstrated querying
          the same tables via the Databricks SQL Statements API — the non-user, app-to-app identity pattern.
        </p>
        <p><strong>The data model (Silverline Capital — equipment lease &amp; loan):</strong></p>
        <pre className="erd">{`customers ── applications ──▶ contracts ──◀ contract_assets ▶── equipment ──▶ vendors
                                   │
                                   ├──◀ payment_schedule
                                   └──◀ invoices ──◀ payments`}</pre>
        <table>
          <thead>
            <tr><th>Table</th><th>Role</th></tr>
          </thead>
          <tbody>
            {[
              ["customers", "The businesses Silverline finances — segment, region, credit rating, revenue"],
              ["vendors", "Equipment suppliers — who provides the financed assets"],
              ["equipment", "Individual assets (make, model, serial, cost, residual value)"],
              ["applications", "Credit pipeline — submitted → approved → declined → booked"],
              ["contracts", "Booked lease/loan deals — type, status (active/delinquent/charged_off/paid_off), APR, term"],
              ["contract_assets", "M:N bridge — which equipment backs which contract"],
              ["payment_schedule", "Amortization plan — principal + interest due per period"],
              ["invoices", "Bills issued for elapsed periods — open / paid / overdue"],
              ["payments", "Cash received against invoices"],
            ].map(([name, role]) => (
              <tr key={name}><td><code>{name}</code></td><td>{role}</td></tr>
            ))}
          </tbody>
        </table>
      </TutorialGuide>

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
