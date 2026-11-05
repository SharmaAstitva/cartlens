-- Every city spelling in the feed must map to a standard city via seeds/city_aliases.csv.
-- If this fails, add the new spelling to the seed.
select distinct city_raw
from {{ ref('stg_events') }}
where city is null and city_raw is not null
