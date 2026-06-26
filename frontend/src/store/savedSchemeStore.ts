import { create } from "zustand";
import { apiClient } from "@/services/apiClient";
import { useAuthStore } from "@/store/authStore";
import type { SavedScheme, SavedSchemesResponse } from "@/types";

type SavedSchemeState = {
  savedSchemes: SavedScheme[];
  savedSchemeIds: Set<string>;
  isLoading: boolean;
  savingIds: Set<string>;
  error: string | null;
  fetchSavedSchemes: () => Promise<void>;
  saveScheme: (schemeId: string) => Promise<void>;
  unsaveScheme: (schemeId: string) => Promise<void>;
  resetSavedSchemes: () => void;
};

function getAccessToken() {
  return useAuthStore.getState().session?.access_token;
}

function buildSavedIds(schemes: SavedScheme[]) {
  return new Set(schemes.map((scheme) => scheme.id));
}

export const useSavedSchemeStore = create<SavedSchemeState>((set, get) => ({
  savedSchemes: [],
  savedSchemeIds: new Set(),
  isLoading: false,
  savingIds: new Set(),
  error: null,

  fetchSavedSchemes: async () => {
    const accessToken = getAccessToken();

    if (!accessToken) {
      set({ savedSchemes: [], savedSchemeIds: new Set(), isLoading: false, error: null });
      return;
    }

    set({ isLoading: true, error: null });

    try {
      const data = await apiClient.get<SavedSchemesResponse>("/saved-schemes", accessToken);
      const items = Array.isArray(data.items) ? data.items : [];
      set({
        savedSchemes: items,
        savedSchemeIds: buildSavedIds(items),
        isLoading: false,
        error: null
      });
    } catch (error) {
      set({
        savedSchemes: [],
        savedSchemeIds: new Set(),
        isLoading: false,
        error: error instanceof Error ? error.message : "Unable to load saved schemes."
      });
    }
  },

  saveScheme: async (schemeId) => {
    const accessToken = getAccessToken();

    if (!accessToken || get().savedSchemeIds.has(schemeId)) {
      return;
    }

    set((state) => ({ savingIds: new Set(state.savingIds).add(schemeId), error: null }));

    try {
      await apiClient.post("/saved-schemes", { scheme_id: schemeId }, accessToken);
      set((state) => {
        const savedSchemeIds = new Set(state.savedSchemeIds).add(schemeId);
        const savingIds = new Set(state.savingIds);
        savingIds.delete(schemeId);
        return { savedSchemeIds, savingIds, error: null };
      });
      await get().fetchSavedSchemes();
    } catch (error) {
      set((state) => {
        const savingIds = new Set(state.savingIds);
        savingIds.delete(schemeId);
        return {
          savingIds,
          error: error instanceof Error ? error.message : "Unable to save scheme."
        };
      });
    }
  },

  unsaveScheme: async (schemeId) => {
    const accessToken = getAccessToken();

    if (!accessToken) {
      return;
    }

    set((state) => ({ savingIds: new Set(state.savingIds).add(schemeId), error: null }));

    try {
      await apiClient.delete(`/saved-schemes/${schemeId}`, accessToken);
      set((state) => {
        const savedSchemeIds = new Set(state.savedSchemeIds);
        savedSchemeIds.delete(schemeId);
        const savingIds = new Set(state.savingIds);
        savingIds.delete(schemeId);
        return {
          savedSchemes: state.savedSchemes.filter((scheme) => scheme.id !== schemeId),
          savedSchemeIds,
          savingIds,
          error: null
        };
      });
    } catch (error) {
      set((state) => {
        const savingIds = new Set(state.savingIds);
        savingIds.delete(schemeId);
        return {
          savingIds,
          error: error instanceof Error ? error.message : "Unable to remove saved scheme."
        };
      });
    }
  },

  resetSavedSchemes: () => {
    set({ savedSchemes: [], savedSchemeIds: new Set(), isLoading: false, savingIds: new Set(), error: null });
  }
}));
