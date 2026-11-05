-- One row per delivered event, with values cleaned and cities standardised.
with raw_events as (
    select event_id, payload, loaded_at from {{ source('raw', 'events') }}
),

parsed as (
    select
        event_id,
        payload ->> 'event_type' as event_type,
        {{ parse_ts("payload ->> 'ts'") }} as occurred_at,
        payload ->> 'customer_id' as customer_id,
        payload ->> 'session_id' as session_id,
        payload ->> 'city' as city_raw,
        lower(regexp_replace(trim(payload ->> 'city'), '\s+', ' ', 'g')) as city_key,
        payload ->> 'channel' as channel,
        payload ->> 'device' as device,
        payload ->> 'product_id' as product_id,
        payload ->> 'category' as category,
        (payload ->> 'quantity')::int as quantity,
        {{ parse_price("payload ->> 'price'") }} as unit_price,
        payload ->> 'order_id' as order_id,
        loaded_at
    from raw_events
)

select
    p.event_id,
    p.event_type,
    p.occurred_at,
    {{ ist_date('p.occurred_at') }} as occurred_date,
    p.customer_id,
    p.session_id,
    a.city,
    a.state,
    a.tier as city_tier,
    p.city_raw,
    p.channel,
    p.device,
    p.product_id,
    p.category,
    p.quantity,
    p.unit_price,
    p.order_id,
    p.loaded_at
from parsed as p
left join {{ ref('city_aliases') }} as a on a.alias = p.city_key
