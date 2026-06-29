import { FormEvent, useEffect, useState } from "react";

import { useProfileStore } from "@/store/profileStore";

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

export function ProfilePage() {
  const profile = useProfileStore((state) => state.profile);
  const error = useProfileStore((state) => state.error);
  const isLoading = useProfileStore((state) => state.isLoading);
  const clearError = useProfileStore((state) => state.clearError);
  const saveProfile = useProfileStore((state) => state.saveProfile);

  const [isEditing, setIsEditing] = useState(false);
  const [state, setState] = useState("");
  const [gender, setGender] = useState("");
  const [educationLevel, setEducationLevel] = useState("");
  const [occupation, setOccupation] = useState("");
  const [annualFamilyIncome, setAnnualFamilyIncome] = useState("");
  const [category, setCategory] = useState("");
  const [disabilityStatus, setDisabilityStatus] = useState(false);
  const [minorityStatus, setMinorityStatus] = useState(false);

  function resetForm() {
    if (!profile) {
      return;
    }

    setState(profile.state);
    setGender(profile.gender ?? "");
    setEducationLevel(profile.education_level);
    setOccupation(profile.occupation);
    setAnnualFamilyIncome(String(profile.annual_family_income));
    setCategory(profile.category);
    setDisabilityStatus(profile.disability_status);
    setMinorityStatus(profile.minority_status);
  }

  useEffect(() => {
    resetForm();
  }, [profile]);

  function startEditing() {
    clearError();
    resetForm();
    setIsEditing(true);
  }

  function cancelEditing() {
    clearError();
    resetForm();
    setIsEditing(false);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!profile) {
      return;
    }

    await saveProfile({
      user_id: profile.user_id,
      full_name: profile.full_name,
      state,
      age: profile.age,
      gender: gender || null,
      education_level: educationLevel,
      occupation,
      annual_family_income: Number(annualFamilyIncome),
      category,
      disability_status: disabilityStatus,
      minority_status: minorityStatus,
      profile_completed: true,
    });

    if (!useProfileStore.getState().error) {
      setIsEditing(false);
    }
  }

  if (!profile) {
    return <p>No profile found.</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">
            Profile
          </h1>

          <p className="text-sm text-muted-foreground">
            Your profile information.
          </p>
        </div>

        {!isEditing ? (
          <button
            className="w-fit rounded-md border px-4 py-2 text-sm font-medium"
            type="button"
            onClick={startEditing}
          >
            Edit Profile
          </button>
        ) : null}
      </div>

      {error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {isEditing ? (
        <form
          className="grid gap-4 rounded-lg border p-4 md:grid-cols-2"
          onSubmit={handleSubmit}
        >
          <ProfileSelect
            label="State"
            options={STATE_OPTIONS}
            value={state}
            onChange={setState}
          />

          <ProfileSelect
            label="Gender"
            options={GENDER_OPTIONS}
            value={gender}
            onChange={setGender}
            placeholder="Select gender"
          />

          <ProfileSelect
            label="Education"
            options={EDUCATION_OPTIONS}
            value={educationLevel}
            onChange={setEducationLevel}
          />

          <ProfileSelect
            label="Occupation"
            options={OCCUPATION_OPTIONS}
            value={occupation}
            onChange={setOccupation}
          />

          <label className="block space-y-2 text-sm">
            <span>Annual Family Income</span>
            <input
              className="w-full rounded-md border px-3 py-2"
              min="0"
              step="0.1"
              type="number"
              value={annualFamilyIncome}
              onChange={(event) =>
                setAnnualFamilyIncome(event.target.value)
              }
              required
            />
          </label>

          <ProfileSelect
            label="Category"
            options={CATEGORY_OPTIONS}
            value={category}
            onChange={setCategory}
          />

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={disabilityStatus}
              onChange={(event) =>
                setDisabilityStatus(event.target.checked)
              }
            />
            <span>Disability Status</span>
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={minorityStatus}
              onChange={(event) =>
                setMinorityStatus(event.target.checked)
              }
            />
            <span>Minority Status</span>
          </label>

          <div className="flex gap-3 md:col-span-2">
            <button
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
              type="submit"
              disabled={isLoading}
            >
              {isLoading ? "Saving..." : "Save"}
            </button>

            <button
              className="rounded-md border px-4 py-2 text-sm font-medium disabled:opacity-60"
              type="button"
              onClick={cancelEditing}
              disabled={isLoading}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          <ProfileItem
            label="Full Name"
            value={profile.full_name}
          />

          <ProfileItem
            label="State"
            value={profile.state}
          />

          <ProfileItem
            label="Age"
            value={profile.age}
          />

          <ProfileItem
            label="Gender"
            value={profile.gender ?? "Not specified"}
          />

          <ProfileItem
            label="Education"
            value={profile.education_level}
          />

          <ProfileItem
            label="Occupation"
            value={profile.occupation}
          />

          <ProfileItem
            label="Annual Family Income"
            value={`Rs. ${profile.annual_family_income}`}
          />

          <ProfileItem
            label="Category"
            value={profile.category}
          />

          <ProfileItem
            label="Disability Status"
            value={
              profile.disability_status
                ? "Yes"
                : "No"
            }
          />

          <ProfileItem
            label="Minority Status"
            value={
              profile.minority_status
                ? "Yes"
                : "No"
            }
          />
        </div>
      )}
    </div>
  );
}

type ProfileItemProps = {
  label: string;
  value: string | number;
};

function ProfileItem({
  label,
  value,
}: ProfileItemProps) {
  return (
    <div className="rounded-lg border p-4">
      <p className="text-xs text-muted-foreground">
        {label}
      </p>

      <p className="mt-1 font-medium">
        {value}
      </p>
    </div>
  );
}

type ProfileSelectProps = {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
};

function ProfileSelect({
  label,
  options,
  value,
  onChange,
  placeholder,
}: ProfileSelectProps) {
  return (
    <label className="block space-y-2 text-sm">
      <span>{label}</span>
      <select
        className="w-full rounded-md border px-3 py-2"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={!placeholder}
      >
        {placeholder ? (
          <option value="">
            {placeholder}
          </option>
        ) : null}

        {options.map((option) => (
          <option
            key={option}
            value={option}
          >
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}
