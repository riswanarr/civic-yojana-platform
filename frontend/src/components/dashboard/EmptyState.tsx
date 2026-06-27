type EmptyStateProps = {
  message: string;
};

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div className="mandala-soft rounded-2xl border border-dashed bg-card/70 px-4 py-7 text-center text-sm text-muted-foreground">
      <div className="mx-auto mb-3 h-1 w-16 rounded-full bg-gradient-to-r from-accent via-primary to-sky-500" />
      <p>{message}</p>
    </div>
  );
}
