"use client";

import { useState } from "react";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { FrameSketch } from "@/components/design/frame-sketch";
import { KernelProgress } from "@/components/design/kernel-progress";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  type DesignResponse,
  type FrameSpec,
  type ReportMetadata,
  ServiceError,
  runDesign,
} from "@/lib/api/service";

// Numeric fields are held as strings (native inputs) and validated/parsed here.
function numberField(opts: {
  message: string;
  gt?: number;
  min?: number;
  max?: number;
  int?: boolean;
  optional?: boolean;
}) {
  return z.string().refine((raw) => {
    const s = raw.trim();
    if (s === "") return opts.optional ?? false;
    const n = Number(s);
    if (!Number.isFinite(n)) return false;
    if (opts.int && !Number.isInteger(n)) return false;
    if (opts.gt !== undefined && !(n > opts.gt)) return false;
    if (opts.min !== undefined && n < opts.min) return false;
    if (opts.max !== undefined && n > opts.max) return false;
    return true;
  }, opts.message);
}

const schema = z
  .object({
    geometry: z.object({
      span_m: numberField({ message: "Span must be greater than 0", gt: 0 }),
      eaves_height_m: numberField({ message: "Eaves height must be greater than 0", gt: 0 }),
      roof_pitch_deg: numberField({ message: "Pitch must be between 0 and 45°", gt: 0, max: 45 }),
      bay_spacing_m: numberField({ message: "Bay spacing must be greater than 0", gt: 0 }),
      number_of_bays: numberField({ message: "At least 1 (whole number)", int: true, min: 1 }),
    }),
    dead: z.object({
      roof_kpa: numberField({ message: "Cannot be negative", min: 0 }),
      services_kpa: numberField({ message: "Cannot be negative", min: 0 }),
      wall_cladding_kpa: numberField({ message: "Cannot be negative", min: 0 }),
    }),
    imposed: z.object({ roof_access: z.boolean() }),
    wind: z.object({
      basic_wind_speed_ms: numberField({ message: "Wind speed must be greater than 0", gt: 0 }),
      terrain_category: z.enum(["A", "B", "C", "D"]),
      site_altitude_m: numberField({ message: "Cannot be negative", min: 0 }),
      has_dominant_opening: z.boolean(),
    }),
    foundation: z.object({
      allowable_bearing_kpa: numberField({
        message: "Must be greater than 0",
        gt: 0,
        optional: true,
      }),
      concrete_fcu_mpa: numberField({ message: "Must be greater than 0", gt: 0 }),
    }),
    materials: z.object({ steel_grade: z.enum(["S275JR", "S355JR"]) }),
    document: z.object({
      project_name: z.string(),
      client: z.string(),
      project_number: z.string(),
      site_address: z.string(),
      engineer_name: z.string(),
      engineer_reg_no: z.string(),
      revision: z.string(),
    }),
    restraints: z.object({
      rafter_restraint_spacing_m: numberField({ message: "Must be greater than 0", gt: 0, optional: true }),
      column_restraint_spacing_m: numberField({ message: "Must be greater than 0", gt: 0, optional: true }),
    }),
    mode: z.enum(["design", "check"]),
    rafter_section: z.string(),
    column_section: z.string(),
    confirmed: z.boolean().refine((v) => v, {
      message: "Please confirm you've reviewed these inputs",
    }),
  })
  .refine(
    (d) =>
      d.mode === "design" ||
      (d.rafter_section.trim().length > 0 && d.column_section.trim().length > 0),
    { message: "Rafter and column section sizes are required in Check mode", path: ["rafter_section"] },
  );

type FormValues = z.infer<typeof schema>;

const n = (value: number | undefined | null): string =>
  value === undefined || value === null ? "" : String(value);
const toNum = (s: string): number => Number(s.trim());
const toOptNum = (s: string): number | null => (s.trim() === "" ? null : Number(s.trim()));

