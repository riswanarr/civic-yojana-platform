import { useEffect, useState } from "react";
import { Bell, Bookmark, ClipboardList, LayoutDashboard, MessageCircle, Menu, Search, User, X } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { useNotificationStore } from "@/store/notificationStore";
import { useProfileStore } from "@/store/profileStore";
import { cn } from "@/lib/utils";

const SIDEBAR_ITEMS = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
  { label: "Explore Schemes", to: "/schemes", icon: Search },
  { label: "Saved Schemes", to: "/saved", icon: Bookmark },
  { label: "Applications", to: "/applications", icon: ClipboardList },
  { label: "Chat Assistant", to: "/chatbot", icon: MessageCircle },
  { label: "Profile", to: "/profile", icon: User }
];

function BrandMark() {
  return (
    <span className="brand-wordmark inline-flex items-baseline gap-0.5 text-lg">
      <span className="text-primary">civic-</span>
      <span className="text-accent">योजना</span>
    </span>
  );
}

function formatNotificationTime(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(date);
}

export function AppLayout() {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const user = useAuthStore((state) => state.user);
  const accessToken = useAuthStore((state) => state.session?.access_token);
  const logout = useAuthStore((state) => state.logout);
  const isLoading = useAuthStore((state) => state.isLoading);
  const profile = useProfileStore((state) => state.profile);
  const notifications = useNotificationStore((state) => state.notifications);
  const unreadCount = useNotificationStore((state) => state.unreadCount);
  const notificationError = useNotificationStore((state) => state.error);
  const fetchNotifications = useNotificationStore((state) => state.fetchNotifications);
  const markAsRead = useNotificationStore((state) => state.markAsRead);
  const resetNotifications = useNotificationStore((state) => state.resetNotifications);

  useEffect(() => {
    if (accessToken) {
      void fetchNotifications();
      return;
    }

    resetNotifications();
  }, [accessToken, fetchNotifications, resetNotifications]);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-background">
      <aside
        className={cn(
          "mandala-soft fixed inset-y-0 left-0 z-40 w-72 border-r bg-card/95 shadow-sm backdrop-blur transition-transform lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center justify-between border-b bg-card/80 px-4">
          <NavLink className="flex items-center gap-2" to="/dashboard" onClick={() => setSidebarOpen(false)}>
            <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-accent/30 via-card to-primary/20 text-sm font-bold text-primary shadow-sm">
              य
            </span>
            <BrandMark />
          </NavLink>
          <button
            className="rounded-lg p-2 text-muted-foreground hover:bg-secondary/70 hover:text-foreground lg:hidden"
            type="button"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="space-y-1 p-3">
          {SIDEBAR_ITEMS.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-muted-foreground transition hover:bg-secondary/70 hover:text-foreground",
                    isActive && "bg-primary text-primary-foreground shadow-sm"
                  )
                }
                key={item.to}
                to={item.to}
                onClick={() => setSidebarOpen(false)}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>

      {sidebarOpen ? (
        <button
          className="fixed inset-0 z-30 bg-foreground/20 backdrop-blur-sm lg:hidden"
          type="button"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation overlay"
        />
      ) : null}

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b bg-card/90 shadow-sm backdrop-blur">
          <nav className="flex h-16 items-center gap-3 px-4">
            <button
              className="rounded-lg p-2 text-muted-foreground hover:bg-secondary/70 hover:text-foreground lg:hidden"
              type="button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu className="h-5 w-5" />
            </button>

            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">
                <BrandMark />
              </p>
              <p className="truncate text-xs text-muted-foreground">Citizen opportunity dashboard</p>
            </div>

            <div className="ml-auto flex items-center gap-2">
              <details className="relative">
                <summary className="relative flex h-10 w-10 cursor-pointer list-none items-center justify-center rounded-xl border bg-card text-muted-foreground shadow-sm transition hover:border-accent/60 hover:text-foreground">
                  <Bell className="h-4 w-4" />
                  {unreadCount > 0 ? (
                    <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-semibold text-accent-foreground shadow-sm">
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                  ) : null}
                </summary>

                <div className="absolute right-0 mt-2 w-80 rounded-2xl border bg-card p-3 shadow-xl">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h2 className="text-sm font-semibold">Notifications</h2>
                    <span className="rounded-full bg-secondary px-2 py-1 text-xs font-medium text-muted-foreground">{unreadCount} unread</span>
                  </div>

                  {notificationError ? (
                    <div className="rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
                      {notificationError}
                    </div>
                  ) : null}

                  <div className="max-h-80 space-y-2 overflow-y-auto">
                    {notifications.length === 0 ? (
                      <p className="rounded-xl border border-dashed bg-secondary/40 p-3 text-sm text-muted-foreground">
                        No notifications yet.
                      </p>
                    ) : (
                      notifications.map((notification) => (
                        <button
                          className={cn(
                            "w-full rounded-md border p-3 text-left text-sm transition hover:border-primary/60",
                            notification.is_read ? "bg-card" : "bg-secondary/60"
                          )}
                          key={notification.id}
                          type="button"
                          onClick={() => void markAsRead(notification.id)}
                        >
                          <span className="flex items-start justify-between gap-3">
                            <span className="font-medium">{notification.title}</span>
                            {!notification.is_read ? (
                              <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" />
                            ) : null}
                          </span>
                          <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                            {notification.message}
                          </span>
                          <span className="mt-2 block text-[11px] text-muted-foreground">
                            {formatNotificationTime(notification.created_at)}
                          </span>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              </details>

              <details className="relative">
                <summary className="flex cursor-pointer list-none items-center gap-2 rounded-xl px-2 py-1.5 text-sm transition hover:bg-secondary/70">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/80 text-xs font-semibold text-primary-foreground shadow-sm">
                    {(profile?.full_name || user?.email || "U").charAt(0).toUpperCase()}
                  </span>
                  <span className="hidden max-w-36 truncate sm:inline">
                    {profile?.full_name || user?.email || "User"}
                  </span>
                </summary>
                <div className="absolute right-0 mt-2 w-64 rounded-2xl border bg-card p-3 shadow-xl">
                  <p className="truncate text-sm font-medium">{profile?.full_name || "User profile"}</p>
                  <p className="mt-1 truncate text-xs text-muted-foreground">{user?.email}</p>
                </div>
              </details>

              <button
                className="rounded-xl border bg-card px-3 py-2 text-sm font-medium shadow-sm transition hover:border-accent/60 hover:bg-secondary/50 disabled:opacity-60"
                type="button"
                onClick={handleLogout}
                disabled={isLoading}
              >
                {isLoading ? "Logging out..." : "Logout"}
              </button>
            </div>
          </nav>
        </header>

        <main className="px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
