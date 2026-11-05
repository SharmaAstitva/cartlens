select distinct on (order_id)
    order_id,
    occurred_at as refunded_at
from {{ ref('stg_events') }}
where event_type = 'order_refunded'
order by order_id, occurred_at
