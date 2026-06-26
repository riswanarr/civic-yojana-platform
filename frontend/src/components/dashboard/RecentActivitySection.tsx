import { DashboardCard } from "@/components/dashboard/DashboardCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { LoadingState } from "@/components/dashboard/LoadingState";

const RECENT_ACTIVITY = [
  { title: "Profile completed", detail: "Your profile is ready for matching." },
  { title: "Dashboard created", detail: "Start exploring schemes from the sidebar." }
];

type RecentActivitySectionProps = {
  isLoading?: boolean;
};

export function RecentActivitySection({ isLoading = false }: RecentActivitySectionProps) {
  return (
    <DashboardCard title="Recent Activity">
      {isLoading ? (
        <LoadingState rows={2} />
      ) : RECENT_ACTIVITY.length ? (
        <div className="space-y-3">
          {RECENT_ACTIVITY.map((activity) => (
            <div className="rounded-md border p-3" key={activity.title}>
              <h3 className="text-sm font-medium">{activity.title}</h3>
              <p className="mt-1 text-xs text-muted-foreground">{activity.detail}</p>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState message="No recent activity yet." />
      )}
    </DashboardCard>
  );
}

