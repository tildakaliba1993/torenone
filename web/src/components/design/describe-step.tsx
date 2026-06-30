"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  type ParseResponse,
  ServiceError,
  parseDescription,
  parseDrawing,
} from "@/lib/api/service";

const EXAMPLES = [
  "20 m clear-span warehouse in Pretoria, 6 m to eaves, 10° roof pitch, 6 m bay spacing, 5 bays.",
  "15 m span farm shed, 5 m eaves height, 8° pitch, 7 m bays, 4 bays, terrain category B.",
  "30 m portal frame near the coast, 7.5 m eaves, 12° pitch, 6 m bays, 8 bays.",
] as const;

const MAX = 5000;
const MAX_IMAGE_BYTES = 10 * 1024 * 1024; // 10 MB

export function DescribeStep({ onComplete }: { onComplete: (result: ParseResponse) => void }) {
  const [description, setDescription] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<ParseResponse | null>(null);
  const [drawingName, setDrawingName] = useState<string | null>(null);
  const [drawingPreview, setDrawingPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const trimmed = description.trim();
  const disabled = pending || trimmed.length === 0 || description.length > MAX;

  function handleResult(result: ParseResponse) {
    if (result.status === "complete" && result.spec) {
      onComplete(result);
      return;
    }
    setFeedback(result);
  }

  async function onParse() {
    if (trimmed.length === 0 || description.length > MAX) return;
    setPending(true);
    setError(null);
    setFeedback(null);
    try {
      handleResult(await parseDescription(trimmed));
    } catch (e) {
      setError(e instanceof ServiceError ? e.message : "Something went wrong while parsing.");
    } finally {
      setPending(false);
    }
  }

  function readAsDataUrl(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => reject(new Error("Could not read the file."));
      reader.readAsDataURL(file);
    });
  }

  async function onDrawingSelected(file: File | undefined) {
    if (!file) return;
    setError(null);
    setFeedback(null);
    const isImage = file.type.startsWith("image/");
    const isPdf = file.type === "application/pdf";
    if (!isImage && !isPdf) {
      setError("Please choose an image (PNG, JPG…) or a PDF.");
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setError("That file is too large — please use one under 10 MB.");
      return;
    }
    setPending(true);
    setDrawingName(file.name);
    try {
      const dataUrl = await readAsDataUrl(file);
      setDrawingPreview(dataUrl);
      // Any text typed above is passed along as extra context for the drawing.
      handleResult(await parseDrawing(dataUrl, trimmed || undefined));
    } catch (e) {
      setError(e instanceof ServiceError ? e.message : "Something went wrong reading the drawing.");
    } finally {
      setPending(false);
    }
  }

  // Re-read the SAME drawing — picking up anything the engineer has since typed above (e.g. a
  // dimension the drawing didn't label). Lets a partially-read drawing be completed without
  // re-uploading or losing what was already read.
  async function onReadDrawingAgain() {
    if (!drawingPreview) return;
    setPending(true);
    setError(null);
    setFeedback(null);
    try {
      handleResult(await parseDrawing(drawingPreview, trimmed || undefined));
    } catch (e) {
      setError(e instanceof ServiceError ? e.message : "Something went wrong reading the drawing.");
    } finally {
      setPending(false);
    }
  }

  function removeDrawing() {
    setDrawingPreview(null);
    setDrawingName(null);
    setFeedback(null);
    setError(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <label htmlFor="description" className="text-sm font-medium text-foreground">
          Describe your portal frame
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={5}
          placeholder="e.g. 20 m clear-span warehouse in Pretoria, 6 m to eaves, 10° pitch, 6 m bays, 5 bays."
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-subtle focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        />
        <span className="text-xs text-subtle">
          {description.length}/{MAX}
        </span>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-xs tracking-wide text-subtle uppercase">Try an example</span>
        <div className="flex flex-col gap-2">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setDescription(example)}
              className="rounded-md border border-border bg-surface-raised px-3 py-2 text-left text-sm text-muted transition-colors hover:border-border-strong hover:text-foreground"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3" aria-hidden="true">
        <span className="h-px flex-1 bg-border" />
        <span className="text-xs tracking-wide text-subtle uppercase">or upload a drawing</span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted">
          Upload a drawing, plan, or sketch. We read only the dimensions you’ve labelled on it —
          anything not shown becomes a question, never a guess. You confirm everything before any
          engineering runs.
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,application/pdf"
          className="hidden"
          onChange={(e) => {
            void onDrawingSelected(e.target.files?.[0]);
            e.target.value = ""; // allow re-selecting the same file
          }}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={pending}
          className="flex flex-col items-center justify-center gap-1 rounded-md border border-dashed border-border-strong bg-surface px-3 py-6 text-sm text-muted transition-colors hover:border-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
        >
          <span className="font-medium text-foreground">Choose a drawing or plan…</span>
          <span className="text-xs text-subtle">PNG, JPG or PDF, up to 10 MB</span>
        </button>
        {drawingPreview ? (
          <div className="flex items-center gap-3 rounded-md border border-border bg-surface-raised p-2">
            {drawingPreview.startsWith("data:application/pdf") ? (
              <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded bg-surface font-mono text-xs font-semibold text-accent">
                PDF
              </span>
            ) : (
              /* eslint-disable-next-line @next/next/no-img-element -- local data-URL preview, not a remote asset */
              <img
                src={drawingPreview}
                alt="Uploaded drawing preview"
                className="h-16 w-16 rounded object-cover"
              />
            )}
            <span className="flex-1 truncate text-sm text-muted">{drawingName}</span>
            <button
              type="button"
              onClick={removeDrawing}
              disabled={pending}
              className="text-xs text-subtle underline-offset-2 hover:text-foreground hover:underline disabled:opacity-60"
            >
              Remove
            </button>
          </div>
        ) : null}
      </div>

      {error ? (
        <p role="alert" className="text-sm font-medium text-danger">
          {error}
        </p>
      ) : null}

      {feedback ? <ParseFeedback result={feedback} /> : null}

      <div>
        {drawingPreview ? (
          <Button onClick={() => void onReadDrawingAgain()} loading={pending} disabled={pending}>
            {pending ? "Reading…" : "Read drawing again with these details"}
          </Button>
        ) : (
          <Button onClick={onParse} loading={pending} disabled={disabled}>
            {pending ? "Working…" : "Parse description"}
          </Button>
        )}
      </div>
    </div>
  );
}

function ParseFeedback({ result }: { result: ParseResponse }) {
  if (result.status === "out_of_scope") {
    return (
      <Card>
        <CardContent className="flex flex-col gap-1 py-4 text-sm">
          <p className="font-medium text-warning">Outside the current scope</p>
          <p className="text-muted">{result.scope_note}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 py-4 text-sm">
        {result.errors.length > 0 ? (
          <div className="flex flex-col gap-1">
            <p className="font-medium text-danger">Please fix</p>
            <ul className="list-disc pl-5 text-muted">
              {result.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {result.questions.length > 0 ? (
          <div className="flex flex-col gap-1">
            <p className="font-medium text-foreground">A few details needed</p>
            <ul className="flex flex-col gap-1 text-muted">
              {result.questions.map((q, i) => (
                <li key={i}>
                  • {q.question}
                  {q.unit ? ` (${q.unit})` : ""}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <p className="text-xs text-subtle">
          Add these to your description (or label them on the drawing) and try again.
        </p>
      </CardContent>
    </Card>
  );
}
