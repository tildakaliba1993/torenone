import { Button } from "@/components/ui/button";

/** Reusable error fallback for async views (Task 6.8). */
export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  retryLabel = "Try again",
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
  retryLabel?: string;
}) {
  return (
    <div
      role="alert"
      className="mx-auto flex w-full max-w-md flex-col items-center gap-3 py-16 text-center"
    >
      <p className="text-base font-semibold text-foreground">{title}</p>
      {message ? <p className="text-sm text-muted">{message}</p> : null}
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}
