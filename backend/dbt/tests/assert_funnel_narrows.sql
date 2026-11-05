select month
from {{ ref('mart_funnel_monthly') }}
where sessions_added_to_cart > sessions_viewed
   or sessions_checked_out > sessions_added_to_cart
   or sessions_ordered > sessions_checked_out
