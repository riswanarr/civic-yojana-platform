import { DashboardCard } from "@/components/dashboard/DashboardCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import type { Profile } from "@/types";

type ProfileCompletenessCardProps = {
  profile: Profile | null;
  isLoading?: boolean;
};

const REQUIRED_PROFILE_FIELDS: Array<keyof Profile> = [
  "full_name",
  "state",
  "age",
  "education_level",
  "occupation",
  "annual_family_income",
  "category"
];

export function ProfileCompletenessCard({ profile, isLoading = false }: ProfileCompletenessCardProps) {
  if (isLoading) {
    return (
      <DashboardCard title="Profile Completeness">
        <LoadingState rows={2} />
      </DashboardCard>
    );
  }

  if (!profile) {
    return (
      <DashboardCard title="Profile Completeness">
        <EmptyState message="Profile details are not available yet." />
      </DashboardCard>
    );
  }

  const completedFields = REQUIRED_PROFILE_FIELDS.filter((field) => Boolean(profile[field])).length;
  const completion = Math.round((completedFields / REQUIRED_PROFILE_FIELDS.length) * 100);

  return (
    <DashboardCard title="Profile Completeness" description="Keep this updated for better matches.">
      <div className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span>{completion}% complete</span>
          <span className="text-muted-foreground">
            {completedFields}/{REQUIRED_PROFILE_FIELDS.length} fields
          </span>
        </div>
        <div className="h-2 rounded-full bg-muted">
          <div className="h-2 rounded-full bg-primary" style={{ width: `${completion}%` }} />
        </div>
      </div>
    </DashboardCard>
  );
}

