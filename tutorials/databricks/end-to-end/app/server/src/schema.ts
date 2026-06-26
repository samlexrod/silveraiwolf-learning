import { GraphQLJSON } from "graphql-scalars";
import { pubsub, ROW_CHANGED } from "./pubsub.js";
import { requirePool, configure, status } from "./session.js";
import { verifyStage } from "./verify.js";
import { loadTutorial, defaultTutorial } from "./tutorial-loader.js";

// The Silverline OLTP model — also the allowlist that guards `tableRows` against injection.
const TABLES = [
  "customers",
  "vendors",
  "equipment",
  "applications",
  "contracts",
  "contract_assets",
  "payment_schedule",
  "invoices",
  "payments",
] as const;

export const typeDefs = /* GraphQL */ `
  scalar JSON

  type ConnectionStatus {
    connected: Boolean!
    user: String
    workspace: String
    warehouseId: String
    lakebaseHost: String
  }

  type Customer {
    customer_id: Int!
    legal_name: String
    segment: String
    region: String
    credit_rating: String
    annual_revenue: Float
  }

  type Contract {
    contract_id: Int!
    customer_id: Int
    contract_type: String
    status: String
    principal: Float
    apr: Float
  }

  type Counts {
    customers: Int!
    contracts: Int!
    invoices: Int!
  }

  type TableInfo {
    name: String!
    count: Int!
  }

  type RowChange {
    table: String!
    op: String!
    ts: Float!
    row: JSON
  }

  type StageCheck {
    name: String!
    passed: Boolean!
    detail: String!
  }

  type VerifyResult {
    passed: Boolean!
    checks: [StageCheck!]!
  }

  type CalloutConfig {
    icon: String!
    body: String!
  }

  type SectionConfig {
    heading: String!
    body: String!
  }

  type StageContent {
    callout: CalloutConfig
    sections: [SectionConfig!]!
  }

  type StageConfig {
    id: String!
    phase: String!
    label: String!
    icon: String!
    title: String!
    "special = 'connect' means render the built-in connect form, not markdown content"
    special: String
    hasVerify: Boolean!
    widgets: [String!]!
    content: StageContent
  }

  type TutorialConfigResult {
    id: String!
    name: String!
    description: String
    stages: [StageConfig!]!
  }

  type Query {
    connectionStatus: ConnectionStatus!
    counts: Counts!
    customers(limit: Int = 25): [Customer!]!
    contracts(limit: Int = 25): [Contract!]!
    tables: [TableInfo!]!
    tableRows(name: String!, limit: Int = 12): [JSON!]!
    verifyStage(id: String!): VerifyResult!
    "Load the tutorial config — stages metadata + markdown content (verify rules stay server-side)"
    tutorialConfig(id: String): TutorialConfigResult!
  }

  type Subscription {
    rowChanged: RowChange!
  }

  type Mutation {
    "Connect the app to a Databricks workspace with a PAT — discovers the warehouse + Lakebase endpoint."
    configure(workspaceUrl: String!, token: String!): ConnectionStatus!
    "Apply a throwaway INSERT -> UPDATE -> DELETE on a temp invoice; fires the live feed."
    simulateChange: String!
  }
`;

export const resolvers = {
  JSON: GraphQLJSON,
  Query: {
    connectionStatus: () => status(),
    counts: async () => {
      const { rows } = await requirePool().query(
        `SELECT (SELECT count(*) FROM customers)::int AS customers,
                (SELECT count(*) FROM contracts)::int AS contracts,
                (SELECT count(*) FROM invoices)::int  AS invoices`,
      );
      return rows[0];
    },
    customers: async (_: unknown, { limit }: { limit: number }) =>
      (
        await requirePool().query(
          `SELECT customer_id, legal_name, segment, region, credit_rating, annual_revenue
           FROM customers ORDER BY customer_id LIMIT $1`,
          [limit],
        )
      ).rows,
    contracts: async (_: unknown, { limit }: { limit: number }) =>
      (
        await requirePool().query(
          `SELECT contract_id, customer_id, contract_type, status, principal, apr
           FROM contracts ORDER BY contract_id LIMIT $1`,
          [limit],
        )
      ).rows,
    tables: async () =>
      Promise.all(
        TABLES.map(async (name) => ({
          name,
          count: (await requirePool().query(`SELECT count(*)::int AS c FROM ${name}`)).rows[0].c as number,
        })),
      ),
    tableRows: async (_: unknown, { name, limit }: { name: string; limit: number }) => {
      if (!TABLES.includes(name as (typeof TABLES)[number])) throw new Error(`unknown table: ${name}`);
      return (await requirePool().query(`SELECT * FROM ${name} ORDER BY 1 LIMIT $1`, [limit])).rows;
    },
    verifyStage: (_: unknown, { id }: { id: string }) => verifyStage(id),
    tutorialConfig: (_: unknown, { id }: { id?: string }) => {
      const config = id ? loadTutorial(id) : defaultTutorial();
      return {
        id: config.id,
        name: config.name,
        description: config.description ?? null,
        stages: config.stages.map((s) => ({
          id: s.id,
          phase: s.phase,
          label: s.label,
          icon: s.icon,
          title: s.title,
          special: s.special ?? null,
          hasVerify: Boolean(s.verify),
          widgets: s.widgets ?? [],
          content: s.content
            ? {
                callout: s.content.callout ?? null,
                sections: s.content.sections,
              }
            : null,
        })),
      };
    },
  },
  Subscription: {
    rowChanged: {
      subscribe: () => pubsub.asyncIterator([ROW_CHANGED]),
    },
  },
  Mutation: {
    configure: (_: unknown, { workspaceUrl, token }: { workspaceUrl: string; token: string }) =>
      configure(workspaceUrl, token),
    simulateChange: async () => {
      const id = 9_000_000 + (Date.now() % 1_000_000);
      const amt = Math.round(1000 + Math.random() * 9000);
      const pool = requirePool();
      await pool.query(
        `INSERT INTO invoices (invoice_id, contract_id, schedule_id, invoice_date, due_date, amount, status)
         VALUES ($1, 1, NULL, current_date, current_date, $2, 'open')`,
        [id, amt],
      );
      await pool.query(`UPDATE invoices SET status = 'overdue', amount = $2 WHERE invoice_id = $1`, [id, amt + 500]);
      await pool.query(`DELETE FROM invoices WHERE invoice_id = $1`, [id]);
      return `Simulated INSERT → UPDATE → DELETE on invoice ${id}`;
    },
  },
};
