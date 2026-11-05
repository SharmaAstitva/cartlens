select cohort_month, month_number
from {{ ref('mart_cohort_retention') }}
where retention_rate < 0
   or retention_rate > 1
   or month_number < 0
   or (month_number = 0 and retention_rate <> 1)
