import { CardSkeleton, PageHeaderSkeleton, PageShell } from "@/components/ui/page-skeleton";

export default function Loading() {
  return (
    <PageShell className="gap-8">
      <PageHeaderSkeleton action={false} />
      <CardSkeleton rows={3} />
      <CardSkeleton rows={2} />
    </PageShell>
  );
}
