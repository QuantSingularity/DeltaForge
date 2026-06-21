// The DeltaForge wordmark and ember triangle. Shared across the homepage,
// auth screens and the dashboard header so the brand stays consistent.
export default function Brand({ size = 26, subtitle = "Trading Operations" }) {
  const mark = (
    <div className="flex items-center gap-2.5">
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        aria-hidden
      >
        <path
          d="M6 24 L16 4 L26 24 Z"
          stroke="#ff7a18"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <path d="M11 24 L16 14 L21 24 Z" fill="#ff7a18" opacity="0.85" />
      </svg>
      <div className="leading-none">
        <div className="text-[15px] font-bold tracking-tight">
          Delta<span className="text-ember">Forge</span>
        </div>
        {subtitle ? (
          <div className="text-[9px] uppercase tracking-[0.22em] text-ink-faint mt-0.5">
            {subtitle}
          </div>
        ) : null}
      </div>
    </div>
  );
  return mark;
}
