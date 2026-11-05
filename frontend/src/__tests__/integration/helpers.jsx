import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import App from "../../App";
import * as data from "../fixtures";
import { mockFetch } from "../fixtures";

export const allRoutes = {
  "/api/health": data.health,
  "/api/v1/kpis": data.kpis,
  "/api/v1/cities": data.cities,
  "/api/v1/funnel": data.funnel,
  "/api/v1/cohorts": data.cohorts,
  "/api/v1/segments": data.segments,
  "/api/v1/pipeline/runs": data.runs,
  "/api/v1/ask/examples": data.examples,
  "/api/v1/ask": data.answer,
};

export function renderApp(path = "/", routes = {}) {
  const fetchMock = mockFetch({ ...allRoutes, ...routes });
  const view = render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
  return { ...view, fetchMock };
}
