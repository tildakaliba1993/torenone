import { ListSkeleton, PageHeaderSkeleton, PageShell } from "@/components/ui/page-skeleton";

export default function Loading() {
  return (
    <PageShell>
      <PageHeaderSkeleton />
      <ListSkeleton rows={5} />
    </PageShell>
  );
}
