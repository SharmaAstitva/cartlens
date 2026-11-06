# Testing strategy

CartLens has three kinds of tests, because there are three kinds of things that can break:
the code, the integration between the code and real infrastructure, and the data itself.

| Layer | Tool | Where | Runs |
| --- | --- | --- | --- |
| Unit tests | pytest, Vitest | `backend/tests/unit`, `frontend/src/__tests__/unit` | every push (CI) |
| Integration tests | pytest + real Postgres, Vitest + Testing Library | `backend/tests/integration`, `frontend/src/__tests__/integration` | every push (CI) |
| Data tests | dbt | `backend/dbt/models/**/_*.yml`, `backend/dbt/tests` | every pipeline run, and inside the integration tests |

## How the code was written: test first

Each module started as a failing test file (red), then the smallest code that passed it (green), then a cleanup
with the tests as a safety net (refactor). For example, `test_sql_guard.py` listed the queries that must be
allowed and the attacks that must be blocked before `sql_guard.py` existed; adding the "CTE named like an
allowed table hides `raw.events`" case later drove the rule that CTE names only shadow unqualified tables.

## Backend

### Unit tests (no database, no network): 106 tests, about 10 seconds

| File | What it proves |
| --- | --- |
| `test_generator.py` | Same window → identical events; nothing from the future; **two adjacent windows equal one combined window** (no event lost or loaded twice across daily runs, including late arrivals and refunds); the feed really contains each kind of mess the pipeline must clean |
| `test_ingest.py` | The quarantine rules: missing customer, unknown event type, empty id, non-object payload |
| `test_flow.py` | Which days a run loads (first run, next day, missed runs, already up to date); turning `DATABASE_URL` into dbt settings (including Neon's `sslmode=require` and URL-encoded passwords); counting dbt results |
| `test_sql_guard.py` | 7 legitimate queries pass; 26 unsafe ones fail with a useful message (writes, multiple statements, raw/ops/system tables, `pg_sleep`, `dblink`, `SELECT INTO`, `FOR UPDATE`...) |
| `test_llm.py` | The Groq client sends the model, schema and key; HTTP errors, network errors and bad JSON all become `LLMError` (uses `httpx.MockTransport`, never the network) |
| `test_ask.py` | Ask service with a fake LLM: happy path, prompt contents, **one repair attempt** after unsafe SQL / database error / bad JSON shape, giving up after two failures, chart fallback, demo mode |
| `test_api.py` | Every endpoint, parameter validation (422), database down (503), tables not built yet (503 with instructions), CORS |
| `test_config.py` | Environment parsing and defaults |

### Integration tests (real Postgres): 29 tests, about 45 seconds

`tests/integration/conftest.py` runs the **real Prefect flow three times** against an empty database:

1. a first run that backfills 120 days and runs `dbt build`;
2. the same day again, which must load nothing (`up_to_date`);
3. the next day, which must load exactly one day.

The other integration tests then check the result:

- `test_pipeline.py`: all dbt tests pass; duplicates are dropped and bad events quarantined; double-submitted
  orders are counted once; every city spelling is standardised; every timestamp format is parsed; every mart has
  rows; dbt's column descriptions reached Postgres (the AI prompt depends on them).
- `test_ingest_db.py`: `COPY` loading, dedupe on `event_id`, quarantine, and that reloading a batch changes
  nothing. Each test runs inside a transaction that is rolled back.
- `test_api_db.py`: every endpoint against real data; **every demo question runs on real data**; the guard
  stops LLM SQL that reads `raw.events`; and the database layer blocks writes and slow queries **even when the
  guard is bypassed** (defence in depth).

Tests never depend on today's date: the flow is given a fixed `as_of` date (1 March 2026), and the generator is
deterministic.

Locally, start the database first: `docker compose up -d db`. The tests use a separate `cartlens_test` database,
created by `db/init/01-test-database.sql`. In CI, a Postgres service container plays the same role.

```bash
cd backend
pytest tests/unit                  # fast, no database
pytest tests/integration           # needs Postgres
pytest --cov                       # everything, with the 90% gate
```

## Frontend

67 tests, about 8 seconds. `fetch` is stubbed with fixtures (`src/__tests__/fixtures.js`), so no API is needed.

- **Unit** (`src/__tests__/unit`): number formatting (Indian digit grouping: ₹17,34,567, ₹1.7Cr), the API
  client's error messages, the `useApi` hook (loading, error, retry, path change), and the Chart, DataTable,
  CohortGrid and Status components. The zoomable chart is tested in three layers: the pure range maths in
  `zoom.js` (zoom around the centre, minimum width, clamping at the edges, panning), the `ZoomChart` component
  (buttons, keyboard, Ctrl + scroll, and the readout and table following the window), and the `useCountUp`
  animation hook with a stubbed clock and `requestAnimationFrame`, including the reduced-motion path.
- **Integration** (`src/__tests__/integration`): the whole `<App>` rendered in a router, as a user sees it:
  navigation, the Ctrl + K quick switcher (filtering, arrow keys, Enter, Escape, clicking outside), KPIs with
  period-over-period change, switching the period, an empty period, the funnel, cohorts, the pipeline page,
  and the Ask flow (click an example, type a question, see the SQL, errors, demo mode). Queries use roles and
  labels (`getByRole("group", { name: "Net revenue" })`), which also checks basic accessibility.

```bash
cd frontend
npm run test:unit
npm run test:integration
npm run coverage                   # everything, with the 90% gate
```

## Data tests (dbt)

37 tests run on every `dbt build`: `unique` / `not_null` on keys, `accepted_values` (event types, channels,
categories, segments), a `relationships` test (every order's customer exists), and four custom tests:

- `assert_every_city_is_mapped`: a new city spelling in the feed fails the build until it is added to the seed;
- `assert_revenue_is_consistent`: no negative revenue, refunded orders have zero net revenue;
- `assert_retention_is_a_rate`: retention between 0 and 1, and exactly 1 in a cohort's first month;
- `assert_funnel_narrows`: each funnel step is no larger than the one before.

A failing data test fails the pipeline run, which is recorded as `failed` in `ops.pipeline_runs` and shown on
the Pipeline page.

## Coverage (measured)

| | Gate | Measured |
| --- | --- | --- |
| Backend (unit + integration, branch coverage on) | 90% | 98.6% |
| Frontend statements / branches / functions / lines | 90% each | 98.6% / 97.9% / 96.6% / 98.9% |

## What is not tested automatically

- The real Groq API (it is mocked; checking it would make CI depend on a third-party key and rate limits).
  Check it by hand after deploying: `/api/health` shows the model, and the Ask page should answer a new question.
- The browser end to end (Playwright is on the roadmap). Recharts draws nothing in jsdom because there is no
  layout, so dragging the chart navigator is checked by hand; the zoom logic it calls is unit-tested.
- The Docker images are built in CI but not started there; `docker compose up` is checked by hand.
