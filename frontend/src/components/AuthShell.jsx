import { Link } from "react-router-dom";
import Brand from "./Brand";

// Centered card used by the sign-in and sign-up screens.
export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="min-h-screen flex flex-col">
      <div className="w-full max-w-6xl mx-auto px-5 py-4">
        <Link to="/" className="inline-block">
          <Brand subtitle="Trading Operations" />
        </Link>
      </div>
      <div className="flex-1 flex items-center justify-center px-5 pb-16">
        <div className="w-full max-w-sm">
          <div className="panel p-7">
            <h1 className="text-xl font-bold tracking-tight">{title}</h1>
            {subtitle ? (
              <p className="mt-1.5 text-sm text-ink-muted">{subtitle}</p>
            ) : null}
            <div className="mt-6">{children}</div>
          </div>
          {footer ? (
            <div className="mt-4 text-center text-sm text-ink-muted">
              {footer}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
