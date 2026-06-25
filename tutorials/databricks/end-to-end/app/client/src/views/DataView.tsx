import { gql } from "@apollo/client";
import { useQuery } from "@apollo/client/react";

const GET_DATA = gql`
  query GetData {
    counts {
      customers
      contracts
      invoices
    }
    customers(limit: 10) {
      customer_id
      legal_name
      segment
      region
      credit_rating
    }
    contracts(limit: 10) {
      contract_id
      contract_type
      status
      principal
      apr
    }
  }
`;

type Customer = {
  customer_id: number;
  legal_name: string;
  segment: string;
  region: string;
  credit_rating: string;
};
type Contract = {
  contract_id: number;
  contract_type: string;
  status: string;
  principal: number;
  apr: number;
};
type DataResult = {
  counts: { customers: number; contracts: number; invoices: number };
  customers: Customer[];
  contracts: Contract[];
};

const money = (n: number) =>
  n?.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export default function DataView() {
  const { data, loading, error, refetch } = useQuery<DataResult>(GET_DATA);

  if (loading) return <p className="muted">Loading from Lakebase…</p>;
  if (error) return <p className="err">Error: {error.message}</p>;
  if (!data) return null;

  return (
    <div className="stack">
      <div className="counts">
        <div className="stat"><b>{data.counts.customers}</b><span>customers</span></div>
        <div className="stat"><b>{data.counts.contracts}</b><span>contracts</span></div>
        <div className="stat"><b>{data.counts.invoices}</b><span>invoices</span></div>
        <button onClick={() => refetch()}>↻ Refetch</button>
      </div>

      <h3>Customers</h3>
      <table>
        <thead><tr><th>id</th><th>legal name</th><th>segment</th><th>region</th><th>rating</th></tr></thead>
        <tbody>
          {data.customers.map((c) => (
            <tr key={c.customer_id}>
              <td>{c.customer_id}</td><td>{c.legal_name}</td><td>{c.segment}</td>
              <td>{c.region}</td><td>{c.credit_rating}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Contracts</h3>
      <table>
        <thead><tr><th>id</th><th>type</th><th>status</th><th>principal</th><th>apr</th></tr></thead>
        <tbody>
          {data.contracts.map((c) => (
            <tr key={c.contract_id}>
              <td>{c.contract_id}</td><td>{c.contract_type}</td>
              <td><span className={`pill ${c.status}`}>{c.status}</span></td>
              <td>{money(c.principal)}</td><td>{(c.apr * 100).toFixed(2)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
