import { useEffect } from "react";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { usePageTitle } from "@/hooks/usePageTitle";
import { useSchemeStore } from "@/store/schemeStore";

export function SchemeDetailPage() {
  const { schemeId } = useParams();
  const scheme = useSchemeStore((state) => state.selectedScheme);
  const isLoading = useSchemeStore((state) => state.isDetailLoading);
  const error = useSchemeStore((state) => state.error);
  const fetchScheme = useSchemeStore((state) => state.fetchScheme);
  const clearSelectedScheme = useSchemeStore((state) => state.clearSelectedScheme);

  usePageTitle(`${scheme?.title ?? "Scheme Detail"} | Government Schemes Discovery`);

  useEffect(() => {
    if (schemeId) {
      void fetchScheme(schemeId);
    }

    return () => clearSelectedScheme();
  }, [clearSelectedScheme, fetchScheme, schemeId]);

  if (isLoading) {
    return <LoadingState rows={5} />;
  }

  if (error) {
    return <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">{error}</div>;
  }

  if (!scheme) {
    return <EmptyState message="Scheme details are not available." />;
  }

  return (
    <div className="space-y-6">
      <Link className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground" to="/schemes">
        <ArrowLeft className="h-4 w-4" />
        Back to schemes
      </Link>

      <div className="rounded-md border bg-background p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 space-y-3">
            <span className="inline-flex rounded-md bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
              {scheme.category}
            </span>
            <h1 className="text-2xl font-semibold">{scheme.title}</h1>
            <p className="max-w-3xl text-sm leading-6 text-muted-foreground">{scheme.description}</p>
          </div>

          {scheme.application_link ? (
            <a
              className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
              href={scheme.application_link}
              rel="noreferrer"
              target="_blank"
            >
              Apply
              <ExternalLink className="h-4 w-4" />
            </a>
          ) : null}
        </div>

        <dl className="mt-6 grid gap-4 border-t pt-5 text-sm md:grid-cols-2 xl:grid-cols-4">
          <div>
            <dt className="text-xs font-medium uppercase text-muted-foreground">State</dt>
            <dd className="mt-1 font-medium">{scheme.state || "All India"}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-muted-foreground">Ministry</dt>
            <dd className="mt-1 font-medium">{scheme.ministry || "Not specified"}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-muted-foreground">Deadline</dt>
            <dd className="mt-1 font-medium">{scheme.deadline || "Not specified"}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-muted-foreground">Source</dt>
            <dd className="mt-1 truncate font-medium">{scheme.official_source || "Not specified"}</dd>
          </div>
        </dl>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-md border bg-background p-5">
          <h2 className="text-base font-semibold">Eligibility</h2>
          <p className="mt-3 whitespace-pre-line text-sm leading-6 text-muted-foreground">
            {scheme.eligibility_criteria || "Eligibility details are not specified."}
          </p>
        </section>

        <section className="rounded-md border bg-background p-5">
          <h2 className="text-base font-semibold">Benefits</h2>
          <p className="mt-3 whitespace-pre-line text-sm leading-6 text-muted-foreground">
            {scheme.benefits || "Benefit details are not specified."}
          </p>
        </section>
      </div>

      {scheme.tags.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {scheme.tags.map((tag) => (
            <span className="rounded-md border bg-background px-2 py-1 text-xs text-muted-foreground" key={tag}>
              {tag}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
