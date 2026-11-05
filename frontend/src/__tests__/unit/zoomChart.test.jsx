import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { compact } from "../../components/chartTheme";
import ZoomChart from "../../components/ZoomChart";
import { inr } from "../../format";

// 30 days; revenue peaks on day 20.
const data = Array.from({ length: 30 }, (_, i) => ({ day: `${i + 1} Oct`, net_revenue: i === 19 ? 9000 : 1000 + i }));
const draw = () => render(<ZoomChart data={data} x="day" y="net_revenue" label="Net revenue" format={inr} />);
const windowText = () => document.querySelector(".zoom-window").textContent;
const plot = () => screen.getByRole("group", { name: /Net revenue chart/ });

describe("ZoomChart", () => {
  it("shows the whole period with a readout of what is in view", () => {
    draw();
    expect(windowText()).toBe("1 Oct to 30 Oct (30 of 30 days)");
    expect(screen.getByRole("button", { name: "Zoom out" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reset" })).toBeDisabled();
    const best = screen.getByText("Best day").nextElementSibling;
    expect(best).toHaveTextContent("20 Oct ₹9,000");
    expect(screen.getAllByRole("row")).toHaveLength(31);
  });

  it("zooms in and out with the buttons, and the table follows", async () => {
    const user = userEvent.setup();
    draw();
    await user.click(screen.getByRole("button", { name: "Zoom in" }));
    expect(windowText()).toBe("9 Oct to 23 Oct (15 of 30 days)");
    expect(screen.getAllByRole("row")).toHaveLength(16);
    await user.click(screen.getByRole("button", { name: "Zoom out" }));
    expect(windowText()).toBe("1 Oct to 30 Oct (30 of 30 days)");
    await user.click(screen.getByRole("button", { name: "Zoom in" }));
    await user.click(screen.getByRole("button", { name: "Reset" }));
    expect(windowText()).toBe("1 Oct to 30 Oct (30 of 30 days)");
  });

  it("responds to the keyboard: + and - zoom, arrows pan, 0 resets", () => {
    draw();
    fireEvent.keyDown(plot(), { key: "+" });
    expect(windowText()).toBe("9 Oct to 23 Oct (15 of 30 days)");
    fireEvent.keyDown(plot(), { key: "ArrowRight" });
    expect(windowText()).toBe("13 Oct to 27 Oct (15 of 30 days)");
    fireEvent.keyDown(plot(), { key: "ArrowLeft" });
    expect(windowText()).toBe("9 Oct to 23 Oct (15 of 30 days)");
    fireEvent.keyDown(plot(), { key: "=" });
    expect(windowText()).toBe("13 Oct to 20 Oct (8 of 30 days)");
    fireEvent.keyDown(plot(), { key: "-" });
    expect(windowText()).toBe("9 Oct to 24 Oct (16 of 30 days)");
    fireEvent.keyDown(plot(), { key: "x" });
    expect(windowText()).toBe("9 Oct to 24 Oct (16 of 30 days)");
    fireEvent.keyDown(plot(), { key: "0" });
    expect(windowText()).toBe("1 Oct to 30 Oct (30 of 30 days)");
  });

  it("zooms with Ctrl or ⌘ + scroll but leaves plain scrolling to the page", () => {
    draw();
    fireEvent.wheel(plot(), { deltaY: -100 });
    expect(windowText()).toBe("1 Oct to 30 Oct (30 of 30 days)");
    fireEvent.wheel(plot(), { deltaY: -100, ctrlKey: true });
    expect(windowText()).toBe("4 Oct to 27 Oct (24 of 30 days)");
    fireEvent.wheel(plot(), { deltaY: 100, metaKey: true });
    expect(windowText()).toBe("1 Oct to 30 Oct (30 of 30 days)");
  });

  it("formats axis values compactly", () => {
    expect(compact(125000)).toBe("125k");
    expect(compact(950)).toBe("950");
  });
});
