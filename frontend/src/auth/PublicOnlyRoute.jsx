import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

// For routes that should not be shown to a signed-in user (sign-in, sign-up).
export default function PublicOnlyRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return children;
}
