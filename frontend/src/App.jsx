import { Link, NavLink, Route, Routes, useLocation } from "react-router";
import CommandPalette from "./components/CommandPalette";
import { longDate } from "./format";
import Ask from "./pages/Ask";
import Customers from "./pages/Customers";
import Funnel from "./pages/Funnel";
import Overview from "./pages/Overview";
import Pipeline from "./pages/Pipeline";
import { useApi } from "./useApi";

const PAGES = [
  { path: "/", label: "Overview", hint: "Revenue, orders and top cities", element: <Overview /> },
  { path: "/customers", label: "Customers", hint: "RFM segments and retention", element: <Customers /> },
  { path: "/funnel", label: "Funnel", hint: "View to order conversion", element: <Funnel /> },
  { path: "/ask", label: "Ask your data", hint: "Questions in plain English", element: <Ask /> },
  { path: "/pipeline", label: "Pipeline", hint: "Runs, row counts and tests", element: <Pipeline /> },
];

function Freshness() {
  const { data, error } = useApi("/api/health");
  if (error) {
    return (
      <span className="freshness bad">
        <i className="pulse" aria-hidden="true" />
        API unreachable
      </span>
    );
  }
  if (!data?.data_through) return null;
  return (
    <span className="freshness">
      <i className="pulse" aria-hidden="true" />
      Data through {longDate(data.data_through)}
    </span>
  );
}

function NotFound() {
  return (
    <section>
      <h1>Page not found</h1>
      <p>
        <Link to="/">Go to the overview</Link>
      </p>
    </section>
  );
}

function Wordmark() {
  return (
    <Link to="/" className="wordmark" aria-label="CartLens home">
      <svg className="lens" viewBox="0 0 32 32" aria-hidden="true">
        <circle cx="14" cy="14" r="9" />
        <path d="M21 21l7 7" />
      </svg>
      <span>
        Cart<b>Lens</b>
      </span>
    </Link>
  );
}

export default function App() {
  const location = useLocation();
  return (
    <div className="shell">
      <header className="rail">
        <Wordmark />
        <CommandPalette items={PAGES} />
        <nav aria-label="Main">
          {PAGES.map((p) => (
            <NavLink key={p.path} to={p.path} end>
              {p.label}
            </NavLink>
          ))}
        </nav>
        <Freshness />
      </header>
      <main>
        <div key={location.pathname} className="page">
          <Routes>
            {PAGES.map((p) => (
              <Route key={p.path} path={p.path} element={p.element} />
            ))}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
