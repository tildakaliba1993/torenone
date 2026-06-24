import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Authenticated session so the request layer proceeds to fetch.
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "tok" } } }),
    },
  }),
}));

import { ServiceError, runDesign, warmService } from "./service";

const DESIGN_REQUEST = {
  spec: {} as never,
  mode: "design" as const,
  project_id: "p1",
};

function okJson(body: unknown): Response {
  return { ok: true, json: async () => body } as unknown as Response;
}

describe("engineering-service client resilience", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_ENGINEERING_SERVICE_URL = "https://svc.example";
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("retries a transient connection failure (Fly cold start) and succeeds", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(okJson({ result: { passed: true }, report: { run_id: "r1" } }));
    vi.stubGlobal("fetch", fetchMock);

    const p = runDesign(DESIGN_REQUEST);
    await vi.advanceTimersByTimeAsync(5000);
    const res = await p;

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(res.report.run_id).toBe("r1");
  });

  it("throws a friendly ServiceError after exhausting retries", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);

    const p = runDesign(DESIGN_REQUEST);
    const assertion = expect(p).rejects.toBeInstanceOf(ServiceError);
    await vi.advanceTimersByTimeAsync(5000);
    await assertion;
    // 3 attempts total before giving up.
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("does NOT retry a genuine HTTP error (avoids double-running a design)", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "bad spec" }),
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);

    const p = runDesign(DESIGN_REQUEST);
    const assertion = expect(p).rejects.toThrow(/bad spec/);
    await vi.advanceTimersByTimeAsync(5000);
    await assertion;
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("warmService never throws, even when the service is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );
    await expect(warmService()).resolves.toBeUndefined();
  });
});
