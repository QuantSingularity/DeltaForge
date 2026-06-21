import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

// Wraps protected routes. While the session is being restored it shows a
// lightweight loader; unauthenticated users are sent to /signin and returned
// to their target after a successful login.
export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-ink-muted">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 rounded-full bg-ember pulse" />
          <span className="text-sm">Restoring session…</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate to="/signin" replace state={{ from: location.pathname }} />
    );
  }

  return children;
}
