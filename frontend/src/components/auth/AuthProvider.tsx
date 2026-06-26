import { useEffect } from "react";
import type { ReactNode } from "react";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/store/authStore";
import { useProfileStore } from "@/store/profileStore";

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const initializeAuth = useAuthStore((state) => state.initializeAuth);
  const setSession = useAuthStore((state) => state.setSession);
  const resetProfile = useProfileStore((state) => state.resetProfile);

  useEffect(() => {
    void initializeAuth();

    const {
      data: { subscription }
    } = supabase.auth.onAuthStateChange((_event, session) => {
      resetProfile();
      setSession(session);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [initializeAuth, resetProfile, setSession]);

  return children;
}
