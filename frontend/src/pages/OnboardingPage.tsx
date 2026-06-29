import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { useProfileStore } from "@/store/profileStore";

export function OnboardingPage() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const profile = useProfileStore((state) => state.profile);
  const error = useProfileStore((state) => state.error);
  const isLoading = useProfileStore((state) => state.isLoading);
  const clearError = useProfileStore((state) => state.clearError);
  const saveProfile = useProfileStore((state) => state.saveProfile);

  const [fullName, setFullName] = useState("");
  const [state, setState] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [educationLevel, setEducationLevel] = useState("");
  const [occupation, setOccupation] = useState("");
  const [annualFamilyIncome, setAnnualFamilyIncome] = useState("");
  const [category, setCategory] = useState("");
  const [disabilityStatus, setDisabilityStatus] = useState(false);
  const [minorityStatus, setMinorityStatus] = useState(false);

  const GENDER_OPTIONS = [
    "Male",
    "Female",
    "Other",
    "Prefer not to say",
  ];

  const EDUCATION_OPTIONS = [
    "10th Pass",
    "12th Pass",
    "Diploma",
    "ITI",
    "Undergraduate (B.A/B.Sc/B.Com)",
    "Engineering Undergraduate (B.Tech/B.E)",
    "Postgraduate (M.A/M.Sc/M.Com)",
    "Engineering Postgraduate (M.Tech/M.E)",
    "PhD",
    "Other",
  ];

  const OCCUPATION_OPTIONS = [
    "Student",
    "Employed",
    "Self-Employed",
    "Job Seeker",
    "Entrepreneur",
    "Farmer",
    "Homemaker",
    "Retired",
    "Other",
  ];

  const CATEGORY_OPTIONS = [
    "General",
    "OBC",
    "SC",
    "ST",
    "EWS",
    "Other",
  ];

  const STATE_OPTIONS = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Puducherry",
    "Chandigarh",
    "Andaman and Nicobar Islands",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Lakshadweep",
  ];

  useEffect(() => {
    clearError();
  }, [clearError]);

  useEffect(() => {
    if (profile?.profile_completed) {
      navigate("/dashboard", { replace: true });
    }
  }, [navigate, profile?.profile_completed]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!user) {
      return;
    }

    await saveProfile({
      user_id: user.id,
      full_name: fullName,
      state,
      age: Number(age),
      gender: gender || null,
      education_level: educationLevel,
      occupation,
      annual_family_income: Number(annualFamilyIncome),
      category,
      disability_status: disabilityStatus,
      minority_status: minorityStatus,
      profile_completed: true,
    });
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-4 py-8">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">
            Complete your profile
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            This information helps personalize your dashboard.
          </p>
        </div>

        <form
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={handleSubmit}
        >
          <label className="block space-y-2 text-sm sm:col-span-2">
            <span>Full Name</span>
            <input
              className="w-full rounded-md border px-3 py-2"
              value={fullName}
              onChange={(event) =>
                setFullName(event.target.value)
              }
              required
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span>State</span>
            <select
              className="w-full rounded-md border px-3 py-2"
              value={state}
              onChange={(event) =>
                setState(event.target.value)
              }
              required
            >
              <option value="">
                Select state
              </option>

              {STATE_OPTIONS.map((option) => (
                <option
                  key={option}
                  value={option}
                >
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="block space-y-2 text-sm">
            <span>Age</span>
            <input
              className="w-full rounded-md border px-3 py-2"
              type="number"
              min="1"
              value={age}
              onChange={(event) =>
                setAge(event.target.value)
              }
              required
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span>Gender</span>
            <select
              className="w-full rounded-md border px-3 py-2"
              value={gender}
              onChange={(event) =>
                setGender(event.target.value)
              }
            >
              <option value="">
                Select gender
              </option>

              {GENDER_OPTIONS.map((option) => (
                <option
                  key={option}
                  value={option}
                >
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="block space-y-2 text-sm">
            <span>Education Level</span>
            <select
              className="w-full rounded-md border px-3 py-2"
              value={educationLevel}
              onChange={(event) =>
                setEducationLevel(
                  event.target.value
                )
              }
              required
            >
              <option value="">
                Select education level
              </option>

              {EDUCATION_OPTIONS.map(
                (option) => (
                  <option
                    key={option}
                    value={option}
                  >
                    {option}
                  </option>
                )
              )}
            </select>
          </label>

          <label className="block space-y-2 text-sm">
            <span>Occupation</span>
            <select
              className="w-full rounded-md border px-3 py-2"
              value={occupation}
              onChange={(event) =>
                setOccupation(
                  event.target.value
                )
              }
              required
            >
              <option value="">
                Select occupation
              </option>

              {OCCUPATION_OPTIONS.map(
                (option) => (
                  <option
                    key={option}
                    value={option}
                  >
                    {option}
                  </option>
                )
              )}
            </select>
          </label>

          <label className="block space-y-2 text-sm">
            <span>
              Annual Family Income (in Lakhs)
            </span>
            <input
              className="w-full rounded-md border px-3 py-2"
              type="number"
              min="0"
              step="0.1"
              placeholder="Example: 2.5"
              value={annualFamilyIncome}
              onChange={(event) =>
                setAnnualFamilyIncome(
                  event.target.value
                )
              }
              required
            />
          </label>

          <label className="block space-y-2 text-sm sm:col-span-2">
            <span>Category</span>
            <select
              className="w-full rounded-md border px-3 py-2"
              value={category}
              onChange={(event) =>
                setCategory(
                  event.target.value
                )
              }
              required
            >
              <option value="">
                Select category
              </option>

              {CATEGORY_OPTIONS.map(
                (option) => (
                  <option
                    key={option}
                    value={option}
                  >
                    {option}
                  </option>
                )
              )}
            </select>
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={disabilityStatus}
              onChange={(event) =>
                setDisabilityStatus(
                  event.target.checked
                )
              }
            />
            <span>Disability Status</span>
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={minorityStatus}
              onChange={(event) =>
                setMinorityStatus(
                  event.target.checked
                )
              }
            />
            <span>Minority Status</span>
          </label>

          {error ? (
            <p className="text-sm text-destructive sm:col-span-2">
              {error}
            </p>
          ) : null}

          <button
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60 sm:col-span-2"
            type="submit"
            disabled={isLoading}
          >
            {isLoading
              ? "Saving..."
              : "Complete Profile"}
          </button>
        </form>
      </div>
    </main>
  );
}