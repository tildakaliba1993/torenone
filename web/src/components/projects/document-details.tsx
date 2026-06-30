"use client";

import { useState } from "react";

import { updateProjectReportMetadata } from "@/app/(app)/projects/[id]/actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { type ReportMetadata } from "@/lib/api/service";

type Field = keyof ReportMetadata;

const FIELDS: Array<{ key: Field; label: string; placeholder?: string }> = [
  { key: "project_name", label: "Project name" },
  { key: "project_number", label: "Project number" },
  { key: "client", label: "Client" },
  { key: "revision", label: "Revision", placeholder: "e.g. A" },
  { key: "site_address", label: "Site address" },
  { key: "engineer_name", label: "Responsible engineer" },
  { key: "engineer_reg_no", label: "ECSA registration no." },
];

function str(v: string | null | undefined): string {
  return v ?? "";
}

/**
 * Project-level document/cover details. Set once here and every calc package generated for the
 * project inherits it (and the Review step pre-fills from it). All optional.
 */
export function DocumentDetails({
  projectId,
  initial,
}: {
  projectId: string;
  initial: ReportMetadata | null;
}) {
  const [values, setValues] = useState<ReportMetadata>({
    project_name: str(initial?.project_name),
    project_number: str(initial?.project_number),
    client: str(initial?.client),
    revision: str(initial?.revision),
    site_address: str(initial?.site_address),
    engineer_name: str(initial?.engineer_name),
    engineer_reg_no: str(initial?.engineer_reg_no),
  });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function onSave() {
    setSaving(true);
    setStatus("idle");
    setError(null);
    const res = await updateProjectReportMetadata({ projectId, metadata: values });
    setSaving(false);
    if (res.error) {
      setStatus("error");
      setError(res.error);
    } else {
      setStatus("saved");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Document details</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 text-sm">
        <p className="text-muted">
          These appear on every calc-package cover for this project so it reads as a submission-ready
          rational design report. All optional — the Review step pre-fills from here and can override
          per design.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {FIELDS.map((f) => (
            <div key={f.key} className="flex flex-col gap-1">
              <label htmlFor={`doc-${f.key}`} className="text-xs text-muted">
                {f.label}
              </label>
              <Input
                id={`doc-${f.key}`}
                placeholder={f.placeholder}
                value={str(values[f.key])}
                onChange={(e) => {
                  setStatus("idle");
                  setValues((v) => ({ ...v, [f.key]: e.target.value }));
                }}
              />
            </div>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={onSave} loading={saving} className="self-start">
            {saving ? "Saving…" : "Save document details"}
          </Button>
          {status === "saved" ? <span className="text-xs text-success">Saved.</span> : null}
          {status === "error" ? (
            <span role="alert" className="text-xs text-danger">
              {error}
            </span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
