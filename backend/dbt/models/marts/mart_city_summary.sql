select
    city,
    state,
    city_tier,
    count(*) as customers,
    count(*) filter (where is_repeat_buyer) as repeat_customers,
    round(count(*) filter (where is_repeat_buyer)::numeric / count(*), 4) as repeat_rate,
    sum(order_count) as orders,
    sum(lifetime_net_revenue)::numeric(14, 2) as net_revenue,
    round(sum(lifetime_net_revenue) / sum(order_count), 2) as avg_order_value
from {{ ref('dim_customers') }}
group by city, state, city_tier
