import { useEffect } from "react";
import { DashboardCard } from "@/components/dashboard/DashboardCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { useAuthStore } from "@/store/authStore";
import { useRecommendationStore } from "@/store/recommendationStore";

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
            <div className="rounded-md border p-3" key={recommendation.scheme_id}>
              <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-sm font-medium">{recommendation.title}</h3>
                <span className="w-fit rounded-md bg-primary px-2 py-1 text-xs font-semibold text-primary-foreground">
                  {recommendation.score}
                </span>
              </div>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">{recommendation.reason}</p>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState message="No AI recommendations are available yet." />
      )}
    </DashboardCard>
  );
}
