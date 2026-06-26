import { DeadlineAlertsSection } from "@/components/dashboard/DeadlineAlertsSection";
import { ProfileCompletenessCard } from "@/components/dashboard/ProfileCompletenessCard";
import { RecentActivitySection } from "@/components/dashboard/RecentActivitySection";
import { SavedSchemesSection } from "@/components/dashboard/SavedSchemesSection";
import { TopMatchesSection } from "@/components/dashboard/TopMatchesSection";
import { WelcomeBanner } from "@/components/dashboard/WelcomeBanner";
import { useProfileStore } from "@/store/profileStore";

export function DashboardPage() {
  const profile = useProfileStore((state) => state.profile);
  const isProfileLoading = useProfileStore((state) => state.isLoading);

  return (
    <div className="space-y-6">
      <WelcomeBanner fullName={profile?.full_name} />

      <div className="grid gap-4 lg:grid-cols-3">
        <ProfileCompletenessCard profile={profile} isLoading={isProfileLoading} />
        <DeadlineAlertsSection />
        <SavedSchemesSection />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <TopMatchesSection />
        <RecentActivitySection />
      </div>
    </div>
  );
}
