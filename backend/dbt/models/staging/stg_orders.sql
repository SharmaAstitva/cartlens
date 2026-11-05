-- One row per order. A double-click on "Pay" sends the same order twice with
-- different event ids, so keep only the first event per order_id.
select distinct on (order_id) *
from {{ ref('stg_events') }}
where event_type = 'order_placed'
order by order_id, occurred_at, event_id
