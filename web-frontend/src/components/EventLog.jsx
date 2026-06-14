import { ago, eventColor } from "../lib/format";

export default function EventLog({ state }) {
  const events = state?.events || [];

  return (
    <section className="panel flex flex-col">
      <div className="panel-head">
        <h2 className="text-sm font-semibold">Event log</h2>
        <span className="eyebrow">most recent first</span>
      </div>
      <div className="flex-1 overflow-y-auto max-h-72 px-1 py-1">
        {events.length === 0 && (
          <div className="text-ink-faint text-sm text-center py-6">
            No events yet.
          </div>
        )}
        {events.map((e, i) => (
          <div
            key={i}
            className="flex items-start gap-2 px-3 py-1.5 hover:bg-panel-850/40 rounded"
          >
            <span
              className={`text-[10px] font-mono font-semibold mt-0.5 w-16 shrink-0 ${eventColor(e.type)}`}
            >
              {e.type}
            </span>
            <span className="text-sm text-ink flex-1">{e.message}</span>
            <span className="text-[10px] font-mono text-ink-faint mt-0.5">
              {ago(e.ts)}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
