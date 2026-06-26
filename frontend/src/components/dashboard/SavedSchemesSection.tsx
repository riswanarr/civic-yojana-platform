import { DashboardCard } from "@/components/dashboard/DashboardCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { LoadingState } from "@/components/dashboard/LoadingState";

const SAVED_SCHEMES = [
  { title: "Student Financial Aid", status: "Saved" },
  { title: "Employment Registration Support", status: "Saved" }
];

type SavedSchemesSectionProps = {
  isLoading?: boolean;
};

export function SavedSchemesSection({ isLoading = false }: SavedSchemesSectionProps) {
  return (
    <DashboardCard title="Saved Schemes">
      {isLoading ? (
        <LoadingState rows={2} />
      ) : SAVED_SCHEMES.length ? (
        <div className="space-y-3">
          {SAVED_SCHEMES.map((scheme) => (
            <div className="flex items-center justify-between rounded-md border p-3" key={scheme.title}>
              <h3 className="text-sm font-medium">{scheme.title}</h3>
              <span className="text-xs text-muted-foreground">{scheme.status}</span>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState message="Saved schemes will appear here." />
      )}
    </DashboardCard>
  );
}

