import { create } from "zustand";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

type AuthState = {
  user: User | null;
  session: Session | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  initializeAuth: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setSession: (session: Session | null) => void;
  clearError: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  session: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,

  initializeAuth: async () => {
    set({ isLoading: true, error: null });

    const { data, error } = await supabase.auth.getSession();

    if (error) {
      set({
        user: null,
        session: null,
        isAuthenticated: false,
        isLoading: false,
        error: error.message
      });
      return;
    }

    set({
      user: data.session?.user ?? null,
      session: data.session,
      isAuthenticated: Boolean(data.session),
      isLoading: false,
      error: null
    });
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    });

    if (error) {
      set({ isLoading: false, error: error.message });
      return;
    }

    set({
      user: data.user,
      session: data.session,
      isAuthenticated: Boolean(data.session),
      isLoading: false,
      error: null
    });
  },

  register: async (email, password) => {
    set({ isLoading: true, error: null });

    const { data, error } = await supabase.auth.signUp({
      email,
      password
    });

    if (error) {
      set({ isLoading: false, error: error.message });
      return;
    }

    set({
      user: data.user,
      session: data.session,
      isAuthenticated: Boolean(data.session),
      isLoading: false,
      error: null
    });
  },

  logout: async () => {
    set({ isLoading: true, error: null });

    const { error } = await supabase.auth.signOut();

    if (error) {
      set({ isLoading: false, error: error.message });
      return;
    }

    set({
      user: null,
      session: null,
      isAuthenticated: false,
      isLoading: false,
      error: null
    });
  },

  setSession: (session) => {
    set({
      user: session?.user ?? null,
      session,
      isAuthenticated: Boolean(session),
      isLoading: false,
      error: null
    });
  },

  clearError: () => {
    set({ error: null });
  }
}));
