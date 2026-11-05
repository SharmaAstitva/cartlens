-- Recency is measured from the latest order date in the data, not today's date,
-- so the scores are reproducible.
with base as (
    select
        customer_id,
        city,
        (select max(order_date) from {{ ref('fct_orders') }}) - last_order_date as recency_days,
        order_count as frequency,
        lifetime_net_revenue as monetary
    from {{ ref('dim_customers') }}
),

scored as (
    select
        *,
        case
            when recency_days <= 30 then 5
            when recency_days <= 60 then 4
            when recency_days <= 120 then 3
            when recency_days <= 240 then 2
            else 1
        end as r_score,
        case
            when frequency >= 6 then 5
            when frequency >= 4 then 4
            when frequency = 3 then 3
            when frequency = 2 then 2
            else 1
        end as f_score,
        ntile(5) over (order by monetary, customer_id) as m_score
    from base
)

select
    *,
    case
        when r_score >= 4 and f_score >= 4 then 'Champions'
        when r_score >= 3 and f_score >= 3 then 'Loyal'
        when r_score >= 4 and f_score = 1 then 'New'
        when r_score <= 2 and f_score >= 3 then 'At risk'
        when r_score <= 2 then 'Hibernating'
        else 'Needs attention'
    end as segment
from scored
