import CohortGrid from "../components/CohortGrid";
import DataTable from "../components/DataTable";
import { Async } from "../components/Status";
import { useApi } from "../useApi";

export default function Customers() {
  const segments = useApi("/api/v1/segments");
  const cohorts = useApi("/api/v1/cohorts?months=12");
  return (
    <section>
      <h1>Customers</h1>
      <h2>RFM segments</h2>
      <p className="lede">
        Customers scored on how recently they ordered, how often, and how much they spent.
      </p>
      <Async result={segments}>
        {(rows) => (
          <DataTable
            columns={["segment", "customers", "net_revenue", "avg_recency_days", "avg_orders"]}
            bars={["customers"]}
            labels={{ avg_recency_days: "Days since last order", avg_orders: "Orders per customer" }}
            rows={rows.map((r) => [r.segment, r.customers, r.net_revenue, r.avg_recency_days, r.avg_orders])}
          />
        )}
      </Async>
      <h2>Monthly retention</h2>
      <p className="lede">
        Each row is the group of customers who first ordered that month; each cell is the share who
        ordered again M months later.
      </p>
      <Async result={cohorts}>{(rows) => <CohortGrid rows={rows} />}</Async>
    </section>
  );
}
