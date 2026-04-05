import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../lib/api";
import { clearGuestMode, enableGuestMode } from "../lib/guestModeStorage";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isDisabled = useMemo(() => {
    return submitting || email.trim().length === 0 || password.length < 8;
  }, [submitting, email, password]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      clearGuestMode();
      navigate("/");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Unable to log in right now.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-surface-page md:grid md:grid-cols-5">
      <section className="flex min-h-[160px] flex-col justify-center bg-brand-blue px-6 py-10 text-white md:col-span-2 md:min-h-screen md:justify-start md:px-10 md:py-12">
        <div>
          <div className="text-[40px] leading-none">
            <span className="font-light">D</span>
            <span className="font-semibold text-brand-gold">P</span>
          </div>
          <p className="mt-6 text-base tracking-[0.04em] text-white/90">DProtein</p>
          <p className="mt-10 max-w-[280px] text-2xl font-light leading-tight">
            Find food that works for you.
          </p>
          <div className="mt-4 h-px w-8 bg-white/30" />
          <p className="mt-4 text-xs uppercase tracking-[0.06em] text-white/60">
            UC Davis - Protein Finder
          </p>
        </div>
      </section>

      <section className="flex items-center justify-center bg-surface-white px-5 py-10 md:col-span-3">
        <div className="w-full max-w-[360px]">
          <h1 className="text-[28px] font-semibold tracking-[-0.01em] text-ink-primary">Welcome back.</h1>

          <form onSubmit={(event) => void handleSubmit(event)} className="mt-8 space-y-4">
            <div>
              <label className="text-[12px] font-semibold uppercase tracking-[0.07em] text-ink-3">
                Email
              </label>
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                autoComplete="email"
                placeholder="you@ucdavis.edu"
                className="mt-2 h-12 w-full rounded-input border border-border-default px-3 text-[15px] text-ink-primary outline-none transition focus:border-2 focus:border-brand-blue"
              />
            </div>

            <div>
              <label className="text-[12px] font-semibold uppercase tracking-[0.07em] text-ink-3">
                Password
              </label>
              <div className="relative mt-2">
                <input
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="********"
                  className="h-12 w-full rounded-input border border-border-default px-3 pr-10 text-[15px] text-ink-primary outline-none transition focus:border-2 focus:border-brand-blue"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-ink-4"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            {error ? (
              <p className="rounded-input border border-status-error-text bg-status-error-bg px-3 py-2 text-sm text-status-error-text">
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={isDisabled}
              className="h-12 w-full rounded-button bg-brand-blue text-[15px] font-medium tracking-[0.01em] text-white transition hover:bg-brand-blue-mid disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submitting ? "Logging in..." : "Log In"}
            </button>
          </form>

          <button
            type="button"
            onClick={() => {
              enableGuestMode();
              navigate("/");
            }}
            className="mt-4 text-sm text-brand-blue underline-offset-4 transition hover:underline"
          >
            Continue as guest {"->"}
          </button>

          <p className="mt-12 text-sm text-ink-3">
            Don&apos;t have an account?{" "}
            <Link to="/signup" className="text-brand-blue underline-offset-4 transition hover:underline">
              Sign up {"->"}
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
