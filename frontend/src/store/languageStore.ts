import { create } from "zustand";

type LanguageCode = "en" | "hi" | "ml";

type LanguageState = {
  language: LanguageCode;
};

export const useLanguageStore = create<LanguageState>(() => ({
  language: "en"
}));

