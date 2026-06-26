import { DashboardCard } from "@/components/dashboard/DashboardCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { LoadingState } from "@/components/dashboard/LoadingState";

const TOP_MATCHES = [
  { title: "Education Support Scheme", category: "Education", match: "High match" },
  { title: "Skill Development Assistance", category: "Employment", match: "Medium match" },
  { title: "Family Welfare Benefit", category: "Welfare", match: "Medium match" }
];

type TopMatchesSectionProps = {
  isLoading?: boolean;
};

export function TopMatchesSection({ isLoading = false }: TopMatchesSectionProps) {
  return (
    <DashboardCard title="Top Matches" description="Placeholder scheme matches for the dashboard shell.">
      {isLoading ? (
        <LoadingState />
      ) : TOP_MATCHES.length ? (
        <div className="space-y-3">
          {TOP_MATCHES.map((scheme) => (
            <div className="rounded-md border p-3" key={scheme.title}>
              <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-sm font-medium">{scheme.title}</h3>
                <span className="text-xs text-muted-foreground">{scheme.match}</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{scheme.category}</p>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState message="No scheme matches to show yet." />
      )}
    </DashboardCard>
  );
}

