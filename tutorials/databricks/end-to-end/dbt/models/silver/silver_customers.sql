-- silver: current-state customers from bronze (typed; latest per customer_id).
{{ config(schema='silver', tags=['medallion'], materialized='table') }}
select
    customer_id,
    legal_name,
    segment,
    region,
    credit_rating,
    cast(annual_revenue as decimal(14, 2)) as annual_revenue,
    cast(onboarded_date as date)           as onboarded_date
from silverline.bronze.customers
qualify row_number() over (partition by customer_id order by updated_at desc) = 1
