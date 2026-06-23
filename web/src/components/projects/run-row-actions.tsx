"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { deleteRun, renameRun } from "@/app/(app)/projects/[id]/actions";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export function RunRowActions({
  id,
  projectId,
  label,
}: {
  id: string;
  projectId: string;
  label: string;
}) {
  const router = useRouter();
  const [renameOpen, setRenameOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [value, setValue] = useState(label);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onRename() {
    setPending(true);
    setError(null);
    const res = await renameRun({ id, projectId, label: value });
    setPending(false);
    if (res.error) return setError(res.error);
    setRenameOpen(false);
    router.refresh();
  }

  async function onDelete() {
    setPending(true);
    setError(null);
    const res = await deleteRun({ id, projectId });
    setPending(false);
    if (res.error) return setError(res.error);
    setDeleteOpen(false);
    router.refresh();
  }

  // Stop row-click navigation when interacting with the actions.
  return (
    <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="sm">
            Rename
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename design</DialogTitle>
            <DialogDescription>A label makes this design easy to find and search.</DialogDescription>
          </DialogHeader>
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. Woodstock warehouse — option A"
            aria-label="Design label"
            autoFocus
          />
          {error ? (
            <p role="alert" className="text-danger text-sm">
              {error}
            </p>
          ) : null}
          <DialogFooter>
            <Button onClick={onRename} loading={pending} disabled={pending}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="sm" className="text-danger hover:text-danger">
            Delete
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete design?</DialogTitle>
            <DialogDescription>
              This permanently deletes this design run and its calc-package PDF. This cannot be
              undone.
            </DialogDescription>
          </DialogHeader>
          {error ? (
            <p role="alert" className="text-danger text-sm">
              {error}
            </p>
          ) : null}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteOpen(false)} disabled={pending}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={onDelete} loading={pending}>
              Delete design
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
