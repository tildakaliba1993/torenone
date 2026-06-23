"use client";

import { useState } from "react";

import Link from "next/link";

import { FrameDiagrams } from "@/components/design/frame-diagrams";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
  /** Wizard "start another design" handler. Omitted when viewing a past run (read-only). */
  onRestart?: () => void;
}) {
  const { result: design, report } = result;
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState<string | null>(null);

  // Editable cost-per-tonne (FR-25/31). Default = the rate the kernel used
  // (indicative_cost / tonnage); recompute the indicative cost client-side as the
  // engineer adjusts it — no re-run needed (cost = tonnage × rate).
  const defaultRatePerTonne =
    design.total_steel_tonnes && design.indicative_cost_zar
      ? design.indicative_cost_zar / design.total_steel_tonnes
      : 20000;
  const [ratePerTonne, setRatePerTonne] = useState<string>(
    String(Math.round(defaultRatePerTonne)),
  );
  const parsedRate = Number(ratePerTonne);
  const computedCost =
    design.total_steel_tonnes != null && Number.isFinite(parsedRate) && parsedRate > 0
      ? design.total_steel_tonnes * parsedRate
      : design.indicative_cost_zar;

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
            <div className="flex items-center gap-2">
              <ProvenanceBadge />
              <StatusBadge status={design.passed ? "pass" : "fail"}>
                {design.passed ? "All checks pass" : "Some checks fail"}
              </StatusBadge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 text-sm">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
            <Stat label="Governing" value={design.governing_utilisation.toFixed(2)} mono />
            {design.total_steel_tonnes != null ? (
              <Stat label="Steel" value={`${design.total_steel_tonnes.toFixed(2)} t`} mono />
            ) : null}
            {computedCost != null ? (
              <Stat label="Indicative cost" value={fmtZar(computedCost)} mono />
            ) : null}
            {design.sections.map((s) => (
              <Stat key={s.member} label={s.member} value={s.designation} mono />
            ))}
          </dl>
          {design.total_steel_tonnes != null ? (
            <div className="flex max-w-xs flex-col gap-1">
              <label htmlFor="cost-per-tonne" className="text-xs text-muted">
                Cost per tonne (ZAR)
              </label>
              <Input
                id="cost-per-tonne"
                type="number"
                inputMode="decimal"
                value={ratePerTonne}
                onChange={(e) => setRatePerTonne(e.target.value)}
                className="font-mono"
              />
              <p className="text-xs text-subtle">
                Indicative only — confirm with your fabricator. Adjust to re-cost the tonnage.
              </p>
            </div>
          ) : null}
          <div className="flex flex-col gap-2">
            <Button onClick={onDownload} loading={downloading} className="self-start">
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

      <LiabilityNotice />

      {design.diagram ? (
        <Card>
          <CardHeader>
            <CardTitle>Bending moment &amp; shear force</CardTitle>
          </CardHeader>
          <CardContent>
            <FrameDiagrams diagram={design.diagram} />
          </CardContent>
        </Card>
      ) : null}

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

      <StandardsCard rulesVersion={design.rules_version} />

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

      {onRestart ? (
        <div>
          <Button variant="secondary" onClick={onRestart}>
            Start another design
          </Button>
        </div>
      ) : null}
    </div>
  );
}

/** In-product liability disclaimer on the results screen (§2.4). */
function LiabilityNotice() {
  return (
    <div
      role="note"
      className="border-warning/40 bg-warning/10 rounded-md border px-4 py-3 text-sm"
    >
      <p className="text-foreground font-medium">Computational aid — not a stamped design</p>
      <p className="text-muted mt-1">
        Every figure here is computed by TorenOne&rsquo;s deterministic SANS kernel and is{" "}
        <strong>indicative</strong>. It is not a substitute for an engineer&rsquo;s professional
        judgement. A registered engineer (ECSA) must review, verify and stamp this design — and check
        all items marked out of scope or provisional — before it is used in construction. See the{" "}
        <Link href="/terms" className="text-accent hover:underline">
          Terms
        </Link>{" "}
        and{" "}
        <Link href="/privacy" className="text-accent hover:underline">
          Privacy Policy
        </Link>
        .
      </p>
    </div>
  );
}

/** Provenance badge (FR-26): every number is from the deterministic kernel, not the AI. */
function ProvenanceBadge() {
  return (
    <span
      className="inline-flex items-center rounded-full border border-border bg-surface px-2.5 py-0.5 text-xs font-medium text-muted"
      title="Every figure is computed by the deterministic SANS kernel — the AI only parses your description."
    >
      Deterministic kernel — not AI
    </span>
  );
}

/** Audit / show-your-working: the pinned standard editions behind this run (FR-26). */
function StandardsCard({ rulesVersion }: { rulesVersion: Record<string, string> }) {
  const entries = Object.entries(rulesVersion);
  if (entries.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Provenance &amp; standards</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm">
        <p className="text-muted">
          Every figure above is produced by TorenOne&rsquo;s deterministic kernel and traced to a
          SANS clause — not generated by AI. This run used the pinned standard editions below; the
          full clause-by-clause working is in the downloadable calc package.
        </p>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2">
          {entries.map(([key, value]) => (
            <div key={key} className="flex justify-between gap-4 border-b border-border/50 py-1">
              <dt className="text-muted capitalize">{key.replace(/_/g, " ")}</dt>
              <dd className="font-mono text-xs">{value}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
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
