{{
    config(
        materialized='table'
    )
}}

with source_data as (
    select 
        1 as user_id,
        'John Doe' as name,
        'john@example.com' as email,
        '2024-01-01' as created_at
    union all
    select 
        2 as user_id,
        'Jane Smith' as name,
        'jane@example.com' as email,
        '2024-01-02' as created_at
)

select * from source_data 