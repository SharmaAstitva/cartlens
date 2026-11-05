import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { kpis, reply } from "../fixtures";
import { renderApp } from "./helpers";

describe("Overview page", () => {
  it("shows KPIs with change against the previous period", async () => {
    renderApp("/");
    const revenue = await screen.findByRole("group", { name: "Net revenue" });
    expect(revenue).toHaveTextContent("₹12.5L");
    expect(revenue).toHaveTextContent("+25.0%");
    expect(screen.getByRole("group", { name: "Repeat rate" })).toHaveTextContent("41.4%");
    expect(screen.getByRole("group", { name: "Orders" })).toHaveTextContent("0.0%");
  });

  it("lists top cities", async () => {
    renderApp("/");
    expect(await screen.findByRole("cell", { name: "Mumbai" })).toBeInTheDocument();
  });

  it("changes the period", async () => {
    const user = userEvent.setup();
    const { fetchMock } = renderApp("/");
    await screen.findByRole("group", { name: "Net revenue" });
    await user.click(screen.getByRole("button", { name: "90 days" }));
    expect(screen.getByRole("button", { name: "90 days" })).toHaveAttribute("aria-pressed", "true");
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/api/v1/kpis?days=90"))).toBe(true);
  });

  it("has a zoomable revenue chart", async () => {
    renderApp("/");
    expect(await screen.findByRole("group", { name: "Chart zoom" })).toBeInTheDocument();
    expect(screen.getByText(/2 of 2 days/)).toBeInTheDocument();
  });

  it("says when a period has no orders", async () => {
    renderApp("/", { "/api/v1/kpis": { ...kpis, series: [] } });
    expect(await screen.findByText("No orders in this period yet.")).toBeInTheDocument();
  });

  it("explains when the warehouse is empty", async () => {
    renderApp("/", {
      "/api/v1/kpis": reply(503, { detail: "Analytics tables are not built yet. Run the pipeline first." }),
    });
    expect(await screen.findByText(/Run the pipeline first/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Try again" }).length).toBeGreaterThan(0);
  });
});
