-- Landing and bookkeeping tables. Idempotent: safe to run on every pipeline run.
create schema if not exists raw;
create schema if not exists ops;

create table if not exists raw.events (
    event_id   text primary key,              -- duplicate deliveries are dropped here
    payload    jsonb not null,                -- the event exactly as received
    batch_id   text not null,
    loaded_at  timestamptz not null default now()
);

create table if not exists raw.quarantine (
    payload_hash   text primary key,
    payload        jsonb not null,
    reason         text not null,
    batch_id       text not null,
    quarantined_at timestamptz not null default now()
);

create table if not exists ops.pipeline_runs (
    run_id             bigserial primary key,
    started_at         timestamptz not null,
    finished_at        timestamptz not null,
    status             text not null,       -- success | up_to_date | failed
    as_of              date not null,
    window_start       date,
    window_end         date,
    events_received    int,
    events_inserted    int,
    events_duplicate   int,
    events_quarantined int,
    dbt_models_ok      int,
    dbt_tests_passed   int,
    dbt_tests_failed   int,
    error              text
);
