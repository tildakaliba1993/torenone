"use client";

import * as React from "react";

import { Toaster as Sonner, toast } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

/**
 * App-wide toast host (Design §B.5). Mount once near the root; call `toast(...)`
 * anywhere. Themed to the dark TorenOne surfaces with semantic success/error colours.
 */
function Toaster(props: ToasterProps) {
  return (
    <Sonner
      theme="dark"
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group rounded-md border border-border bg-surface-raised text-foreground shadow-lg",
          description: "text-muted",
          actionButton: "bg-primary text-primary-foreground",
          cancelButton: "bg-surface text-muted",
          success: "text-success",
          error: "text-danger",
        },
      }}
      {...props}
    />
  );
}

export { Toaster, toast };
