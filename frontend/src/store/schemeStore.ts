import { create } from "zustand";

type SchemeState = {
  isLoading: boolean;
};

export const useSchemeStore = create<SchemeState>(() => ({
  isLoading: false
}));

