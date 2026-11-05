import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useApi } from "../../useApi";
import { mockFetch, reply } from "../fixtures";

describe("useApi", () => {
  it("loads data", async () => {
    mockFetch({ "/x": { n: 1 } });
    const { result } = renderHook(() => useApi("/x"));
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.data).toEqual({ n: 1 }));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("reports errors and can retry", async () => {
    let calls = 0;
    mockFetch({ "/x": () => (++calls === 1 ? reply(503, { detail: "Database unavailable" }) : { n: 2 }) });
    const { result } = renderHook(() => useApi("/x"));
    await waitFor(() => expect(result.current.error).toBe("Database unavailable"));
    act(() => result.current.reload());
    await waitFor(() => expect(result.current.data).toEqual({ n: 2 }));
    expect(result.current.error).toBeNull();
  });

  it("refetches when the path changes", async () => {
    mockFetch({ "/a": { v: "a" }, "/b": { v: "b" } });
    const { result, rerender } = renderHook(({ path }) => useApi(path), { initialProps: { path: "/a" } });
    await waitFor(() => expect(result.current.data).toEqual({ v: "a" }));
    rerender({ path: "/b" });
    await waitFor(() => expect(result.current.data).toEqual({ v: "b" }));
  });
});
