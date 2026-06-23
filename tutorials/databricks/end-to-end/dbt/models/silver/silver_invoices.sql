-- silver: current-state invoices from bronze, conformed with their contract (carries customer_id +
-- contract_type so the gold + metric layer can slice without re-joining contracts).
{{ config(schema='silver', tags=['medallion'], materialized='table') }}
select
    i.invoice_id,
    i.contract_id,
    ct.customer_id,
    ct.contract_type,
    cast(i.invoice_date as date) as invoice_date,
    cast(i.due_date as date)     as due_date,
    cast(i.amount as decimal(12, 2)) as amount,
    i.status
from silverline.bronze.invoices i
join {{ ref('silver_contracts') }} ct on ct.contract_id = i.contract_id
where i.invoice_id is not null and i.contract_id is not null
