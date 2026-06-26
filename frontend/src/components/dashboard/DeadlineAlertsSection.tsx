import { DashboardCard } from "@/components/dashboard/DashboardCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { LoadingState } from "@/components/dashboard/LoadingState";

const DEADLINE_ALERTS = [
  { title: "Scholarship application window", date: "Coming soon" },
  { title: "Document verification reminder", date: "Pending date" }
];

type DeadlineAlertsSectionProps = {
  isLoading?: boolean;
};

export function DeadlineAlertsSection({ isLoading = false }: DeadlineAlertsSectionProps) {
  return (
    <DashboardCard title="Deadline Alerts">
      {isLoading ? (
        <LoadingState rows={2} />
      ) : DEADLINE_ALERTS.length ? (
        <div className="space-y-3">
          {DEADLINE_ALERTS.map((alert) => (
            <div className="rounded-md border p-3" key={alert.title}>
              <h3 className="text-sm font-medium">{alert.title}</h3>
              <p className="mt-1 text-xs text-muted-foreground">{alert.date}</p>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState message="No deadline alerts yet." />
      )}
    </DashboardCard>
  );
}

