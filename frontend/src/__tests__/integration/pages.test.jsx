import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderApp } from "./helpers";

describe("Customers page", () => {
  it("shows segments and the cohort grid", async () => {
    renderApp("/customers");
    expect(await screen.findByRole("cell", { name: "Champions" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "₹25,00,000" })).toBeInTheDocument();
    expect(await screen.findByTitle("Sep 2026 cohort, month 1: 120 of 500 customers")).toBeInTheDocument();
  });
});

describe("Funnel page", () => {
  it("shows the latest month's funnel with step conversion", async () => {
    renderApp("/funnel");
    const steps = await screen.findByRole("list", { name: "Funnel for Nov 2026" });
    const items = within(steps).getAllByRole("listitem");
    expect(items).toHaveLength(4);
    expect(items[1]).toHaveTextContent("Added to cart");
    expect(items[1]).toHaveTextContent("38.3% of previous step");
    expect(screen.getByRole("cell", { name: "Oct 2026" })).toBeInTheDocument();
  });

  it("handles no data", async () => {
    renderApp("/funnel", { "/api/v1/funnel": [] });
    expect(await screen.findByText("No sessions yet. Run the pipeline to load data.")).toBeInTheDocument();
  });
});

describe("Pipeline page", () => {
  it("shows health, row counts and run history", async () => {
    renderApp("/pipeline");
    expect(await screen.findByRole("group", { name: "Raw events" })).toHaveTextContent("2,71,000");
    expect(screen.getByRole("group", { name: "AI model" })).toHaveTextContent("Demo mode");
    expect(await screen.findByText("connection refused")).toBeInTheDocument();
    expect(screen.getByText("34 passed")).toBeInTheDocument();
    expect(screen.getAllByText("success").length).toBeGreaterThan(0);
  });

  it("names the model when one is configured", async () => {
    renderApp("/pipeline", {
      "/api/health": {
        status: "ok", database: "ok", llm: { mode: "groq", model: "openai/gpt-oss-120b" },
        counts: { raw_events: 1, quarantined: 0, orders: null, customers: null }, last_run: null, data_through: null,
      },
    });
    expect(await screen.findByRole("group", { name: "AI model" })).toHaveTextContent("openai/gpt-oss-120b");
    expect(screen.getByText("Data not loaded yet")).toBeInTheDocument();
  });
});
