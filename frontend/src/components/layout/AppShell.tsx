import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../../context/AuthContext";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();

  return (
    <div className="min-h-screen bg-surface-page">
      <header className="h-14 border-b border-border-default bg-surface-white">
        <div className="mx-auto flex h-full w-full max-w-[1100px] items-center justify-between px-5 md:px-10">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-3">
              <div className="text-xl">
                <span className="font-light text-brand-blue">D</span>
                <span className="font-semibold text-brand-gold">P</span>
              </div>
              <span className="text-[15px] font-medium text-ink-primary md:inline">DProtein</span>
            </Link>

            <nav className="hidden items-center gap-2 md:flex">
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  `rounded-button px-3 py-1.5 text-sm transition ${
                    isActive
                      ? "bg-brand-blue text-white"
                      : "text-ink-2 hover:bg-brand-blue-tint hover:text-brand-blue"
                  }`
                }
              >
                Home
              </NavLink>
              <NavLink
                to="/tracker"
                className={({ isActive }) =>
                  `rounded-button px-3 py-1.5 text-sm transition ${
                    isActive
                      ? "bg-brand-blue text-white"
                      : "text-ink-2 hover:bg-brand-blue-tint hover:text-brand-blue"
                  }`
                }
              >
                Tracker
              </NavLink>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            {loading ? (
              <span className="text-sm text-ink-3">Checking session...</span>
            ) : user ? (
              <>
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-pill bg-brand-blue text-[12px] font-medium text-white">
                    {user.email.slice(0, 1).toUpperCase()}
                  </div>
                  <span className="hidden text-sm text-ink-2 md:inline">{user.email}</span>
                </div>
                <button
                  type="button"
                  onClick={() => void logout()}
                  className="rounded-button border border-border-default px-3 py-1.5 text-sm text-ink-2 transition hover:border-brand-blue hover:text-brand-blue"
                >
                  Log out
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="text-sm font-medium text-brand-blue underline-offset-4 transition hover:underline"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[980px] px-5 py-10 md:px-10">{children}</main>
    </div>
  );
}
