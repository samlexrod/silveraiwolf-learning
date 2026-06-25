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

export default function SeedView() {
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
      <Callout icon="🌱">
        <p>
          The seed stage loads <strong>Silverline Capital's full 9-table operational model</strong> into
          Lakebase. It uses a deterministic script (<code>MOCK_SEED=42</code>) so results are identical
          every run — safe to re-run if anything goes wrong.
        </p>
        <p>
          The data represents a fictional equipment lease &amp; loan finance company's full lifecycle:{" "}
          customers → applications → contracts → equipment → billing → payments.
        </p>
      </Callout>

      <TutorialGuide title="What to do in stage 05 — seed Lakebase">
        <ol>
          <li>
            In your workspace, open{" "}
            <strong>
              <code>SilverAIWolf/05-seed/05.1_seed_oltp</code>
            </strong>{" "}
            (serverless) and click <strong>Run All</strong>. It mints a Lakebase credential via the SDK
            and seeds all 9 tables.
            <br />
            Expected counts:{" "}
            <code>
              customers=60 vendors=15 equipment=220 applications=140 contracts=85 contract_assets=180
              payment_schedule=2904 invoices=1452 payments=1291
            </code>
          </li>
          <li>
            Run{" "}
            <strong>
              <code>SilverAIWolf/05-seed/05.2_data_model</code>
            </strong>{" "}
            (serverless, Run All) — shows the ERD, counts, and a segment analysis using psycopg.
          </li>
          <li>
            Run{" "}
            <strong>
              <code>SilverAIWolf/05-seed/05.3_documents</code>
            </strong>{" "}
            (serverless, Run All) — generates contract PDFs and credit memos and writes them to{" "}
            <code>/Volumes/silverline/bronze/files/</code>. Verify in Catalog Explorer.
          </li>
          <li>Once seeded, click any table tile below to query live rows from Lakebase.</li>
        </ol>

        <p>
          <strong>Entity-relationship overview:</strong>
        </p>
        <pre className="erd">{`customers ── applications ──▶ contracts ──◀ contract_assets ▶── equipment ──▶ vendors
                                   │
                                   ├──◀ payment_schedule
                                   └──◀ invoices ──◀ payments`}</pre>

        <table>
          <thead>
            <tr>
              <th>Table</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["customers", "Businesses Silverline finances — segment, region, credit rating"],
              ["vendors", "Equipment suppliers"],
              ["equipment", "Individual financed assets (make, model, serial, cost)"],
              ["applications", "Credit pipeline — submitted → approved → booked"],
              ["contracts", "Booked lease/loan deals — type, status, APR, term"],
              ["contract_assets", "M:N bridge — which equipment backs which contract"],
              ["payment_schedule", "Amortization plan per period"],
              ["invoices", "Bills issued — open / paid / overdue"],
              ["payments", "Cash received against invoices"],
            ].map(([name, role]) => (
              <tr key={name}>
                <td>
                  <code>{name}</code>
                </td>
                <td>{role}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TutorialGuide>

      <div className="tablegrid">
        {loading ? (
          <p className="muted">Loading…</p>
        ) : (
          data?.tables.map((t) => (
            <button
              key={t.name}
              className={`tcard ${sel === t.name ? "on" : ""}`}
              onClick={() => pick(t.name)}
            >
              <b>{t.count.toLocaleString()}</b>
              <span>{t.name}</span>
            </button>
          ))
        )}
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
                <thead>
                  <tr>
                    {cols.map((c) => (
                      <th key={c}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i}>
                      {cols.map((c) => (
                        <td key={c}>{fmt(r[c])}</td>
                      ))}
                    </tr>
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
