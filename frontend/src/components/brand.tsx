export function BrandMark({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 44"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M20 3 35 10v12c0 10-10 16-15 19C15 38 5 32 5 22V10L20 3Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path
        d="m14 17 6-4 6 4v8l-6 4-6-4v-8Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path
        d="M20 13v16M14 17l12 8M26 17l-12 8"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <circle cx="20" cy="21" r="3" fill="currentColor" />
    </svg>
  );
}
export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <span className="brand">
      <BrandMark className="brand-mark" />
      {!compact && (
        <span>
          Cyber<span className="brand-light">Sage</span>
          <small>INTELLIGENCE WORKSPACE</small>
        </span>
      )}
    </span>
  );
}
