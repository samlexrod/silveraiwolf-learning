-- gold: AR aging per contract (overdue / open / paid / total billed) — the collections view.
{{ config(schema='gold', tags=['medallion'], materialized='table') }}
select
    contract_id,
    sum(case when status = 'overdue' then amount else 0 end) as overdue_amount,
    sum(case when status = 'open'    then amount else 0 end) as open_amount,
    sum(case when status = 'paid'    then amount else 0 end) as paid_amount,
    sum(amount)                                              as total_billed
from {{ ref('silver_invoices') }}
group by contract_id
