"""Check LLM-written SQL before it touches the database.

This is one of three layers. The others: execution in a READ ONLY transaction
with a statement timeout (queries.run_readonly), and a row limit.
"""

import sqlglot
from sqlglot import exp

ALLOWED_TABLES = frozenset(
    {
        "fct_orders",
        "dim_customers",
        "fct_daily_kpis",
        "mart_funnel_monthly",
        "mart_cohort_retention",
        "mart_rfm",
        "mart_city_summary",
    }
)
ALLOWED_SCHEMA = "analytics"
BLOCKED_FUNCTIONS = {
    "dblink",
    "set_config",
    "current_setting",
    "query_to_xml",
    "lo_import",
    "lo_export",
}
FORBIDDEN_NODES = (exp.Into, exp.Lock, exp.Insert, exp.Update, exp.Delete, exp.Merge)


class UnsafeSQLError(ValueError):
    pass


def guard_sql(sql: str) -> str:
    """Return the query re-rendered from its parse tree, or raise UnsafeSQLError."""
    if not sql or not sql.strip():
        raise UnsafeSQLError("The query is empty.")
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except sqlglot.errors.SqlglotError as exc:
        raise UnsafeSQLError(f"Could not parse the SQL: {exc}") from exc
    if len(statements) != 1:
        raise UnsafeSQLError("Only one statement is allowed.")
    tree = statements[0]
    if not isinstance(tree, exp.Query):
        raise UnsafeSQLError("Only a single SELECT query is allowed.")

    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            kind = (
                "INTO"
                if isinstance(node, exp.Into)
                else "lock"
                if isinstance(node, exp.Lock)
                else "write"
            )
            raise UnsafeSQLError(f"SELECT ... {kind} clauses are not allowed.")
        if isinstance(node, exp.Func):
            name = (node.name if isinstance(node, exp.Anonymous) else node.sql_name()).lower()
            if name.startswith("pg_") or name in BLOCKED_FUNCTIONS:
                raise UnsafeSQLError(f"The function {name}() is not allowed.")

    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name, schema = table.name.lower(), table.db.lower()
        if not name:  # table function such as generate_series(); checked above
            continue
        if not schema and name in cte_names:
            continue
        full = f"{schema}.{name}" if schema else name
        if table.catalog or (schema and schema != ALLOWED_SCHEMA) or name not in ALLOWED_TABLES:
            allowed = ", ".join(sorted(ALLOWED_TABLES))
            raise UnsafeSQLError(f"Table {full} is not allowed. Use only: {allowed}.")

    return tree.sql(dialect="postgres", pretty=True)
