import Callout from "../Callout";
import TutorialGuide from "../TutorialGuide";

export default function BusinessLayerView() {
  return (
    <div className="stack">
      <Callout icon="📋">
        <p>
          The gold tables exist but aren't documented. <strong>COMMENTs on tables and columns</strong>{" "}
          are what Genie and AI assistants read to understand the schema — "billed" maps to{" "}
          <code>total_billed</code>, "overdue" maps to <code>overdue_amount</code>. An undocumented
          gold layer means worse Genie answers.
        </p>
        <p>
          A <code>customer_360</code> view rolls contract aging up to the customer grain — one row
          per customer with their overdue balance and total billed. This is what a collections team
          or a Genie query would naturally ask for.
        </p>
      </Callout>

      <TutorialGuide title="What to do in stage 10 — document the business layer">
        <ol>
          <li>
            Add table and column COMMENTs to the gold tables (paste into SQL editor → Run):
            <pre className="erd">{`COMMENT ON TABLE silverline.gold.gold_segment_portfolio IS
  'Portfolio by customer segment — contract counts, principal, APR, residual.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN segment
  COMMENT 'Customer business segment.';
ALTER TABLE silverline.gold.gold_segment_portfolio ALTER COLUMN total_principal
  COMMENT 'Sum of contract principal financed for the segment.';
-- (same pattern for each column on both tables)`}</pre>
          </li>
          <li>
            Add COMMENTs to <code>gold_contract_aging</code> columns:{" "}
            <code>contract_id</code>, <code>overdue_amount</code>, <code>open_amount</code>,{" "}
            <code>paid_amount</code>, <code>total_billed</code>.
          </li>
          <li>
            Create the <code>customer_360</code> view (customer profile + contract aging, rolled to
            customer grain):
            <pre className="erd">{`CREATE OR REPLACE VIEW silverline.gold.customer_360
COMMENT 'Per-customer collections view: profile + contract aging.'
AS
SELECT c.customer_id, c.legal_name, c.segment, c.region, c.credit_rating,
       sum(a.overdue_amount) AS overdue_amount,
       sum(a.total_billed)   AS total_billed
FROM silverline.gold.gold_contract_aging a
JOIN silverline.silver.silver_contracts ct ON ct.contract_id = a.contract_id
JOIN silverline.silver.silver_customers c  ON c.customer_id  = ct.customer_id
GROUP BY c.customer_id, c.legal_name, c.segment, c.region, c.credit_rating;`}</pre>
          </li>
          <li>
            Verify: run{" "}
            <code>DESCRIBE TABLE EXTENDED silverline.gold.gold_segment_portfolio</code> and check
            that comments appear. Browse the table in <strong>Catalog Explorer</strong> to see them
            in the UI.
          </li>
        </ol>
      </TutorialGuide>
    </div>
  );
}
