import { describe, expect, it } from "vitest";

import { buildCsp, cspHeader } from "./csp";

describe("buildCsp", () => {
  it("allows the Supabase origin (REST + websocket) and the service in connect-src", () => {
    const csp = buildCsp({
      supabaseUrl: "https://abc.supabase.co",
      serviceUrl: "https://api.torenone.fly.dev",
    });
    const connect = csp.split(";").find((d) => d.trim().startsWith("connect-src"))!;
    expect(connect).toContain("'self'");
    expect(connect).toContain("https://abc.supabase.co");
    expect(connect).toContain("wss://abc.supabase.co");
    expect(connect).toContain("https://api.torenone.fly.dev");
  });

  it("locks down framing, base-uri and objects", () => {
    const csp = buildCsp({});
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("base-uri 'self'");
    expect(csp).toContain("default-src 'self'");
  });

  it("ignores malformed URLs without throwing", () => {
    const csp = buildCsp({ supabaseUrl: "not a url", serviceUrl: undefined });
    const connect = csp.split(";").find((d) => d.trim().startsWith("connect-src"))!;
    expect(connect.trim()).toBe("connect-src 'self'");
  });
});

describe("cspHeader", () => {
  it("is report-only by default (cannot break the app)", () => {
    expect(cspHeader({}).key).toBe("Content-Security-Policy-Report-Only");
  });

  it("enforces when enforce=true", () => {
    expect(cspHeader({ enforce: true }).key).toBe("Content-Security-Policy");
  });
});
