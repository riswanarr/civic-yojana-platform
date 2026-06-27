import { useEffect } from "react";
import { CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import { DashboardCard } from "@/components/dashboard/DashboardCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { useAuthStore } from "@/store/authStore";
import { useRecommendationStore } from "@/store/recommendationStore";

function formatScore(score: number) {
  return score > 1 ? Math.round(score) : Math.round(score * 100);
}

function getRecommendationReasons(reason: string) {
  const reasons = reason
    .split(/[.;\n]/)
    .map((item) => item.trim())
    .filter(Boolean);

  return reasons.length ? reasons : ["Recommended based on your profile details."];
}

export function TopMatchesSection() {
  const accessToken = useAuthStore((state) => state.session?.access_token);
  const recommendations = useRecommendationStore((state) => state.recommendations);
  const isLoading = useRecommendationStore((state) => state.isLoading);
  const error = useRecommendationStore((state) => state.error);
  const fetchRecommendations = useRecommendationStore((state) => state.fetchRecommendations);
  const resetRecommendations = useRecommendationStore((state) => state.resetRecommendations);

  useEffect(() => {
    if (accessToken) {
      void fetchRecommendations();
      return;
    }

    resetRecommendations();
  }, [accessToken, fetchRecommendations, resetRecommendations]);

  return (
    <DashboardCard title="AI Recommendations" description="Personalized scheme suggestions based on your profile.">
      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      ) : recommendations.length ? (
        <div className="space-y-3">
          {recommendations.map((recommendation) => (
            <div className="rounded-md border bg-background p-4" key={recommendation.scheme_id}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <Link
                    className="text-sm font-semibold hover:text-primary"
                    to={`/schemes/${recommendation.scheme_id}`}
                  >
                    {recommendation.title}
                  </Link>
                  <p className="mt-1 text-xs font-medium text-muted-foreground">
                    Why recommended
                  </p>
                </div>

                <div className="w-fit rounded-md border bg-muted/30 px-3 py-2 text-right">
                  <p className="text-[11px] font-medium uppercase text-muted-foreground">
                    Recommendation Score
                  </p>
                  <p className="mt-1 text-base font-semibold">
                    {formatScore(recommendation.score)}%
                  </p>
                </div>
              </div>

              <ul className="mt-3 space-y-2 text-xs leading-5 text-muted-foreground">
                {getRecommendationReasons(recommendation.reason).map((reason) => (
                  <li className="flex gap-2" key={reason}>
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState message="No AI recommendations are available yet." />
      )}
    </DashboardCard>
  );
}
