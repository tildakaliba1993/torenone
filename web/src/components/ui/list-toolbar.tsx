"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Input } from "@/components/ui/input";

export interface ToolbarSelect {
  param: string;
  label: string;
  defaultValue: string;
  options: { value: string; label: string }[];
}

const SELECT_CLASS =
  "h-9 rounded-md border border-border bg-surface px-2.5 text-sm text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none";

/**
 * Search + filter/sort toolbar for a list. Each control is synced to the URL query string
 * (debounced search), so the page re-queries server-side with pagination. Any change
 * resets to page 1.
 */
export function ListToolbar({
  searchKey = "q",
  searchPlaceholder,
  selects = [],
}: {
  searchKey?: string;
  searchPlaceholder?: string;
  selects?: ToolbarSelect[];
}) {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const [q, setQ] = useState(sp.get(searchKey) ?? "");
  const first = useRef(true);

  function update(key: string, value: string, isDefault: boolean) {
    const params = new URLSearchParams(sp.toString());
    if (value && !isDefault) params.set(key, value);
    else params.delete(key);
    params.delete("page"); // any filter change → back to page 1
    router.replace(params.size ? `${pathname}?${params}` : pathname, { scroll: false });
  }

  // Debounce the search box → URL.
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const t = setTimeout(() => update(searchKey, q.trim(), q.trim() === ""), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  return (
    <div className="flex flex-wrap items-center gap-3">
      {searchPlaceholder !== undefined ? (
        <Input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={searchPlaceholder}
          className="max-w-xs"
          aria-label="Search"
        />
      ) : null}
      {selects.map((s) => {
        const current = sp.get(s.param) ?? s.defaultValue;
        return (
          <label key={s.param} className="flex items-center gap-2 text-xs text-muted">
            <span className="hidden sm:inline">{s.label}</span>
            <select
              className={SELECT_CLASS}
              value={current}
              onChange={(e) => update(s.param, e.target.value, e.target.value === s.defaultValue)}
            >
              {s.options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        );
      })}
    </div>
  );
}
