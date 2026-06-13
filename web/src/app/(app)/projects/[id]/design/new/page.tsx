import { notFound, redirect } from "next/navigation";

import { DesignFlow } from "@/components/design/design-flow";
import { createClient } from "@/lib/supabase/server";

export default async function NewDesignPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // RLS (Task 5.4) ensures this only resolves for a project in the caller's firm.
  const { data: project } = await supabase.from("projects").select("id, name").eq("id", id).single();
  if (!project) notFound();

  return <DesignFlow projectId={project.id as string} projectName={project.name as string} />;
}
