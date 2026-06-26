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
    <section className={cn("rounded-lg border bg-card p-4 text-card-foreground", className)}>
      <div className="mb-4">
        <h2 className="text-base font-semibold">{title}</h2>
        {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {children}
    </section>
  );
}

