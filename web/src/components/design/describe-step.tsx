"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { type ParseResponse, ServiceError, parseDescription } from "@/lib/api/service";

const EXAMPLES = [
  "20 m clear-span warehouse in Pretoria, 6 m to eaves, 10° roof pitch, 6 m bay spacing, 5 bays.",
  "15 m span farm shed, 5 m eaves height, 8° pitch, 7 m bays, 4 bays, terrain category B.",
  "30 m portal frame near the coast, 7.5 m eaves, 12° pitch, 6 m bays, 8 bays.",
] as const;

const MAX = 5000;

export function DescribeStep({ onComplete }: { onComplete: (result: ParseResponse) => void }) {
  const [description, setDescription] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<ParseResponse | null>(null);

  const trimmed = description.trim();
  const disabled = pending || trimmed.length === 0 || description.length > MAX;

  async function onParse() {
    if (trimmed.length === 0 || description.length > MAX) return;
    setPending(true);
    setError(null);
    setFeedback(null);
    try {
      const result = await parseDescription(trimmed);
      if (result.status === "complete" && result.spec) {
        onComplete(result);
        return;
      }
      setFeedback(result);
    } catch (e) {
      setError(e instanceof ServiceError ? e.message : "Something went wrong while parsing.");
    } finally {
      setPending(false);
    }
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

      {error ? (
        <p role="alert" className="text-sm font-medium text-danger">
          {error}
        </p>
      ) : null}

      {feedback ? <ParseFeedback result={feedback} /> : null}

      <div>
        <Button onClick={onParse} loading={pending} disabled={disabled}>
          {pending ? "Parsing…" : "Parse description"}
        </Button>
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
        <p className="text-xs text-subtle">Add these to your description and parse again.</p>
      </CardContent>
    </Card>
  );
}
