import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { answer, reply } from "../fixtures";
import { renderApp } from "./helpers";

describe("Ask your data", () => {
  it("answers an example question with chart, explanation and SQL", async () => {
    const user = userEvent.setup();
    const { fetchMock } = renderApp("/ask");
    await user.click(await screen.findByRole("button", { name: answer.question }));

    expect(await screen.findByText(answer.explanation)).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Mumbai" })).toBeInTheDocument();
    expect(screen.getByText("Show the SQL")).toBeInTheDocument();
    expect(screen.getByText(/COUNT\(DISTINCT customer_id\)/)).toBeInTheDocument();
    const call = fetchMock.mock.calls.find(([url]) => url.endsWith("/api/v1/ask"));
    expect(JSON.parse(call[1].body)).toEqual({ question: answer.question });
  });

  it("explains demo mode", async () => {
    renderApp("/ask");
    expect(await screen.findByText(/Demo mode/)).toBeInTheDocument();
  });

  it("submits a typed question", async () => {
    const user = userEvent.setup();
    renderApp("/ask", { "/api/v1/ask/examples": { mode: "groq", questions: [] } });
    await user.type(screen.getByRole("textbox", { name: "Your question" }), "Top cities by revenue?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText(answer.explanation)).toBeInTheDocument();
    expect(screen.queryByText(/Demo mode/)).not.toBeInTheDocument();
  });

  it("does not submit an empty question", async () => {
    renderApp("/ask");
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  it("shows why a question could not be answered", async () => {
    const user = userEvent.setup();
    renderApp("/ask", {
      "/api/v1/ask/examples": { mode: "groq", questions: [] },
      "/api/v1/ask": reply(422, { detail: "Couldn't build a working query for that question." }),
    });
    await user.type(screen.getByRole("textbox", { name: "Your question" }), "What is love?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't build a working query");
  });

  it("notes truncated results", async () => {
    const user = userEvent.setup();
    renderApp("/ask", { "/api/v1/ask": { ...answer, truncated: true, chart: { type: "table", x: null, y: null } } });
    await user.click(await screen.findByRole("button", { name: answer.question }));
    expect(await screen.findByText(/Showing the first 2 rows/)).toBeInTheDocument();
  });
});
