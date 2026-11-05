import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderApp } from "./helpers";

const dialog = () => screen.queryByRole("dialog", { name: "Jump to a page" });

describe("Command palette", () => {
  it("opens with Ctrl+K, filters, and goes to the chosen page with Enter", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.keyboard("{Control>}k{/Control}");
    expect(dialog()).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Search pages" })).toHaveFocus();
    await user.keyboard("fun");
    expect(within(dialog()).getAllByRole("option")).toHaveLength(1);
    await user.keyboard("{Enter}");
    expect(dialog()).not.toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 1, name: "Funnel" })).toBeInTheDocument();
  });

  it("moves through results with the arrow keys and closes with Escape", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.click(screen.getByRole("button", { name: /Jump to/ }));
    const options = within(dialog()).getAllByRole("option");
    expect(options[0]).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowDown}{ArrowDown}{ArrowUp}");
    expect(options[1]).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowUp}{ArrowUp}");
    expect(options[0]).toHaveAttribute("aria-selected", "true");
    for (let i = 0; i < 9; i++) await user.keyboard("{ArrowDown}");
    expect(options.at(-1)).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{Shift}");
    await user.keyboard("{Escape}");
    expect(dialog()).not.toBeInTheDocument();
  });

  it("says when nothing matches, ignores Enter, and closes on a click outside", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.keyboard("{Meta>}k{/Meta}");
    await user.keyboard("zzz{Enter}");
    expect(within(dialog()).getByText("No page matches “zzz”.")).toBeInTheDocument();
    await user.click(screen.getByRole("dialog"));
    expect(dialog()).toBeInTheDocument();
    await user.click(document.querySelector(".palette-backdrop"));
    expect(dialog()).not.toBeInTheDocument();
  });

  it("goes to a page that is clicked, and Ctrl+K toggles it shut", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.keyboard("{Control>}k{/Control}");
    const pipeline = within(dialog()).getByRole("option", { name: /Pipeline/ });
    await user.hover(pipeline);
    expect(pipeline).toHaveAttribute("aria-selected", "true");
    await user.click(pipeline);
    expect(await screen.findByRole("heading", { level: 1, name: "Pipeline" })).toBeInTheDocument();
    await user.keyboard("{Control>}k{/Control}");
    await user.keyboard("{Control>}k{/Control}");
    expect(dialog()).not.toBeInTheDocument();
  });
});
