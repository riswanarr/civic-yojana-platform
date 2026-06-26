import { create } from "zustand";
import { supabase } from "@/lib/supabase";
import type { Profile, ProfileInput } from "@/types";

type ProfileState = {
  profile: Profile | null;
  isLoaded: boolean;
  isLoading: boolean;
  error: string | null;
  fetchProfile: (userId: string) => Promise<void>;
  saveProfile: (profile: ProfileInput) => Promise<void>;
  resetProfile: () => void;
  clearError: () => void;
};

export const useProfileStore = create<ProfileState>((set) => ({
  profile: null,
  isLoaded: false,
  isLoading: false,
  error: null,

  fetchProfile: async (userId) => {
    set({ isLoading: true, error: null });

    const { data, error } = await supabase
      .from("profiles")
      .select("*")
      .eq("user_id", userId)
      .maybeSingle();

    if (error) {
      set({ profile: null, isLoaded: true, isLoading: false, error: error.message });
      return;
    }

    set({ profile: data, isLoaded: true, isLoading: false, error: null });
  },

  saveProfile: async (profileInput) => {
    set({ isLoading: true, error: null });

    const { data, error } = await supabase
      .from("profiles")
      .upsert(profileInput, { onConflict: "user_id" })
      .select("*")
      .single();

    if (error) {
      set({ isLoading: false, error: error.message });
      return;
    }

    set({ profile: data, isLoaded: true, isLoading: false, error: null });
  },

  resetProfile: () => {
    set({ profile: null, isLoaded: false, isLoading: false, error: null });
  },

  clearError: () => {
    set({ error: null });
  }
}));
