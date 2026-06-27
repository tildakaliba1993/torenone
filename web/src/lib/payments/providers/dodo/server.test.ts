import crypto from "node:crypto";

import { describe, expect, it } from "vitest";

import { normalizeDodoEvent, verifyDodoSignature } from "./server";

// Standard Webhooks secret: `whsec_` + base64 of the raw key bytes.
const RAW_KEY = Buffer.from("dodo-test-signing-key-0123456789");
const SECRET = `whsec_${RAW_KEY.toString("base64")}`;
const ID = "msg_123";
const TS = "1700000000";
const BODY = JSON.stringify({ type: "subscription.active", data: { subscription_id: "sub_1" } });

function sign(id: string, ts: string, body: string, secret: string): string {
  const keyB64 = secret.startsWith("whsec_") ? secret.slice("whsec_".length) : secret;
  const key = Buffer.from(keyB64, "base64");
  const sig = crypto.createHmac("sha256", key).update(`${id}.${ts}.${body}`).digest("base64");
  return `v1,${sig}`;
}

describe("verifyDodoSignature", () => {
  it("accepts a correctly signed payload", () => {
    const signature = sign(ID, TS, BODY, SECRET);
    expect(verifyDodoSignature(BODY, { id: ID, timestamp: TS, signature }, SECRET)).toBe(true);
  });

  it("accepts when one of several space-delimited signatures matches", () => {
    const good = sign(ID, TS, BODY, SECRET);
    const signature = `v1,AAAA ${good}`;
    expect(verifyDodoSignature(BODY, { id: ID, timestamp: TS, signature }, SECRET)).toBe(true);
  });

  it("rejects a wrong secret", () => {
    const signature = sign(ID, TS, BODY, `whsec_${Buffer.from("nope").toString("base64")}`);
    expect(verifyDodoSignature(BODY, { id: ID, timestamp: TS, signature }, SECRET)).toBe(false);
  });

  it("rejects a tampered body", () => {
    const signature = sign(ID, TS, BODY, SECRET);
    expect(
      verifyDodoSignature(BODY + "tampered", { id: ID, timestamp: TS, signature }, SECRET),
    ).toBe(false);
  });

  it("rejects missing headers and secret", () => {
    const signature = sign(ID, TS, BODY, SECRET);
    expect(verifyDodoSignature(BODY, { id: null, timestamp: TS, signature }, SECRET)).toBe(false);
    expect(verifyDodoSignature(BODY, { id: ID, timestamp: null, signature }, SECRET)).toBe(false);
    expect(verifyDodoSignature(BODY, { id: ID, timestamp: TS, signature: null }, SECRET)).toBe(false);
    expect(verifyDodoSignature(BODY, { id: ID, timestamp: TS, signature }, "")).toBe(false);
  });
});

describe("normalizeDodoEvent", () => {
  it("normalizes a subscription event and maps status", () => {
    const raw = JSON.stringify({
      type: "subscription.on_hold",
      data: {
        subscription_id: "sub_1",
        status: "on_hold",
        customer: { customer_id: "cus_1" },
        next_billing_date: "2026-08-01T00:00:00Z",
        metadata: { firm_id: "firm-1" },
      },
    });
    expect(normalizeDodoEvent(raw)).toEqual({
      kind: "subscription",
      provider: "dodo",
      firmId: "firm-1",
      customerId: "cus_1",
      subscriptionId: "sub_1",
      status: "past_due", // on_hold → past_due
      currentPeriodEnd: "2026-08-01T00:00:00Z",
    });
  });

  it("normalizes a PAYG payment with a run_id", () => {
    const raw = JSON.stringify({
      type: "payment.succeeded",
      data: { payment_id: "pay_1", metadata: { firm_id: "firm-1", run_id: "run-1" } },
    });
    expect(normalizeDodoEvent(raw)).toEqual({
      kind: "package",
      provider: "dodo",
      firmId: "firm-1",
      runId: "run-1",
      transactionId: "pay_1",
    });
  });

  it("ignores unmappable / irrelevant events and bad JSON", () => {
    expect(
      normalizeDodoEvent(JSON.stringify({ type: "subscription.active", data: { subscription_id: "s" } })),
    ).toBeNull(); // no firm_id
    expect(
      normalizeDodoEvent(
        JSON.stringify({ type: "payment.succeeded", data: { payment_id: "p", metadata: { firm_id: "f" } } }),
      ),
    ).toBeNull(); // renewal payment, no run_id
    expect(normalizeDodoEvent(JSON.stringify({ type: "dispute.opened", data: {} }))).toBeNull();
    expect(normalizeDodoEvent("not json")).toBeNull();
  });
});