function defaultsFromSpec(spec: FrameSpec, doc?: ReportMetadata): FormValues {
  return {
    geometry: {
      span_m: n(spec.geometry.span_m),
      eaves_height_m: n(spec.geometry.eaves_height_m),
      roof_pitch_deg: n(spec.geometry.roof_pitch_deg),
      bay_spacing_m: n(spec.geometry.bay_spacing_m),
      number_of_bays: n(spec.geometry.number_of_bays),
    },
    dead: {
      roof_kpa: n(spec.dead?.roof_kpa),
      services_kpa: n(spec.dead?.services_kpa ?? 0),
      wall_cladding_kpa: n(spec.dead?.wall_cladding_kpa ?? 0),
    },
    imposed: { roof_access: spec.imposed?.roof_access ?? false },
    wind: {
      basic_wind_speed_ms: n(spec.wind?.basic_wind_speed_ms),
      terrain_category: spec.wind?.terrain_category ?? "B",
      site_altitude_m: n(spec.wind?.site_altitude_m ?? 0),
      has_dominant_opening: spec.wind?.has_dominant_opening ?? false,
    },
    foundation: {
      allowable_bearing_kpa: n(spec.foundation?.allowable_bearing_kpa),
      concrete_fcu_mpa: n(spec.foundation?.concrete_fcu_mpa ?? 25),
    },
    materials: { steel_grade: spec.materials?.steel_grade ?? "S355JR" },
    document: {
      project_name: doc?.project_name ?? "",
      client: doc?.client ?? "",
      project_number: doc?.project_number ?? "",
      site_address: doc?.site_address ?? "",
      engineer_name: doc?.engineer_name ?? "",
      engineer_reg_no: doc?.engineer_reg_no ?? "",
      revision: doc?.revision ?? "",
    },
    restraints: {
      rafter_restraint_spacing_m: n(spec.restraints?.rafter_restraint_spacing_m),
      column_restraint_spacing_m: n(spec.restraints?.column_restraint_spacing_m),
    },
    mode: "design",
    rafter_section: "",
    column_section: "",
    confirmed: false,
  };
}

const SELECT_CLASS =
  "flex h-9 w-full rounded-md border border-border bg-surface px-3 text-sm text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none";

/** Build a ReportMetadata from the form's document fields, or undefined if all blank. */
function buildReportMetadata(d: FormValues["document"]): ReportMetadata | undefined {
  const md: ReportMetadata = {
    project_name: d.project_name.trim() || null,
    client: d.client.trim() || null,
    project_number: d.project_number.trim() || null,
    site_address: d.site_address.trim() || null,
    engineer_name: d.engineer_name.trim() || null,
    engineer_reg_no: d.engineer_reg_no.trim() || null,
    revision: d.revision.trim() || null,
  };
  return Object.values(md).some((v) => v) ? md : undefined;
}

