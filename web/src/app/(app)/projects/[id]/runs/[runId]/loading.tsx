import { CardSkeleton, PageHeaderSkeleton, PageShell } from "@/components/ui/page-skeleton";

export default function Loading() {
  return (
    <PageShell>
      <PageHeaderSkeleton eyebrow action={false} />
      <CardSkeleton rows={2} />
      <CardSkeleton rows={5} />
    </PageShell>
  );
}
