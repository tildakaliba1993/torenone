"use client";

import { useState } from "react";

import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  type CheckResult,
  type DesignResponse,
  ServiceError,
  getReportSignedUrl,
} from "@/lib/api/service";

type Status = "pass" | "review" | "fail" | "advisory";

/** Presentation-only: flag near-limit (passing) checks for the engineer's eye. */
function checkStatus(check: CheckResult): Status {
  // Advisory-only checks (e.g. SLS-2 wind sway) are non-gating — never show them as a
  // hard FAIL even when they exceed their limit.
  if (check.informational) return "advisory";
  if (!check.passed || check.utilisation > 1.0) return "fail";
  if (check.utilisation >= 0.9) return "review";
  return "pass";
}

/** Short label shown inside the status badge. */
function checkStatusLabel(check: CheckResult): string {
  if (check.informational) return "advisory";
  return check.passed ? "pass" : "fail";
}

function fmtZar(value: number): string {
  // Deterministic thousands separators (locale-independent).
  return `R ${Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`;
}

export function ResultsStep({
  result,
  onRestart,
}: {
  result: DesignResponse;
  onRestart: () => void;
}) {
  const { result: design, report } = result;
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState<string | null>(null);

  async function onDownload() {
    setDownloading(true);
    setDlError(null);
    try {
      const url = await getReportSignedUrl(report.storage_path);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (e) {
      setDlError(e instanceof ServiceError ? e.message : "Could not download the PDF.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <CardTitle>Design result</CardTitle>
            <StatusBadge status={design.passed ? "pass" : "fail"}>
              {design.passed ? "All checks pass" : "Some checks fail"}
            </StatusBadge>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 text-sm">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
            <Stat label="Governing" value={design.governing_utilisation.toFixed(2)} mono />
            {design.total_steel_tonnes != null ? (
              <Stat label="Steel" value={`${design.total_steel_tonnes.toFixed(2)} t`} mono />
            ) : null}
            {design.indicative_cost_zar != null ? (
              <Stat label="Indicative cost" value={fmtZar(design.indicative_cost_zar)} mono />
            ) : null}
            {design.sections.map((s) => (
              <Stat key={s.member} label={s.member} value={s.designation} mono />
            ))}
          </dl>
          <div className="flex flex-col gap-2">
            <Button onClick={onDownload} disabled={downloading} className="self-start">
              {downloading ? "Preparing…" : "Download calc package (PDF)"}
            </Button>
            {dlError ? (
              <p role="alert" className="text-sm font-medium text-danger">
                {dlError}
              </p>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Checks</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Check</TableHead>
                <TableHead>Clause</TableHead>
                <TableHead>Utilisation</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {design.checks.map((check, i) => (
                <TableRow key={`${check.name}-${i}`}>
                  <TableCell className="font-medium">{check.name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted">{check.clause}</TableCell>
                  <TableCell className="font-mono">{check.utilisation.toFixed(2)}</TableCell>
                  <TableCell>
                    <StatusBadge status={checkStatus(check)}>
                      {checkStatusLabel(check)}
                    </StatusBadge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {design.wind ? (
        <Card>
          <CardHeader>
            <CardTitle>Wind actions — SANS 10160-3</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-3">
              <Stat
                label="Peak velocity pressure qp"
                value={`${design.wind.peak_velocity_pressure_kpa.toFixed(3)} kPa`}
                mono
              />
              <Stat label="Reference height" value={`${design.wind.reference_height_m.toFixed(2)} m`} mono />
              <Stat label="Scenario" value={design.wind.scenario} />
            </dl>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Load case</TableHead>
                  <TableHead>Col W</TableHead>
                  <TableHead>Col L</TableHead>
                  <TableHead>Raf W</TableHead>
                  <TableHead>Raf L</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {design.wind.cases.map((c, i) => (
                  <TableRow key={i}>
                    <TableCell className="text-muted">{c.name}</TableCell>
                    <TableCell className="font-mono">{c.windward_column_udl_kn_per_m.toFixed(2)}</TableCell>
                    <TableCell className="font-mono">{c.leeward_column_udl_kn_per_m.toFixed(2)}</TableCell>
                    <TableCell className="font-mono">{c.windward_rafter_udl_kn_per_m.toFixed(2)}</TableCell>
                    <TableCell className="font-mono">{c.leeward_rafter_udl_kn_per_m.toFixed(2)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="text-xs text-subtle">
              Member line loads (kN/m). Columns: horizontal, +ve = inward; rafters: normal to roof,
              −ve = uplift. The wind load-combination frame analysis isn’t run yet — see Notes.
            </p>
          </CardContent>
        </Card>
      ) : null}

      {design.connections.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Connections</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 text-sm">
            {design.connections.map((c) => (
              <DetailBlock
                key={c.location}
                title={`${c.location} connection`}
                description={c.description}
                rows={[
                  ["Design moment", `${c.design_moment_knm.toFixed(1)} kNm`],
                  ["Design shear", `${c.design_shear_kn.toFixed(1)} kN`],
                ]}
              />
            ))}
          </CardContent>
        </Card>
      ) : null}

      {design.baseplate ? (
        <Card>
          <CardHeader>
            <CardTitle>Baseplate</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <DetailBlock
              title={`${design.baseplate.base_fixity} base`}
              description={design.baseplate.description}
              rows={[
                ["Design axial", `${design.baseplate.design_axial_kn.toFixed(1)} kN`],
                ["Design shear", `${design.baseplate.design_shear_kn.toFixed(1)} kN`],
              ]}
            />
          </CardContent>
        </Card>
      ) : null}

      {design.footing ? (
        <Card>
          <CardHeader>
            <CardTitle>Pad footing</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <DetailBlock
              title="Footing"
              description={design.footing.description}
              rows={[
                ["Plan size", `${design.footing.plan_size_mm.toFixed(0)} mm`],
                ["Thickness", `${design.footing.thickness_mm.toFixed(0)} mm`],
                ["Allowable bearing", `${design.footing.allowable_bearing_kpa.toFixed(0)} kPa`],
              ]}
            />
          </CardContent>
        </Card>
      ) : null}

      {design.warnings.length > 0 ? (
        <Card>
          <CardContent className="flex flex-col gap-1 py-4 text-sm">
            <p className="font-medium text-warning">Notes</p>
            <ul className="list-disc pl-5 text-muted">
              {design.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      <div>
        <Button variant="secondary" onClick={onRestart}>
          Start another design
        </Button>
      </div>
    </div>
  );
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-muted capitalize">{label}</dt>
      <dd className={mono ? "font-mono" : undefined}>{value}</dd>
    </div>
  );
}

function DetailBlock({
  title,
  description,
  rows,
}: {
  title: string;
  description: string;
  rows: Array<[string, string]>;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-md border border-border p-3">
      <p className="font-medium capitalize">{title}</p>
      <p className="text-muted">{description}</p>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between">
            <dt className="text-muted">{k}</dt>
            <dd className="font-mono">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
