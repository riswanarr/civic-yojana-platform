import { Link, Outlet } from "react-router-dom";

export function AppLayout() {
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
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

