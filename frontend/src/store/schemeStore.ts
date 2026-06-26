import { create } from "zustand";
import { apiClient } from "@/services/apiClient";
import { useAuthStore } from "@/store/authStore";
import type { Scheme, SchemeFilters, SchemeListResponse } from "@/types";

type SchemeState = {
  schemes: Scheme[];
  selectedScheme: Scheme | null;
  page: number;
  pageSize: number;
  total: number;
  isLoading: boolean;
  isDetailLoading: boolean;
  error: string | null;
  fetchSchemes: (filters?: SchemeFilters) => Promise<void>;
  fetchScheme: (schemeId: string) => Promise<void>;
  clearSelectedScheme: () => void;
  clearError: () => void;
};

function buildSchemeQuery(filters: SchemeFilters = {}) {
  const params = new URLSearchParams();

  if (filters.search?.trim()) params.set("search", filters.search.trim());
  if (filters.state?.trim()) params.set("state", filters.state.trim());
  if (filters.category?.trim()) params.set("category", filters.category.trim());
  if (filters.ministry?.trim()) params.set("ministry", filters.ministry.trim());
  params.set("page", String(filters.page ?? 1));
  params.set("page_size", String(filters.pageSize ?? 12));

  return params.toString();
}

export const useSchemeStore = create<SchemeState>((set) => ({
  schemes: [],
  selectedScheme: null,
  page: 1,
  pageSize: 12,
  total: 0,
  isLoading: false,
  isDetailLoading: false,
  error: null,

  fetchSchemes: async (filters = {}) => {
    set({ isLoading: true, error: null });

    try {
      const accessToken = useAuthStore.getState().session?.access_token;
      const query = buildSchemeQuery(filters);
      const data = await apiClient.get<SchemeListResponse>(`/schemes?${query}`, accessToken);

      set({
        schemes: data.items,
        page: data.page,
        pageSize: data.page_size,
        total: data.total,
        isLoading: false,
        error: null
      });
    } catch (error) {
      set({
        schemes: [],
        isLoading: false,
        error: error instanceof Error ? error.message : "Unable to load schemes."
      });
    }
  },

  fetchScheme: async (schemeId) => {
    set({ selectedScheme: null, isDetailLoading: true, error: null });

    try {
      const accessToken = useAuthStore.getState().session?.access_token;
      const data = await apiClient.get<Scheme>(`/schemes/${schemeId}`, accessToken);

      set({ selectedScheme: data, isDetailLoading: false, error: null });
    } catch (error) {
      set({
        selectedScheme: null,
        isDetailLoading: false,
        error: error instanceof Error ? error.message : "Unable to load scheme."
      });
    }
  },

  clearSelectedScheme: () => {
    set({ selectedScheme: null, isDetailLoading: false });
  },

  clearError: () => {
    set({ error: null });
  }
}));
