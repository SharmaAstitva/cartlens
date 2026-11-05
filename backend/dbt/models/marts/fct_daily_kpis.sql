with bounds as (
    select min(occurred_date) as first_day, max(occurred_date) as last_day
    from {{ ref('stg_events') }}
),

days as (
    select generate_series(first_day, last_day, interval '1 day')::date as date from bounds
),

sessions as (
    select occurred_date as date, count(distinct session_id) as sessions
    from {{ ref('stg_events') }}
    where event_type = 'page_view'
    group by 1
),

orders as (
    select
        order_date as date,
        count(*) as orders,
        count(distinct customer_id) as customers,
        count(*) filter (where customer_order_number = 1) as new_customers,
        count(*) filter (where is_refunded) as refunded_orders,
        sum(gross_revenue) as gross_revenue,
        sum(net_revenue) as net_revenue
    from {{ ref('fct_orders') }}
    group by 1
)

select
    d.date,
    coalesce(s.sessions, 0) as sessions,
    coalesce(o.orders, 0) as orders,
    coalesce(o.customers, 0) as customers,
    coalesce(o.new_customers, 0) as new_customers,
    coalesce(o.refunded_orders, 0) as refunded_orders,
    coalesce(o.gross_revenue, 0)::numeric(14, 2) as gross_revenue,
    coalesce(o.net_revenue, 0)::numeric(14, 2) as net_revenue,
    round(o.net_revenue / nullif(o.orders, 0), 2) as avg_order_value,
    round(o.orders::numeric / nullif(s.sessions, 0), 4) as conversion_rate
from days as d
left join sessions as s on s.date = d.date
left join orders as o on o.date = d.date
