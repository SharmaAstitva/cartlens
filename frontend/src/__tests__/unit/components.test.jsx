import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Chart from "../../components/Chart";
import CohortGrid from "../../components/CohortGrid";
import DataTable from "../../components/DataTable";
import { ErrorNote, Loading } from "../../components/Status";
import { cohorts } from "../fixtures";

const columns = ["city", "repeat_buyers"];
const rows = [["Mumbai", 52], ["Pune", 47]];

describe("DataTable", () => {
  it("renders headers and formatted cells", () => {
    render(<DataTable columns={["city", "net_revenue"]} rows={[["Pune", 1500]]} />);
    expect(screen.getByRole("columnheader", { name: "Net revenue" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "₹1,500" })).toBeInTheDocument();
  });

  it("right-aligns number columns and draws in-cell bars", () => {
    render(
      <DataTable
        columns={["city", "customers", "net_revenue"]}
        rows={[["Mumbai", 100, 4000], ["Pune", 50, null]]}
        bars={["customers", "net_revenue"]}
      />,
    );
    expect(screen.getByRole("columnheader", { name: "Customers" })).toHaveClass("num");
    expect(screen.getByRole("columnheader", { name: "City" })).not.toHaveClass("num");
    expect(screen.getByRole("cell", { name: "50" })).toHaveStyle({ "--bar": "0.5" });
    expect(screen.getByRole("cell", { name: "₹4,000" })).toHaveAttribute("data-money");
    expect(screen.getByRole("cell", { name: "50" })).not.toHaveAttribute("data-money");
    expect(screen.getByRole("cell", { name: "–" })).not.toHaveClass("bar-cell");
  });

  it("says when there are no rows", () => {
    render(<DataTable columns={["city"]} rows={[]} />);
    expect(screen.getByText("No rows matched.")).toBeInTheDocument();
  });
});

describe("Chart", () => {
  it.each(["bar", "line"])("draws a %s chart and keeps the data table", (type) => {
    const { container } = render(<Chart spec={{ type, x: "city", y: "repeat_buyers" }} columns={columns} rows={rows} />);
    expect(container.querySelector(".recharts-responsive-container")).not.toBeNull();
    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("shows a single value as a number", () => {
    render(<Chart spec={{ type: "number", x: null, y: "net_revenue" }} columns={["net_revenue"]} rows={[[125000]]} />);
    expect(screen.getByText("₹1,25,000")).toHaveClass("big-number");
  });

  it("falls back to a table", () => {
    const { container } = render(<Chart spec={{ type: "table", x: null, y: null }} columns={columns} rows={rows} />);
    expect(container.querySelector(".recharts-responsive-container")).toBeNull();
    expect(screen.getByRole("cell", { name: "Mumbai" })).toBeInTheDocument();
  });

  it("uses a table when a number answer has several rows", () => {
    render(<Chart spec={{ type: "number", x: null, y: "repeat_buyers" }} columns={columns} rows={rows} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
  });
});

describe("CohortGrid", () => {
  it("lays out cohorts by month with retention cells", () => {
    render(<CohortGrid rows={cohorts} />);
    expect(screen.getByRole("rowheader", { name: /Sep 2026/ })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: /Oct 2026/ })).toBeInTheDocument();
    expect(screen.getByTitle("Sep 2026 cohort, month 1: 120 of 500 customers")).toHaveTextContent("24%");
    expect(screen.getAllByText("100%")).toHaveLength(2);
  });
});

describe("Status", () => {
  it("shows loading and errors", () => {
    render(<><Loading /><ErrorNote message="Database unavailable" /></>);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    expect(screen.getByRole("alert")).toHaveTextContent("Database unavailable");
  });
});
