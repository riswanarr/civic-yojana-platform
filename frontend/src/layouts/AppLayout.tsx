import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

export function AppLayout() {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const isLoading = useAuthStore((state) => state.isLoading);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <nav className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3 text-sm">
          <Link className="font-semibold" to="/">
            Schemes Discovery
          </Link>
          <Link to="/schemes">Schemes</Link>
          <Link to="/applications">Applications</Link>
          <Link to="/chatbot">Chatbot</Link>
          <Link to="/profile">Profile</Link>
          <button
            className="ml-auto text-sm font-medium text-primary disabled:opacity-60"
            type="button"
            onClick={handleLogout}
            disabled={isLoading}
          >
            {isLoading ? "Logging out..." : "Logout"}
          </button>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
