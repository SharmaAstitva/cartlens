export function Loading({ label = "Loading" }) {
  return (
    <p className="status" role="status">
      {label}…
    </p>
  );
}

export function ErrorNote({ message, onRetry }) {
  return (
    <div className="error-note" role="alert">
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="button-quiet" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

/** Render loading / error / content for a useApi() result. */
export function Async({ result, children }) {
  if (result.error) return <ErrorNote message={result.error} onRetry={result.reload} />;
  if (result.loading && !result.data) return <Loading />;
  return children(result.data);
}
