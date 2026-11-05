import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { reply } from "../fixtures";
import { renderApp } from "./helpers";

describe("App shell", () => {
  it("shows how fresh the data is", async () => {
    renderApp("/");
    expect(await screen.findByText("Data through 3 Nov 2026")).toBeInTheDocument();
  });

  it("navigates between pages", async () => {
    const user = userEvent.setup();
    renderApp("/");
    const nav = screen.getByRole("navigation");
    await user.click(within(nav).getByRole("link", { name: "Customers" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Customers" })).toBeInTheDocument();
    await user.click(within(nav).getByRole("link", { name: "Ask your data" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Ask your data" })).toBeInTheDocument();
    expect(within(nav).getByRole("link", { name: "Ask your data" })).toHaveAttribute("aria-current", "page");
  });

  it("shows a not-found page", async () => {
    renderApp("/nope");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to the overview" })).toHaveAttribute("href", "/");
  });

  it("says when the API cannot be reached", async () => {
    renderApp("/", { "/api/health": reply(503, { detail: "Database unavailable" }) });
    expect(await screen.findByText("API unreachable")).toBeInTheDocument();
  });
});
