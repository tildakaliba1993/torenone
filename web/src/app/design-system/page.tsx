"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Toaster, toast } from "@/components/ui/toast";

const projectSchema = z.object({
  projectName: z.string().min(1, "Project name is required"),
});
type ProjectValues = z.infer<typeof projectSchema>;

/**
 * Living style guide for the TorenOne design system (Task 6.1). Renders every
 * themed primitive so the build verifies them and the team has a visual reference.
 */
export default function DesignSystemPage() {
  const form = useForm<ProjectValues>({
    resolver: zodResolver(projectSchema),
    defaultValues: { projectName: "" },
  });

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-10 px-6 py-16">
      <header className="flex flex-col gap-2">
        <span className="font-mono text-xs tracking-widest text-accent uppercase">
          TorenOne · Design system
        </span>
        <h1 className="text-2xl font-semibold tracking-tight">Component primitives</h1>
        <p className="max-w-xl text-sm text-muted">Themed shadcn/ui on the steel-blue tokens.</p>
      </header>

      <section className="flex flex-wrap items-center gap-3">
        <Button>Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="outline">Outline</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="destructive">Destructive</Button>
        <Button variant="link">Link</Button>
        <Button onClick={() => toast.success("Design run started")}>Toast</Button>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Member utilisation</CardTitle>
          <CardDescription>Numbers come from the deterministic kernel.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Member</TableHead>
                <TableHead>Section</TableHead>
                <TableHead>Utilisation</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell>Rafter</TableCell>
                <TableCell className="font-mono">305x165x54</TableCell>
                <TableCell className="font-mono">0.78</TableCell>
                <TableCell>
                  <StatusBadge status="pass">0.78</StatusBadge>
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Apex connection</TableCell>
                <TableCell className="font-mono">M20 8.8</TableCell>
                <TableCell className="font-mono">0.99</TableCell>
                <TableCell>
                  <StatusBadge status="review">0.99</StatusBadge>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Tabs defaultValue="design">
        <TabsList>
          <TabsTrigger value="design">Design</TabsTrigger>
          <TabsTrigger value="check">Check</TabsTrigger>
        </TabsList>
        <TabsContent value="design" className="text-sm text-muted">
          Auto-size to the lightest passing section.
        </TabsContent>
        <TabsContent value="check" className="text-sm text-muted">
          Verify engineer-supplied sections.
        </TabsContent>
      </Tabs>

      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(() => toast.success("Project created"))}
          className="flex max-w-sm flex-col gap-4"
        >
          <FormField
            control={form.control}
            name="projectName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Project name</FormLabel>
                <FormControl>
                  <Input placeholder="Woodstock warehouse" {...field} />
                </FormControl>
                <FormDescription>Shown in your project list.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit">Create project</Button>
        </form>
      </Form>

      <Dialog>
        <DialogTrigger asChild>
          <Button variant="secondary">Open dialog</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm the spec</DialogTitle>
            <DialogDescription>Nothing computes until you confirm (FR-4).</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="secondary">Cancel</Button>
            </DialogClose>
            <Button>Run design</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Toaster />
    </main>
  );
}
