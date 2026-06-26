import type { ReactNode } from "react";
import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { useProfileStore } from "@/store/profileStore";

type ProtectedRouteProps = {
  children: ReactNode;
  requireCompletedProfile?: boolean;
  redirectCompletedProfile?: boolean;
};

export function ProtectedRoute({
  children,
  requireCompletedProfile = true,
  redirectCompletedProfile = false
}: ProtectedRouteProps) {
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isAuthLoading = useAuthStore((state) => state.isLoading);
  const profile = useProfileStore((state) => state.profile);
  const isProfileLoaded = useProfileStore((state) => state.isLoaded);
  const isProfileLoading = useProfileStore((state) => state.isLoading);
  const fetchProfile = useProfileStore((state) => state.fetchProfile);

  useEffect(() => {
    if (isAuthenticated && user && !isProfileLoaded && !isProfileLoading) {
      void fetchProfile(user.id);
    }
  }, [fetchProfile, isAuthenticated, isProfileLoaded, isProfileLoading, user]);

  if (isAuthLoading || (isAuthenticated && !isProfileLoaded)) {
    return <div className="p-6 text-sm text-muted-foreground">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (redirectCompletedProfile && profile?.profile_completed) {
    return <Navigate to="/dashboard" replace />;
  }

  if (requireCompletedProfile && !profile?.profile_completed) {
    return <Navigate to="/onboarding" replace />;
  }

  return children;
}
