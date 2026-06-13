import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function ProjectNotFound() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-col items-center gap-4 px-6 py-16 text-center">
      <p className="text-base font-semibold text-foreground">Project not found</p>
      <p className="text-sm text-muted">
        It may have been deleted, or it belongs to another firm.
      </p>
      <Button asChild variant="secondary">
        <Link href="/projects">Back to projects</Link>
      </Button>
    </main>
  );
}
