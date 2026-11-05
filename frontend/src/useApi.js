import { useCallback, useEffect, useState } from "react";
import { getJson } from "./api";

/**
 * Fetch JSON from the API for a path; refetches when the path changes or reload() is called.
 * While a new request is in flight, the previous data stays visible.
 */
export function useApi(path) {
  const [attempt, setAttempt] = useState(0);
  const key = `${path}#${attempt}`;
  const [result, setResult] = useState({ key: null, data: null, error: null });

  useEffect(() => {
    const controller = new AbortController();
    getJson(path, { signal: controller.signal })
      .then((data) => setResult({ key, data, error: null }))
      .catch((err) => {
        if (!controller.signal.aborted) setResult({ key, data: null, error: err.message });
      });
    return () => controller.abort();
  }, [path, key]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  const current = result.key === key;
  return { data: result.data, error: current ? result.error : null, loading: !current, reload };
}
