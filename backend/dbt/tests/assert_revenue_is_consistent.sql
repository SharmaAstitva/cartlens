select order_id
from {{ ref('fct_orders') }}
where gross_revenue < 0
   or net_revenue < 0
   or net_revenue > gross_revenue
   or (is_refunded and net_revenue <> 0)
