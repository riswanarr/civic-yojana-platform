import { create } from "zustand";

type ProfileState = {
  isLoaded: boolean;
};

export const useProfileStore = create<ProfileState>(() => ({
  isLoaded: false
}));

