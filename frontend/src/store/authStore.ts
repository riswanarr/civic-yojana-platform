import { create } from "zustand";

type AuthState = {
  isAuthenticated: boolean;
};

export const useAuthStore = create<AuthState>(() => ({
  isAuthenticated: false
}));

