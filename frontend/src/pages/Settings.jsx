import { useOutletContext } from "react-router-dom";
import ConfigEditor from "../components/ConfigEditor";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../auth/AuthContext";

function AccountCard() {
  const { user } = useAuth();
  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="text-sm font-semibold">Account</h2>
        <span className="eyebrow">signed in</span>
      </div>
      <div className="p-4 space-y-3 text-sm">
        <div className="flex justify-between">
          <span className="text-ink-muted">Name</span>
          <span>{user?.name || "-"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-ink-muted">Email</span>
          <span className="font-mono text-xs">{user?.email || "-"}</span>
        </div>
      </div>
    </section>
  );
}

function StatusCard() {
  const { state } = useOutletContext();
  const status = state?.status || {};
  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="text-sm font-semibold">Runtime</h2>
        <span className="eyebrow">live</span>
      </div>
      <div className="p-4 space-y-3 text-sm">
        <div className="flex justify-between">
          <span className="text-ink-muted">Mode</span>
          <span className="uppercase">{status.mode || "sandbox"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-ink-muted">Exchange</span>
          <span>{status.exchange || "-"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-ink-muted">Bot</span>
          <span className={status.bot_running ? "text-buy" : "text-ink-faint"}>
            {status.bot_running ? "running" : "stopped"}
          </span>
        </div>
      </div>
    </section>
  );
}

export default function Settings() {
  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Bot configuration hot-reloads on save. Account and runtime details below."
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ConfigEditor />
        <div className="space-y-4">
          <AccountCard />
          <StatusCard />
        </div>
      </div>
    </div>
  );
}
