-- gold: financing portfolio by customer segment (the business layer).
{{ config(schema='gold', tags=['medallion'], materialized='table') }}
select
    c.segment,
    count(*)                                                   as contract_count,
    sum(case when ct.status = 'active' then 1 else 0 end)      as active_contracts,
    sum(ct.principal)                                          as total_principal,
    round(avg(ct.apr), 4)                                      as avg_apr,
    sum(ct.residual_value)                                     as total_residual
from {{ ref('silver_contracts') }} ct
join {{ ref('silver_customers') }} c on c.customer_id = ct.customer_id
group by c.segment
