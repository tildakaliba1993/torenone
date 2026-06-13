import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="font-mono text-xs tracking-widest text-accent uppercase">404</p>
      <p className="text-base font-semibold text-foreground">Page not found</p>
      <p className="text-sm text-muted">The page you’re looking for doesn’t exist.</p>
      <Button asChild variant="secondary">
        <Link href="/">Go home</Link>
      </Button>
    </main>
  );
}
