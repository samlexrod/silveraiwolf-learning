-- Governed Metric View — one definition of the billing/collections metrics, sliceable by any dimension
-- via MEASURE(). Source = the silver billing fact (silver_invoices, already conformed with contract_type +
-- customer_id), joined to silver_customers for segment/region. Run in the SQL editor (the WITH METRICS
-- YAML is finicky over the CLI).
CREATE OR REPLACE VIEW silverline.gold.portfolio_metrics
WITH METRICS
LANGUAGE YAML
COMMENT 'Governed Silverline Capital billing metrics — single source of truth for billed/overdue, sliceable by any dimension.'
AS $$
version: 0.1
source: silverline.silver.silver_invoices
joins:
  - name: customer
    source: silverline.silver.silver_customers
    'on': source.customer_id = customer.customer_id
dimensions:
  - name: segment
    expr: customer.segment
  - name: region
    expr: customer.region
  - name: credit_rating
    expr: customer.credit_rating
  - name: contract_type
    expr: source.contract_type
  - name: status
    expr: source.status
  - name: invoice_date
    expr: source.invoice_date
measures:
  - name: total_billed
    expr: SUM(amount)
  - name: invoice_count
    expr: COUNT(1)
  - name: overdue_amount
    expr: SUM(CASE WHEN status = 'overdue' THEN amount ELSE 0 END)
  - name: overdue_ratio
    expr: SUM(CASE WHEN status = 'overdue' THEN amount ELSE 0 END) / SUM(amount)
$$;
