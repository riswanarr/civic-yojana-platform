import { useEffect } from "react";
import { ArrowRight, BookmarkCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { usePageTitle } from "@/hooks/usePageTitle";
import { useAuthStore } from "@/store/authStore";
import { useSavedSchemeStore } from "@/store/savedSchemeStore";

export function SavedSchemesPage() {
  usePageTitle("Saved Schemes | Government Schemes Discovery");

  const accessToken = useAuthStore((state) => state.session?.access_token);
  const savedSchemes = useSavedSchemeStore((state) => state.savedSchemes);
  const isLoading = useSavedSchemeStore((state) => state.isLoading);
  const savingIds = useSavedSchemeStore((state) => state.savingIds);
  const error = useSavedSchemeStore((state) => state.error);
  const fetchSavedSchemes = useSavedSchemeStore((state) => state.fetchSavedSchemes);
  const unsaveScheme = useSavedSchemeStore((state) => state.unsaveScheme);
  const resetSavedSchemes = useSavedSchemeStore((state) => state.resetSavedSchemes);

  useEffect(() => {
    if (accessToken) {
      void fetchSavedSchemes();
      return;
    }

    resetSavedSchemes();
  }, [accessToken, fetchSavedSchemes, resetSavedSchemes]);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Saved Schemes</h1>
        <p className="text-sm text-muted-foreground">Schemes you saved for later review.</p>
      </div>

      {error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {isLoading ? <LoadingState rows={4} /> : null}

      {!isLoading && !error && savedSchemes.length === 0 ? (
        <EmptyState message="No saved schemes yet. Save schemes from Explore Schemes to review them here." />
      ) : null}

      {!isLoading && savedSchemes.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {savedSchemes.map((scheme) => (
            <article
              className="group flex min-h-64 flex-col rounded-md border bg-background p-4 transition hover:border-primary/60 hover:shadow-sm"
              key={scheme.id}
            >
              <div className="flex items-start justify-between gap-3">
                <span className="rounded-md bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
                  {scheme.category}
                </span>
                <button
                  className="inline-flex h-8 items-center gap-1 rounded-md border px-2 text-xs font-medium text-muted-foreground hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
                  type="button"
                  onClick={() => void unsaveScheme(scheme.id)}
                  disabled={savingIds.has(scheme.id)}
                >
                  <BookmarkCheck className="h-3.5 w-3.5" />
                  Saved
                </button>
              </div>

              <Link className="flex flex-1 flex-col" to={`/schemes/${scheme.id}`}>
                <div className="mt-4 flex items-start justify-between gap-3">
                  <h2 className="line-clamp-2 text-base font-semibold">{scheme.title}</h2>
                  <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-primary" />
                </div>
                <p className="mt-2 line-clamp-4 text-sm text-muted-foreground">{scheme.description}</p>

                <dl className="mt-auto grid gap-2 pt-4 text-xs text-muted-foreground">
                  <div className="flex justify-between gap-3">
                    <dt>State</dt>
                    <dd className="truncate text-right font-medium text-foreground">{scheme.state || "All India"}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt>Ministry</dt>
                    <dd className="truncate text-right font-medium text-foreground">{scheme.ministry || "Not specified"}</dd>
                  </div>
                </dl>
              </Link>
            </article>
          ))}
        </div>
      ) : null}
    </div>
  );
}
