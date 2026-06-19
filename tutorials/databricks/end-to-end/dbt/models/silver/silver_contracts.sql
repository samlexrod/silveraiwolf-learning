-- silver: current-state lease/loan contracts from bronze (typed; latest per contract_id).
{{ config(schema='silver', tags=['medallion'], materialized='table') }}
select
    contract_id,
    customer_id,
    contract_type,
    status,
    cast(principal as decimal(14, 2))      as principal,
    cast(apr as decimal(6, 4))             as apr,
    term_months,
    cast(start_date as date)               as start_date,
    cast(end_date as date)                 as end_date,
    cast(residual_value as decimal(14, 2)) as residual_value
from silverline.bronze.contracts
qualify row_number() over (partition by contract_id order by updated_at desc) = 1
