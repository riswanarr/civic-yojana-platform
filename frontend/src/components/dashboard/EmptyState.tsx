type EmptyStateProps = {
  message: string;
};

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div className="rounded-md border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
      {message}
    </div>
  );
}

