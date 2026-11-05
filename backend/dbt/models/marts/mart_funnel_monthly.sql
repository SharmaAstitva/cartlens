with sessions as (
    select
        session_id,
        date_trunc('month', min(occurred_date))::date as month,
        bool_or(event_type = 'page_view') as viewed,
        bool_or(event_type = 'add_to_cart') as carted,
        bool_or(event_type = 'checkout_started') as checked_out,
        bool_or(event_type = 'order_placed') as ordered
    from {{ ref('stg_events') }}
    group by session_id
)

select
    month,
    count(*) filter (where viewed) as sessions_viewed,
    count(*) filter (where carted) as sessions_added_to_cart,
    count(*) filter (where checked_out) as sessions_checked_out,
    count(*) filter (where ordered) as sessions_ordered
from sessions
group by month
