import { create } from "zustand";
import { apiClient } from "@/services/apiClient";
import { useAuthStore } from "@/store/authStore";
import type { Recommendation, RecommendationResponse } from "@/types";

type RecommendationState = {
  recommendations: Recommendation[];
  isLoading: boolean;
  error: string | null;
  fetchRecommendations: () => Promise<void>;
  resetRecommendations: () => void;
};

export const useRecommendationStore = create<RecommendationState>((set) => ({
  recommendations: [],
  isLoading: false,
  error: null,

  fetchRecommendations: async () => {

    const accessToken = useAuthStore.getState().session?.access_token;

    if (!accessToken) {
      set({ recommendations: [], isLoading: false, error: null });
      return;
    }

    set({ isLoading: true, error: null });

    try {
      const data = await apiClient.get<RecommendationResponse>("/recommendations", accessToken);
      set({ recommendations: data.recommendations, isLoading: false, error: null });
    } catch (error) {
      set({
        recommendations: [],
        isLoading: false,
        error: error instanceof Error ? error.message : "Unable to load recommendations."
      });
    }
  },

  resetRecommendations: () => {
    set({ recommendations: [], isLoading: false, error: null });
  }
}));
