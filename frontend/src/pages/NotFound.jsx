import { Link } from "react-router-dom";
import Brand from "../components/Brand";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-5 text-center">
      <Brand subtitle="Trading Operations" />
      <div className="mt-10 text-6xl font-bold text-ember">404</div>
      <p className="mt-3 text-ink-muted">
        That page is not on the desk. It may have been moved or never existed.
      </p>
      <Link
        to="/"
        className="mt-7 px-5 py-2.5 rounded-lg text-sm font-semibold border border-ember/50 text-ember hover:bg-ember/10 transition-colors"
      >
        Back to home
      </Link>
    </div>
  );
}
