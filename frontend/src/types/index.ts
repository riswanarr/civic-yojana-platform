export type LanguageCode = "en" | "hi" | "ml";

export type Profile = {
  id: string;
  user_id: string;
  full_name: string;
  state: string;
  age: number;
  gender: string | null;
  education_level: string;
  occupation: string;
  annual_family_income: number;
  category: string;
  disability_status: boolean;
  minority_status: boolean;
  profile_completed: boolean;
  created_at: string;
  updated_at: string;
};

export type ProfileInput = {
  user_id: string;
  full_name: string;
  state: string;
  age: number;
  gender?: string | null;
  education_level: string;
  occupation: string;
  annual_family_income: number;
  category: string;
  disability_status: boolean;
  minority_status: boolean;
  profile_completed: boolean;
};
