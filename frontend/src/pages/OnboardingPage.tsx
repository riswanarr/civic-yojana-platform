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
      profile_completed: true
    });
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-4 py-8">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Complete your profile</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            This information helps personalize your dashboard.
          </p>
        </div>

        <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleSubmit}>
          <label className="block space-y-2 text-sm sm:col-span-2">
            <span>Full Name</span>
            <input
              className="w-full rounded-md border px-3 py-2"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              required
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span>State</span>
            <input
              className="w-full rounded-md border px-3 py-2"
              value={state}
              onChange={(event) => setState(event.target.value)}
              required
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span>Age</span>
            <input
              className="w-full rounded-md border px-3 py-2"
              type="number"
              min="1"
              value={age}
              onChange={(event) => setAge(event.target.value)}
              required
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span>Gender</span>
            <input
              className="w-full rounded-md border px-3 py-2"
              value={gender}
              onChange={(event) => setGender(event.target.value)}
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span>Education Level</span>
            <input
              className="w-full rounded-md border px-3 py-2"
              value={educationLevel}
              onChange={(event) => setEducationLevel(event.target.value)}
              required
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span>Occupation</span>
            <input
              className="w-full rounded-md border px-3 py-2"
              value={occupation}
              onChange={(event) => setOccupation(event.target.value)}
              required
            />
          </label>

          <label className="block space-y-2 text-sm">
            <span>Annual Family Income</span>
            <input
              className="w-full rounded-md border px-3 py-2"
              type="number"
              min="0"
              value={annualFamilyIncome}
              onChange={(event) => setAnnualFamilyIncome(event.target.value)}
              required
            />
          </label>

          <label className="block space-y-2 text-sm sm:col-span-2">
            <span>Category</span>
            <input
              className="w-full rounded-md border px-3 py-2"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              required
            />
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={disabilityStatus}
              onChange={(event) => setDisabilityStatus(event.target.checked)}
            />
            <span>Disability Status</span>
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={minorityStatus}
              onChange={(event) => setMinorityStatus(event.target.checked)}
            />
            <span>Minority Status</span>
          </label>

          {error ? <p className="text-sm text-destructive sm:col-span-2">{error}</p> : null}

          <button
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60 sm:col-span-2"
            type="submit"
            disabled={isLoading}
          >
            {isLoading ? "Saving..." : "Complete Profile"}
          </button>
        </form>
      </div>
    </main>
  );
}
