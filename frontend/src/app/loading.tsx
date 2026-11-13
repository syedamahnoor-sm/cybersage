export default function Loading() {
  return (
    <div className="loading-page" role="status">
      <span className="skeleton" />
      <span className="skeleton" />
      <span className="sr-only">Loading workspace…</span>
    </div>
  );
}
