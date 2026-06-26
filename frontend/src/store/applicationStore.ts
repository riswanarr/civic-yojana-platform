import { create } from "zustand";

type ApplicationState = {
  isLoading: boolean;
};

export const useApplicationStore = create<ApplicationState>(() => ({
  isLoading: false
}));

