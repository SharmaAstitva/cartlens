"""Unit tests for the Ask-your-data service. The database and LLM are faked."""

from datetime import date

import pytest

from app import ask as ask_module
from app.ask import EXAMPLES, AskError, AskUnavailable, ask, match_example
from app.llm import LLMError


class FakeLLM:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []

    def complete_json(self, system, user, schema):
        self.prompts.append((system, user, schema))
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def db(monkeypatch):
    """Fake the three query functions ask() needs and record executed SQL."""
    executed = []

    def run_readonly(conn, sql, max_rows, timeout_ms):
        executed.append(sql)
        if "boom" in sql:
            raise ask_module.psycopg.errors.UndefinedColumn('column "boom" does not exist')
        return ["city", "repeat_buyers"], [["Pune", 12], ["Surat", 9]], False

    monkeypatch.setattr(ask_module.queries, "describe_marts", lambda conn: "fct_orders(city text)")
    monkeypatch.setattr(
        ask_module.queries, "data_range", lambda conn: (date(2025, 11, 4), date(2026, 11, 3))
    )
    monkeypatch.setattr(ask_module.queries, "run_readonly", run_readonly)
    return executed


def good(sql="select city, count(*) as repeat_buyers from fct_orders group by city", chart=None):
    return {
        "sql": sql,
        "chart": chart or {"type": "bar", "x": "city", "y": "repeat_buyers"},
        "explanation": "Pune leads.",
    }


def call(question, llm, **kw):
    return ask(question, conn=None, llm=llm, max_rows=200, timeout_ms=5000, **kw)


def test_llm_answer_is_guarded_executed_and_returned(db):
    llm = FakeLLM(good())
    out = call("Which city has the most repeat buyers?", llm)
    assert out["mode"] == "groq"
    assert out["columns"] == ["city", "repeat_buyers"]
    assert out["rows"][0] == ["Pune", 12]
    assert out["chart"] == {"type": "bar", "x": "city", "y": "repeat_buyers"}
    assert out["explanation"] == "Pune leads."
    assert out["sql"].startswith("SELECT")
    assert db == [out["sql"]]


def test_prompt_contains_schema_and_data_dates(db):
    llm = FakeLLM(good())
    call("Revenue last month?", llm)
    system, user, schema = llm.prompts[0]
    assert "fct_orders(city text)" in system
    assert "2026-11-03" in system
    assert "Revenue last month?" in user
    assert schema["required"] == ["sql", "chart", "explanation"]


def test_unsafe_sql_gets_one_repair_attempt(db):
    llm = FakeLLM(good("select * from raw.events"), good())
    out = call("q?", llm)
    assert out["rows"]
    assert "raw.events" in llm.prompts[1][1], "the error should be fed back to the model"


def test_database_error_gets_one_repair_attempt(db):
    llm = FakeLLM(good("select boom from fct_orders"), good())
    out = call("q?", llm)
    assert out["rows"] and len(llm.prompts) == 2
    assert "boom" in llm.prompts[1][1]


def test_invalid_json_shape_gets_one_repair_attempt(db):
    llm = FakeLLM({"sql": "select 1"}, good())
    assert call("q?", llm)["rows"]


def test_two_failures_raise_ask_error(db):
    llm = FakeLLM(good("drop table fct_orders"), good("delete from fct_orders"))
    with pytest.raises(AskError, match="SELECT"):
        call("q?", llm)
    assert db == []


def test_llm_outage_raises_ask_error(db):
    llm = FakeLLM(LLMError("Groq returned 503"))
    with pytest.raises(AskError, match="503"):
        call("q?", llm)


def test_chart_with_unknown_columns_falls_back_to_table(db):
    llm = FakeLLM(good(chart={"type": "line", "x": "month", "y": "revenue"}))
    assert call("q?", llm)["chart"]["type"] == "table"


def test_demo_mode_answers_example_questions(db):
    example = EXAMPLES[0]
    out = call(example["question"].upper() + "  ", None)
    assert out["mode"] == "demo"
    assert out["explanation"] == example["explanation"]
    assert len(db) == 1


def test_demo_mode_refuses_other_questions(db):
    with pytest.raises(AskUnavailable):
        call("What is the meaning of life?", None)


def test_match_example_ignores_case_and_punctuation():
    q = EXAMPLES[1]["question"]
    assert match_example(q.lower().rstrip("?")) is EXAMPLES[1]
    assert match_example("something else") is None


def test_every_example_passes_the_guard():
    from app.sql_guard import guard_sql

    for example in EXAMPLES:
        assert guard_sql(example["sql"])