export function ReviewStep({
  spec,
  projectId,
  onComplete,
  onBack,
  onReportMetadata,
  initialReportMetadata,
}: {
  spec: FrameSpec;
  projectId: string;
  onComplete: (result: DesignResponse) => void;
  onBack: () => void;
  /** Lift the entered document metadata so in-session Explore runs reuse it. */
  onReportMetadata?: (metadata: ReportMetadata | undefined) => void;
  /** Project-level document metadata to pre-fill the document fields. */
  initialReportMetadata?: ReportMetadata;
}) {
  const [error, setError] = useState<string | null>(null);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: defaultsFromSpec(spec, initialReportMetadata),
  });

  const geometry = useWatch({ control: form.control, name: "geometry" });
  const mode = useWatch({ control: form.control, name: "mode" });
  const confirmed = useWatch({ control: form.control, name: "confirmed" });

  async function onSubmit(values: FormValues) {
    setError(null);
    const builtSpec: FrameSpec = {
      geometry: {
        span_m: toNum(values.geometry.span_m),
        eaves_height_m: toNum(values.geometry.eaves_height_m),
        roof_pitch_deg: toNum(values.geometry.roof_pitch_deg),
        bay_spacing_m: toNum(values.geometry.bay_spacing_m),
        number_of_bays: toNum(values.geometry.number_of_bays),
      },
      materials: { steel_grade: values.materials.steel_grade },
      base_fixity: "pinned",
      restraints: {
        rafter_restraint_spacing_m: toOptNum(values.restraints.rafter_restraint_spacing_m),
        column_restraint_spacing_m: toOptNum(values.restraints.column_restraint_spacing_m),
      },
      dead: {
        roof_kpa: toNum(values.dead.roof_kpa),
        services_kpa: toNum(values.dead.services_kpa),
        wall_cladding_kpa: toNum(values.dead.wall_cladding_kpa),
      },
      imposed: { roof_access: values.imposed.roof_access },
      wind: {
        basic_wind_speed_ms: toNum(values.wind.basic_wind_speed_ms),
        terrain_category: values.wind.terrain_category,
        site_altitude_m: toNum(values.wind.site_altitude_m),
        has_dominant_opening: values.wind.has_dominant_opening,
      },
      foundation: {
        allowable_bearing_kpa: toOptNum(values.foundation.allowable_bearing_kpa),
        concrete_fcu_mpa: toNum(values.foundation.concrete_fcu_mpa),
      },
    };
    const sections =
      values.mode === "check"
        ? [
            { member: "rafter", designation: values.rafter_section.trim() },
            { member: "column", designation: values.column_section.trim() },
          ]
        : null;
    const reportMetadata = buildReportMetadata(values.document);
    onReportMetadata?.(reportMetadata);
    try {
      const result = await runDesign({
        spec: builtSpec,
        mode: values.mode,
        sections,
        project_id: projectId,
        report_metadata: reportMetadata ?? null,
      });
      onComplete(result);
    } catch (e) {
      setError(e instanceof ServiceError ? e.message : "Something went wrong running the design.");
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-6" noValidate>
        <Card>
          <CardHeader>
            <CardTitle>Geometry</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <FrameSketch
              span={Number(geometry?.span_m)}
              eaves={Number(geometry?.eaves_height_m)}
              pitch={Number(geometry?.roof_pitch_deg)}
            />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <NumberField name="geometry.span_m" label="Span" unit="m" />
              <NumberField name="geometry.eaves_height_m" label="Eaves height" unit="m" />
              <NumberField name="geometry.roof_pitch_deg" label="Roof pitch" unit="°" />
              <NumberField name="geometry.bay_spacing_m" label="Bay spacing" unit="m" />
              <NumberField name="geometry.number_of_bays" label="Number of bays" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Loads</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <NumberField name="dead.roof_kpa" label="Roof dead load" unit="kPa" />
              <NumberField name="dead.services_kpa" label="Services" unit="kPa" />
              <NumberField name="dead.wall_cladding_kpa" label="Wall cladding" unit="kPa" />
            </div>
            <CheckboxField name="imposed.roof_access" label="Roof is accessible (maintenance access)" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Wind</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <NumberField name="wind.basic_wind_speed_ms" label="Basic wind speed" unit="m/s" />
              <FormField
                control={form.control}
                name="wind.terrain_category"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Terrain category</FormLabel>
                    <FormControl>
                      <select {...field} className={SELECT_CLASS}>
                        <option value="A">A</option>
                        <option value="B">B</option>
                        <option value="C">C</option>
                        <option value="D">D</option>
                      </select>
                    </FormControl>
                    <FormDescription>SANS 10160-3:2019 category.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <NumberField name="wind.site_altitude_m" label="Site altitude" unit="m" />
            </div>
            <CheckboxField
              name="wind.has_dominant_opening"
              label="Has a dominant opening (e.g. large roller door)"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Foundation &amp; material</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField
              control={form.control}
              name="foundation.allowable_bearing_kpa"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Allowable bearing</FormLabel>
                  <FormControl>
                    <Input type="number" inputMode="decimal" placeholder="optional" {...field} />
                  </FormControl>
                  <FormDescription>kPa — leave blank to skip the footing design.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <NumberField name="foundation.concrete_fcu_mpa" label="Concrete fcu" unit="MPa" />
            <FormField
              control={form.control}
              name="materials.steel_grade"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Steel grade</FormLabel>
                  <FormControl>
                    <select {...field} className={SELECT_CLASS}>
                      <option value="S275JR">S275JR</option>
                      <option value="S355JR">S355JR</option>
                    </select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Document details (optional)</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="text-sm text-muted">
              These appear on the calc-package cover so it reads as a submission-ready rational
              design report. All optional — leave blank to omit the cover block.
            </p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TextField name="document.project_name" label="Project name" />
              <TextField name="document.project_number" label="Project number" />
              <TextField name="document.client" label="Client" />
              <TextField name="document.revision" label="Revision" placeholder="e.g. A" />
              <TextField name="document.site_address" label="Site address" />
              <TextField name="document.engineer_name" label="Responsible engineer" />
              <TextField name="document.engineer_reg_no" label="ECSA registration no." />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Run mode</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex gap-2">
              <Button
                type="button"
                variant={mode === "design" ? "primary" : "secondary"}
                onClick={() => form.setValue("mode", "design")}
              >
                Design (auto-size)
              </Button>
              <Button
                type="button"
                variant={mode === "check" ? "primary" : "secondary"}
                onClick={() => form.setValue("mode", "check")}
              >
                Check my sections
              </Button>
            </div>
            <p className="text-sm text-muted">
              {mode === "design"
                ? "Design mode auto-sizes the lightest adequate sections for you."
                : "Check mode verifies sections you've already chosen against every SANS clause — you stay the author of the design, TorenOne just checks your working."}
            </p>
            {mode === "check" ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="rafter_section"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Rafter section</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. IPE 400" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="column_section"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Column section</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. IPE 450" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          <CheckboxField
            name="confirmed"
            label="I've reviewed these inputs and confirm them. The engineer is the authoritative pilot — TorenOne computes only what you confirm."
          />
          {error ? (
            <p role="alert" className="text-sm font-medium text-danger">
              {error}
            </p>
          ) : null}
          {form.formState.isSubmitting ? <KernelProgress /> : null}
          <div className="flex gap-3">
            <Button
              type="submit"
              loading={form.formState.isSubmitting}
              disabled={!confirmed || form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? "Running design…" : "Run design"}
            </Button>
            <Button type="button" variant="ghost" onClick={onBack} disabled={form.formState.isSubmitting}>
              Back
            </Button>
          </div>
        </div>
      </form>
    </Form>
  );
}

function NumberField({ name, label, unit }: { name: string; label: string; unit?: string }) {
  return (
    <FormField
      name={name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>
            {label}
            {unit ? <span className="text-subtle"> ({unit})</span> : null}
          </FormLabel>
          <FormControl>
            <Input type="number" inputMode="decimal" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function TextField({
  name,
  label,
  placeholder,
}: {
  name: string;
  label: string;
  placeholder?: string;
}) {
  return (
    <FormField
      name={name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>{label}</FormLabel>
          <FormControl>
            <Input placeholder={placeholder} {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

function CheckboxField({ name, label }: { name: string; label: string }) {
  return (
    <FormField
      name={name}
      render={({ field }) => (
        <FormItem>
          <label className="flex cursor-pointer items-start gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={Boolean(field.value)}
              onChange={(e) => field.onChange(e.target.checked)}
              className="mt-0.5 h-4 w-4 accent-[var(--primary)]"
            />
            <span>{label}</span>
          </label>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
