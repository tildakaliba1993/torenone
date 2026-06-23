"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { deleteProject, renameProject } from "@/app/(app)/projects/actions";
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

export function ProjectRowActions({ id, name }: { id: string; name: string }) {
  const router = useRouter();
  const [renameOpen, setRenameOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [value, setValue] = useState(name);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onRename() {
    setPending(true);
    setError(null);
    const res = await renameProject({ id, name: value });
    setPending(false);
    if (res.error) return setError(res.error);
    setRenameOpen(false);
    router.refresh();
  }

  async function onDelete() {
    setPending(true);
    setError(null);
    const res = await deleteProject({ id });
    setPending(false);
    if (res.error) return setError(res.error);
    setDeleteOpen(false);
    router.refresh();
  }

  return (
    <div className="flex items-center justify-end gap-1">
      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="sm">
            Rename
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename project</DialogTitle>
            <DialogDescription>Give this project a new name.</DialogDescription>
          </DialogHeader>
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            aria-label="Project name"
            autoFocus
          />
          {error ? (
            <p role="alert" className="text-danger text-sm">
              {error}
            </p>
          ) : null}
          <DialogFooter>
            <Button onClick={onRename} loading={pending} disabled={pending || !value.trim()}>
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
            <DialogTitle>Delete project?</DialogTitle>
            <DialogDescription>
              This permanently deletes &ldquo;{name}&rdquo; and all of its designs and reports. This
              cannot be undone.
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
              Delete project
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
