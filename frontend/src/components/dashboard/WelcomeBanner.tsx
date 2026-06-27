type WelcomeBannerProps = {
  fullName?: string;
};

export function WelcomeBanner({ fullName }: WelcomeBannerProps) {
  const displayName = fullName?.trim() || "there";

  return (
    <section className="relative overflow-hidden rounded-2xl border bg-gradient-to-br from-card via-secondary/50 to-card p-5 text-card-foreground shadow-sm">
      <div className="mandala-soft absolute inset-y-0 right-0 w-1/3 opacity-60" />
      <div className="relative">
        <p className="text-sm font-medium text-muted-foreground">Welcome back</p>
        <h1 className="mt-2 text-2xl font-semibold">Hello, {displayName}</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Your civic-योजना dashboard is ready for scheme discovery, saved items, and application tracking.
        </p>
      </div>
    </section>
  );
}
