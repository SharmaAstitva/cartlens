with refunds as (
    select order_id, refunded_at from {{ ref('stg_refunds') }}
)

select
    o.order_id,
    o.customer_id,
    o.occurred_at as ordered_at,
    o.occurred_date as order_date,
    o.city,
    o.state,
    o.city_tier,
    o.channel,
    o.device,
    o.product_id,
    o.category,
    o.quantity,
    o.unit_price,
    (o.quantity * o.unit_price)::numeric(12, 2) as gross_revenue,
    r.refunded_at is not null as is_refunded,
    r.refunded_at,
    (case when r.refunded_at is null then o.quantity * o.unit_price else 0 end)::numeric(12, 2)
        as net_revenue,
    row_number() over (partition by o.customer_id order by o.occurred_at, o.order_id)
        as customer_order_number
from {{ ref('stg_orders') }} as o
left join refunds as r on r.order_id = o.order_id
