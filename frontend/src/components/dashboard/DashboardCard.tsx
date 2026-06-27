import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type DashboardCardProps = {
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
};

export function DashboardCard({ title, description, children, className }: DashboardCardProps) {
  return (
    <section
      className={cn(
        "rounded-2xl border bg-card/90 p-4 text-card-foreground shadow-sm transition hover:border-accent/50 hover:shadow-md",
        className
      )}
    >
      <div className="mb-4">
        <div className="mb-2 h-1 w-10 rounded-full bg-gradient-to-r from-accent via-primary to-sky-500" />
        <h2 className="text-base font-semibold">{title}</h2>
        {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {children}
    </section>
  );
}
