{# Timestamps arrive in four formats: ISO with offset, ISO UTC, DD/MM/YYYY local (IST), epoch ms. #}
{% macro parse_ts(col) %}
    case
        when {{ col }} ~ '^\d{13}$' then to_timestamp(({{ col }})::bigint / 1000.0)
        when {{ col }} ~ '^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$'
            then to_timestamp({{ col }}, 'DD/MM/YYYY HH24:MI:SS')::timestamp at time zone 'Asia/Kolkata'
        else ({{ col }})::timestamptz
    end
{% endmacro %}

{# Prices arrive as numbers or as strings like "₹1,299.00". #}
{% macro parse_price(col) %}
    nullif(regexp_replace({{ col }}, '[^0-9.]', '', 'g'), '')::numeric(12, 2)
{% endmacro %}

{% macro ist_date(col) %}
    ({{ col }} at time zone 'Asia/Kolkata')::date
{% endmacro %}
