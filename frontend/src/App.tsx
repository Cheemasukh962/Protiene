import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { useAuth } from "./context/AuthContext";
import { isGuestModeEnabled } from "./lib/guestModeStorage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import RoutePage from "./pages/RoutePage";
import SignupPage from "./pages/SignupPage";
import TrackerPage from "./pages/TrackerPage";

function PageLoadingState() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-page">
      <p className="text-sm text-ink-3">Loading session...</p>
    </div>
  );
}

function ProtectedAppRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <PageLoadingState />;
  }

  if (user || isGuestModeEnabled()) {
    return <AppShell>{children}</AppShell>;
  }

  return <Navigate to="/login" replace />;
}

function LoginRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return <PageLoadingState />;
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return <LoginPage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        path="/"
        element={
          <ProtectedAppRoute>
            <HomePage />
          </ProtectedAppRoute>
        }
      />
      <Route
        path="/route"
        element={
          <ProtectedAppRoute>
            <RoutePage />
          </ProtectedAppRoute>
        }
      />
      <Route
        path="/tracker"
        element={
          <ProtectedAppRoute>
            <TrackerPage />
          </ProtectedAppRoute>
        }
      />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
