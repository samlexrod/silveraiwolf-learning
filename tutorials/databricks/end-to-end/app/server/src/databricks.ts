// Thin Databricks REST helpers — everything authenticated with the user's PAT.
async function api<T = any>(host: string, token: string, path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${host}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) throw new Error(`${path} → ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.json() as Promise<T>;
}

export const whoami = async (host: string, token: string): Promise<string> =>
  (await api(host, token, "/api/2.0/preview/scim/v2/Me")).userName;

export const listWarehouses = async (host: string, token: string): Promise<any[]> =>
  (await api(host, token, "/api/2.0/sql/warehouses")).warehouses ?? [];

export const listProjects = async (host: string, token: string): Promise<any[]> =>
  (await api(host, token, "/api/2.0/postgres/projects")).projects ?? [];

export const endpointHost = async (host: string, token: string, ep: string): Promise<string> =>
  (await api(host, token, `/api/2.0/postgres/${ep}`)).status?.hosts?.host;

// Mint the short-lived JWT Lakebase Postgres accepts as the password.
export const mintPgCredential = async (host: string, token: string, ep: string): Promise<string> =>
  (
    await api(host, token, "/api/2.0/postgres/credentials", {
      method: "POST",
      body: JSON.stringify({ endpoint: ep }),
    })
  ).token;

export const listDashboards = async (host: string, token: string): Promise<any[]> =>
  (await api(host, token, "/api/2.0/lakeview/dashboards")).dashboards ?? [];

export const listGenieSpaces = async (host: string, token: string): Promise<any[]> =>
  (await api(host, token, "/api/2.0/genie/spaces")).spaces ?? [];

// Run one SQL statement on a serverless warehouse (Delta — bronze/silver/gold, metric views).
export const runSql = async (host: string, token: string, warehouseId: string, statement: string) =>
  api(host, token, "/api/2.0/sql/statements", {
    method: "POST",
    body: JSON.stringify({ warehouse_id: warehouseId, wait_timeout: "50s", statement }),
  });
