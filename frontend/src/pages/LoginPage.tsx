import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

type LocationState = {
  from?: {
    pathname?: string;
  };
};

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as LocationState | null;
  const redirectTo = locationState?.from?.pathname ?? "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const error = useAuthStore((state) => state.error);
  const clearError = useAuthStore((state) => state.clearError);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLoading = useAuthStore((state) => state.isLoading);
  const login = useAuthStore((state) => state.login);

  useEffect(() => {
    clearError();
  }, [clearError]);

  useEffect(() => {
    if (isAuthenticated) {
      navigate(redirectTo, { replace: true });
    }
  }, [isAuthenticated, navigate, redirectTo]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await login(email, password);
  }

  return (
    <main className="mandala-soft flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6 rounded-2xl border bg-card/90 p-6 shadow-xl">
        <div>
          <p className="brand-wordmark mb-4 text-xl">
            <span className="text-primary">civic-</span>
            <span className="text-accent">योजना</span>
          </p>
          <h1 className="text-2xl font-semibold">Login</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Access your civic opportunity dashboard.
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block space-y-2 text-sm">
            <span>Email</span>
            <input
              className="w-full rounded-xl border bg-background/70 px-3 py-2 outline-none focus:border-primary"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span>Password</span>
            <input
              className="w-full rounded-xl border bg-background/70 px-3 py-2 outline-none focus:border-primary"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          <button
            className="w-full rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:opacity-60"
            type="submit"
            disabled={isLoading}
          >
            {isLoading ? "Logging in..." : "Login"}
          </button>
        </form>

        <p className="text-sm text-muted-foreground">
          New here?{" "}
          <Link className="font-medium text-primary" to="/register">
            Create an account
          </Link>
        </p>
      </div>
    </main>
  );
}
