"""Ask your data: question -> LLM -> validated JSON -> guarded SQL -> rows + chart."""

from __future__ import annotations

import re
from typing import Literal

import psycopg
from pydantic import BaseModel, ValidationError

from app import queries
from app.llm import LLMError
from app.sql_guard import UnsafeSQLError, guard_sql


class ChartSpec(BaseModel):
    type: Literal["bar", "line", "number", "table"]
    x: str | None = None
    y: str | None = None


class LLMAnswer(BaseModel):
    sql: str
    chart: ChartSpec
    explanation: str


# JSON schema sent to Groq (strict mode: every property required, nulls allowed).
ANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["sql", "chart", "explanation"],
    "properties": {
        "sql": {"type": "string", "description": "One PostgreSQL SELECT query."},
        "chart": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "x", "y"],
            "properties": {
                "type": {"type": "string", "enum": ["bar", "line", "number", "table"]},
                "x": {"type": ["string", "null"], "description": "Result column for the x axis."},
                "y": {"type": ["string", "null"], "description": "Numeric result column to plot."},
            },
        },
        "explanation": {"type": "string", "description": "One or two plain sentences."},
    },
}

SYSTEM_PROMPT = """You are a careful analytics engineer for CartLens, an Indian D2C e-commerce store.
Write ONE PostgreSQL SELECT query that answers the user's question using only these tables
(schema "analytics", already on the search path):

{schema}

Rules:
- Read-only SELECT (CTEs allowed). Never use other tables, system catalogs or functions starting with pg_.
- The data covers {first} to {last}. Treat {last} as "today". "Last month" means the calendar
  month before the month of {last}; "last 30 days" means the 30 days ending {last}.
- Money is in Indian rupees. Use net_revenue for revenue unless the user asks for gross.
- Give result columns short snake_case aliases. Round money to 0 decimals and rates to 3.
- Return at most 50 rows, ordered meaningfully.
- chart: "line" for trends over time (x = date or month column), "bar" for comparing categories,
  "number" for a single value, "table" otherwise. x and y must be column names from your query.
- explanation: one or two plain sentences on how you answered (definitions, time window), not the result."""

EXAMPLES = [
    {
        "question": "Which city had the most repeat buyers last month?",
        "sql": """with bounds as (
  select date_trunc('month', max(order_date)) - interval '1 month' as month_start,
         date_trunc('month', max(order_date)) as month_end
  from fct_orders
)
select o.city, count(distinct o.customer_id) as repeat_buyers
from fct_orders o, bounds b
where o.order_date >= b.month_start and o.order_date < b.month_end
  and o.customer_order_number > 1
group by o.city
order by repeat_buyers desc
limit 10""",
        "chart": {"type": "bar", "x": "city", "y": "repeat_buyers"},
        "explanation": "Counts customers who ordered last month and had ordered before "
        "(customer_order_number > 1), grouped by the order's city.",
    },
    {
        "question": "How has monthly revenue changed over the last 6 months?",
        "sql": """select date_trunc('month', order_date)::date as month,
       round(sum(net_revenue)) as net_revenue
from fct_orders
where order_date >= date_trunc('month', (select max(order_date) from fct_orders))
                    - interval '5 months'
group by 1
order by 1""",
        "chart": {"type": "line", "x": "month", "y": "net_revenue"},
        "explanation": "Sums revenue after refunds per calendar month, for the latest month "
        "and the five before it.",
    },
    {
        "question": "Which product category has the highest refund rate?",
        "sql": """select category,
       count(*) as orders,
       round(avg(case when is_refunded then 1 else 0 end), 3) as refund_rate
from fct_orders
group by category
order by refund_rate desc""",
        "chart": {"type": "bar", "x": "category", "y": "refund_rate"},
        "explanation": "Refund rate is refunded orders divided by all orders in the category, "
        "across all time.",
    },
    {
        "question": "How many customers are in each RFM segment?",
        "sql": """select segment, count(*) as customers, round(sum(monetary)) as net_revenue
from mart_rfm
group by segment
order by customers desc""",
        "chart": {"type": "bar", "x": "segment", "y": "customers"},
        "explanation": "Uses the RFM model: recency, frequency and spend scores combined into "
        "named segments.",
    },
    {
        "question": "What share of orders came from the app in the last 30 days?",
        "sql": """select channel, count(*) as orders,
       round(count(*)::numeric / sum(count(*)) over (), 3) as share
from fct_orders
where order_date > (select max(order_date) from fct_orders) - 30
group by channel
order by orders desc""",
        "chart": {"type": "bar", "x": "channel", "y": "share"},
        "explanation": "Splits orders from the last 30 days by channel (app or web) and divides "
        "by the total.",
    },
]


class AskError(Exception):
    """The question could not be answered (shown to the user as a 422)."""


class AskUnavailable(Exception):
    """No LLM configured and the question is not one of the examples (503)."""


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower()).rstrip("?.! ")


def match_example(question: str) -> dict | None:
    wanted = _normalise(question)
    return next((e for e in EXAMPLES if _normalise(e["question"]) == wanted), None)


def _execute(conn, answer: LLMAnswer, max_rows: int, timeout_ms: int) -> dict:
    sql = guard_sql(answer.sql)
    columns, rows, truncated = queries.run_readonly(conn, sql, max_rows, timeout_ms)
    chart = answer.chart.model_dump()
    if chart["type"] in ("bar", "line") and not {chart["x"], chart["y"]} <= set(columns):
        chart = {"type": "table", "x": None, "y": None}
    return {
        "sql": sql,
        "chart": chart,
        "explanation": answer.explanation,
        "columns": columns,
        "rows": rows,
        "truncated": truncated,
    }


def ask(question: str, *, conn, llm, max_rows: int, timeout_ms: int) -> dict:
    if llm is None:
        example = match_example(question)
        if example is None:
            raise AskUnavailable(
                "The AI model is not configured on this server (demo mode). "
                "Try one of the example questions."
            )
        result = _execute(conn, LLMAnswer.model_validate(example), max_rows, timeout_ms)
        return {"question": question, "mode": "demo", **result}

    first, last = queries.data_range(conn)
    system = SYSTEM_PROMPT.format(schema=queries.describe_marts(conn), first=first, last=last)
    user = f"Question: {question}"
    error = ""
    for _attempt in range(2):  # one repair attempt with the error fed back
        try:
            raw = llm.complete_json(system, user, ANSWER_SCHEMA)
        except LLMError as exc:
            raise AskError(f"The AI model is unavailable right now: {exc}") from exc
        try:
            answer = LLMAnswer.model_validate(raw)
            result = _execute(conn, answer, max_rows, timeout_ms)
            return {"question": question, "mode": "groq", **result}
        except (ValidationError, UnsafeSQLError, psycopg.Error) as exc:
            error = " ".join(str(exc).split())[:500]
            user = (
                f"Question: {question}\n\nYour previous answer failed with this error:\n{error}\n"
                "Fix the query and answer again."
            )
    raise AskError(f"Couldn't build a working query for that question. Last error: {error}")
