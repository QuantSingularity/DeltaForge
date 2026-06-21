// Consistent page title block for the authenticated pages.
export default function PageHeader({ title, subtitle, children }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
      <div>
        <h1 className="text-lg font-bold tracking-tight">{title}</h1>
        {subtitle ? (
          <p className="text-sm text-ink-muted mt-0.5">{subtitle}</p>
        ) : null}
      </div>
      {children ? (
        <div className="flex items-center gap-2">{children}</div>
      ) : null}
    </div>
  );
}
