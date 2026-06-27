import { create } from "zustand";
import { apiClient } from "@/services/apiClient";
import { useAuthStore } from "@/store/authStore";
import type { Recommendation, RecommendationResponse } from "@/types";

type RecommendationState = {
  recommendations: Recommendation[];
  isLoading: boolean;
  error: string | null;
  loadedForToken: string | null;
  fetchRecommendations: () => Promise<void>;
  resetRecommendations: () => void;
};

export const useRecommendationStore = create<RecommendationState>((set, get) => ({
  recommendations: [],
  isLoading: false,
  error: null,
  loadedForToken: null,

  fetchRecommendations: async () => {
    const accessToken = useAuthStore.getState().session?.access_token;

    if (!accessToken) {
      set({ recommendations: [], isLoading: false, error: null, loadedForToken: null });
      return;
    }

    const { isLoading, loadedForToken } = get();
    if (isLoading || loadedForToken === accessToken) {
      return;
    }

    set({ isLoading: true, error: null });

    try {
      const data = await apiClient.get<RecommendationResponse>("/recommendations", accessToken);
      set({
        recommendations: Array.isArray(data.recommendations) ? data.recommendations : [],
        isLoading: false,
        error: null,
        loadedForToken: accessToken
      });
    } catch (error) {
      set({
        recommendations: [],
        isLoading: false,
        error: error instanceof Error ? error.message : "Unable to load recommendations.",
        loadedForToken: accessToken
      });
    }
  },

  resetRecommendations: () => {
    set({ recommendations: [], isLoading: false, error: null, loadedForToken: null });
  }
}));
