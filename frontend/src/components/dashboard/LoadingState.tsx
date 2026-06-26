type LoadingStateProps = {
  rows?: number;
};

export function LoadingState({ rows = 3 }: LoadingStateProps) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, index) => (
        <div className="h-12 animate-pulse rounded-md bg-muted" key={index} />
      ))}
    </div>
  );
}

