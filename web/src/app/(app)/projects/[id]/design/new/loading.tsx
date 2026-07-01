import { CardSkeleton, PageHeaderSkeleton, PageShell } from "@/components/ui/page-skeleton";

export default function Loading() {
  return (
    <PageShell>
      <PageHeaderSkeleton eyebrow />
      <CardSkeleton rows={6} />
    </PageShell>
  );
}
