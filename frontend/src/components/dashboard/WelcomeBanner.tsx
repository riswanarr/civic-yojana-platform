type WelcomeBannerProps = {
  fullName?: string;
};

export function WelcomeBanner({ fullName }: WelcomeBannerProps) {
  const displayName = fullName?.trim() || "there";

  return (
    <section className="rounded-lg border bg-card p-5 text-card-foreground">
      <p className="text-sm text-muted-foreground">Welcome back</p>
      <h1 className="mt-2 text-2xl font-semibold">Hello, {displayName}</h1>
      <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
        Your dashboard is ready for scheme discovery, saved items, and application tracking.
      </p>
    </section>
  );
}

