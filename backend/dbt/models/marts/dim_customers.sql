select
    customer_id,
    (array_agg(city order by ordered_at desc))[1] as city,
    (array_agg(state order by ordered_at desc))[1] as state,
    (array_agg(city_tier order by ordered_at desc))[1] as city_tier,
    (array_agg(channel order by ordered_at))[1] as first_channel,
    min(order_date) as first_order_date,
    max(order_date) as last_order_date,
    count(*) as order_count,
    sum(net_revenue)::numeric(14, 2) as lifetime_net_revenue,
    count(*) >= 2 as is_repeat_buyer
from {{ ref('fct_orders') }}
group by customer_id
