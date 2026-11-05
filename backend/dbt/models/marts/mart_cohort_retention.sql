with firsts as (
    select customer_id, date_trunc('month', first_order_date)::date as cohort_month
    from {{ ref('dim_customers') }}
),

activity as (
    select distinct customer_id, date_trunc('month', order_date)::date as active_month
    from {{ ref('fct_orders') }}
),

sizes as (
    select cohort_month, count(*) as cohort_size from firsts group by 1
)

select
    f.cohort_month,
    (
        (extract(year from a.active_month) * 12 + extract(month from a.active_month))
        - (extract(year from f.cohort_month) * 12 + extract(month from f.cohort_month))
    )::int as month_number,
    s.cohort_size,
    count(*) as active_customers,
    round(count(*)::numeric / s.cohort_size, 4) as retention_rate
from firsts as f
inner join activity as a on a.customer_id = f.customer_id
inner join sizes as s on s.cohort_month = f.cohort_month
group by 1, 2, 3
