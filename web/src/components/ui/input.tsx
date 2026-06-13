import * as React from "react";

import { cn } from "@/lib/utils";

/** Text input themed to the TorenOne tokens (Design §B.5). */
const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-9 w-full rounded-md border border-border bg-surface px-3 py-1 text-sm text-foreground shadow-sm transition-colors placeholder:text-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export { Input };
