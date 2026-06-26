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

export type Scheme = {
  id: string;
  title: string;
  description: string;
  ministry: string | null;
  state: string | null;
  category: string;
  eligibility_criteria: string | null;
  benefits: string | null;
  application_link: string | null;
  official_source: string | null;
  deadline: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type SchemeListResponse = {
  items: Scheme[];
  page: number;
  page_size: number;
  total: number;
};

export type SavedScheme = Scheme & {
  saved_at?: string;
};

export type SavedSchemesResponse = {
  items: SavedScheme[];
};

export type SchemeFilters = {
  search?: string;
  state?: string;
  category?: string;
  ministry?: string;
  page?: number;
  pageSize?: number;
};

export type Recommendation = {
  scheme_id: string;
  title: string;
  score: number;
  reason: string;
};

export type RecommendationResponse = {
  recommendations: Recommendation[];
};
export type EligibilityResponse = {
  scheme_id: string;
  scheme_title: string;
  eligibility_score: number;
  status: string;
  matched_criteria: string[];
  missing_requirements: string[];
  reason: string;
};
