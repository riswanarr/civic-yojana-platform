import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowRight, Bookmark, BookmarkCheck, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { usePageTitle } from "@/hooks/usePageTitle";
import { useAuthStore } from "@/store/authStore";
import { useSchemeStore } from "@/store/schemeStore";
import { useSavedSchemeStore } from "@/store/savedSchemeStore";

const PAGE_SIZE = 12;

const CATEGORY_OPTIONS = [
  "Agriculture",
  "Education",
  "Employment",
  "Fellowship / Research",
  "Government Job",
  "Government Job / Banking",
  "Government Job / Defence",
  "Government Job / Energy",
  "Government Job / Finance",
  "Government Job / Insurance",
  "Government Job / Manufacturing",
  "Government Job / Railway",
  "Government Job / Research",
  "Health",
  "Housing",
  "Minority Welfare",
  "Scholarship",
  "Social Welfare",
  "Skill Development / Job",
  "Startup / Job Creation",
  "Women and Child",
  "Youth"
];

const STATE_OPTIONS = [
  "All India",
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Delhi",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jammu and Kashmir",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "NCR Delhi",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal"
];

export function SchemesPage() {
  usePageTitle("Explore Schemes | Government Schemes Discovery");

  const schemes = useSchemeStore((state) => state.schemes);
  const page = useSchemeStore((state) => state.page);
  const pageSize = useSchemeStore((state) => state.pageSize);
  const total = useSchemeStore((state) => state.total);
  const isLoading = useSchemeStore((state) => state.isLoading);
  const error = useSchemeStore((state) => state.error);
  const fetchSchemes = useSchemeStore((state) => state.fetchSchemes);
  const accessToken = useAuthStore((state) => state.session?.access_token);
  const savedSchemeIds = useSavedSchemeStore((state) => state.savedSchemeIds);
  const savingIds = useSavedSchemeStore((state) => state.savingIds);
  const savedError = useSavedSchemeStore((state) => state.error);
  const fetchSavedSchemes = useSavedSchemeStore((state) => state.fetchSavedSchemes);
  const saveScheme = useSavedSchemeStore((state) => state.saveScheme);
  const unsaveScheme = useSavedSchemeStore((state) => state.unsaveScheme);
  const resetSavedSchemes = useSavedSchemeStore((state) => state.resetSavedSchemes);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [state, setState] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const emptyMessage =
    search || category || state
      ? "No schemes match the selected search, category, and state filters. Try clearing one filter or choosing All states and national schemes."
      : "No schemes are available yet.";

  const activeFilters = useMemo(
    () => ({
      search,
      category,
      state,
      page: currentPage,
      pageSize: PAGE_SIZE
    }),
    [category, currentPage, search, state]
  );

  useEffect(() => {
    void fetchSchemes(activeFilters);
  }, [activeFilters, fetchSchemes]);

  useEffect(() => {
    if (accessToken) {
      void fetchSavedSchemes();
      return;
    }

    resetSavedSchemes();
  }, [accessToken, fetchSavedSchemes, resetSavedSchemes]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchInput);
    setCurrentPage(1);
  }

  function updateCategory(value: string) {
    setCategory(value);
    setCurrentPage(1);
  }

  function updateState(value: string) {
    setState(value);
    setCurrentPage(1);
  }

  function goToPage(nextPage: number) {
    setCurrentPage(nextPage);
  }

  function toggleSaved(schemeId: string) {
    if (savedSchemeIds.has(schemeId)) {
      void unsaveScheme(schemeId);
      return;
    }

    void saveScheme(schemeId);
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Explore Schemes</h1>
        <p className="text-sm text-muted-foreground">Search and filter available government schemes.</p>
      </div>

      <div className="rounded-md border bg-background p-4">
        <div className="grid gap-3 lg:grid-cols-[1fr_220px_220px]">
          <form className="flex min-w-0 gap-2" onSubmit={handleSearch}>
            <label className="sr-only" htmlFor="scheme-search">
              Search schemes
            </label>
            <div className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                id="scheme-search"
                className="h-10 w-full rounded-md border bg-background pl-9 pr-3 text-sm outline-none focus:border-primary"
                placeholder="Search by title, benefit, ministry..."
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </div>
            <button className="h-10 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" type="submit">
              Search
            </button>
          </form>

          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Category
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm font-normal text-foreground outline-none focus:border-primary"
              value={category}
              onChange={(event) => updateCategory(event.target.value)}
            >
              <option value="">All categories</option>
              {CATEGORY_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            State
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm font-normal text-foreground outline-none focus:border-primary"
              value={state}
              onChange={(event) => updateState(event.target.value)}
            >
              <option value="">All states and national schemes</option>
              {STATE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {error ? <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">{error}</div> : null}
      {savedError ? <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">{savedError}</div> : null}

      {isLoading ? <LoadingState rows={6} /> : null}

      {!isLoading && !error && schemes.length === 0 ? <EmptyState message={emptyMessage} /> : null}

      {!isLoading && schemes.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {schemes.map((scheme) => (
            <article
              className="group flex min-h-64 flex-col rounded-md border bg-background p-4 transition hover:border-primary/60 hover:shadow-sm"
              key={scheme.id}
            >
              <div className="flex items-start justify-between gap-3">
                <span className="rounded-md bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
                  {scheme.category}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    className="inline-flex h-8 items-center gap-1 rounded-md border px-2 text-xs font-medium text-muted-foreground hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
                    type="button"
                    onClick={() => toggleSaved(scheme.id)}
                    disabled={!accessToken || savingIds.has(scheme.id)}
                  >
                    {savedSchemeIds.has(scheme.id) ? <BookmarkCheck className="h-3.5 w-3.5" /> : <Bookmark className="h-3.5 w-3.5" />}
                    {savedSchemeIds.has(scheme.id) ? "Saved" : "Save"}
                  </button>
                  <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-primary" />
                </div>
              </div>

              <Link className="flex flex-1 flex-col" to={`/schemes/${scheme.id}`}>
                <h2 className="mt-4 line-clamp-2 text-base font-semibold">{scheme.title}</h2>
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

      {!isLoading && total > 0 ? (
        <div className="flex flex-col gap-3 border-t pt-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>
            Showing page {page} of {totalPages} ({total} schemes)
          </p>
          <div className="flex gap-2">
            <button
              className="rounded-md border px-3 py-2 font-medium text-foreground disabled:cursor-not-allowed disabled:opacity-50"
              type="button"
              onClick={() => goToPage(page - 1)}
              disabled={page <= 1}
            >
              Previous
            </button>
            <button
              className="rounded-md border px-3 py-2 font-medium text-foreground disabled:cursor-not-allowed disabled:opacity-50"
              type="button"
              onClick={() => goToPage(page + 1)}
              disabled={page >= totalPages}
            >
              Next
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
