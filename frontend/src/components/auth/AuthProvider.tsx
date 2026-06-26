import { useEffect } from "react";
import type { ReactNode } from "react";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/store/authStore";

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const initializeAuth = useAuthStore((state) => state.initializeAuth);
  const setSession = useAuthStore((state) => state.setSession);

  useEffect(() => {
    void initializeAuth();

    const {
      data: { subscription }
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [initializeAuth, setSession]);

  return children;
}
