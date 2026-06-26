import { useProfileStore } from "@/store/profileStore";

export function ProfilePage() {
  const profile = useProfileStore(
    (state) => state.profile
  );

  if (!profile) {
    return <p>No profile found.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">
          Profile
        </h1>

        <p className="text-sm text-muted-foreground">
          Your profile information.
        </p>
      </div>

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
          value={`₹${profile.annual_family_income}`}
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