import { describe, expect, it } from "vitest";
import { API_URL, ApiError, getJson, postJson } from "../../api";
import { mockFetch, reply } from "../fixtures";

describe("api", () => {
  it("uses the local API by default", () => {
    expect(API_URL).toBe("http://localhost:8000");
  });

  it("gets JSON", async () => {
    const fetchMock = mockFetch({ "/api/health": { status: "ok" } });
    await expect(getJson("/api/health")).resolves.toEqual({ status: "ok" });
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/health");
  });

  it("posts JSON", async () => {
    const fetchMock = mockFetch({ "/api/v1/ask": (path, opts) => ({ echo: JSON.parse(opts.body) }) });
    await expect(postJson("/api/v1/ask", { question: "q" })).resolves.toEqual({ echo: { question: "q" } });
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(fetchMock.mock.calls[0][1].headers["Content-Type"]).toBe("application/json");
  });

  it("raises the API's error detail", async () => {
    mockFetch({ "/api/v1/ask": reply(422, { detail: "Table raw.events is not allowed." }) });
    const error = await postJson("/api/v1/ask", {}).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(422);
    expect(error.message).toBe("Table raw.events is not allowed.");
  });

  it("explains validation errors and bodies without detail", async () => {
    mockFetch({
      "/a": reply(422, { detail: [{ msg: "String should have at least 3 characters" }] }),
      "/b": reply(500, null),
    });
    await expect(getJson("/a")).rejects.toThrow("String should have at least 3 characters");
    await expect(getJson("/b")).rejects.toThrow("Request failed (500)");
  });

  it("explains network failures", async () => {
    mockFetch({});
    await expect(getJson("/api/health")).rejects.toThrow(/waking up/);
  });
});
