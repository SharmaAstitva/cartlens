import { useState } from "react";
import { postJson } from "../api";
import Chart from "../components/Chart";
import { ErrorNote, Loading } from "../components/Status";
import { useApi } from "../useApi";

function Answer({ result }) {
  return (
    <article className="answer">
      <p className="answer-question">{result.question}</p>
      <p>{result.explanation}</p>
      <Chart spec={result.chart} columns={result.columns} rows={result.rows} />
      {result.truncated && <p className="muted">Showing the first {result.rows.length} rows.</p>}
      <details>
        <summary>Show the SQL</summary>
        <pre>
          <code>{result.sql}</code>
        </pre>
      </details>
    </article>
  );
}

export default function Ask() {
  const examples = useApi("/api/v1/ask/examples");
  const [question, setQuestion] = useState("");
  const [state, setState] = useState({ busy: false, result: null, error: null });

  async function ask(q) {
    setQuestion(q);
    setState({ busy: true, result: null, error: null });
    try {
      setState({ busy: false, result: await postJson("/api/v1/ask", { question: q }), error: null });
    } catch (err) {
      setState({ busy: false, result: null, error: err.message });
    }
  }

  const demo = examples.data?.mode === "demo";
  return (
    <section className="ask">
      <h1>Ask your data</h1>
      <form
        className="ask-form"
        onSubmit={(e) => {
          e.preventDefault();
          ask(question.trim());
        }}
      >
        <label htmlFor="question" className="visually-hidden">
          Your question
        </label>
        <input
          id="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Which city had the most repeat buyers last month?"
          maxLength={300}
          autoComplete="off"
        />
        <button type="submit" disabled={question.trim().length < 3 || state.busy}>
          Ask
        </button>
      </form>
      {demo && (
        <p className="note">
          Demo mode: this server has no AI key, so only the example questions below are answered.
        </p>
      )}
      {examples.data?.questions.length > 0 && (
        <ul className="chips" aria-label="Example questions">
          {examples.data.questions.map((q) => (
            <li key={q}>
              <button type="button" onClick={() => ask(q)} disabled={state.busy}>
                {q}
              </button>
            </li>
          ))}
        </ul>
      )}
      {state.busy && <Loading label="Writing and checking the query" />}
      {state.error && <ErrorNote message={state.error} />}
      {state.result && <Answer result={state.result} />}
    </section>
  );
}
