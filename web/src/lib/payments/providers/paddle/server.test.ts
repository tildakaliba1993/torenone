import crypto from "node:crypto";

import { describe, expect, it } from "vitest";

import { normalizePaddleEvent, verifyPaddleSignature } from "./server";

const SECRET = "pdl_ntfset_test_secret";
const BODY = JSON.stringify({ event_type: "subscription.activated", data: { id: "sub_1" } });

function sign(body: string, ts: string, secret: string): string {
  const h1 = crypto.createHmac("sha256", secret).update(`${ts}:${body}`).digest("hex");
  return `ts=${ts};h1=${h1}`;
}

describe("verifyPaddleSignature", () => {
  it("accepts a correctly signed payload", () => {
    const header = sign(BODY, "1700000000", SECRET);
    expect(verifyPaddleSignature(BODY, header, SECRET)).toBe(true);
  });

  it("rejects a wrong secret", () => {
    const header = sign(BODY, "1700000000", "the_wrong_secret");
    expect(verifyPaddleSignature(BODY, header, SECRET)).toBe(false);
  });

  it("rejects a tampered body", () => {
    const header = sign(BODY, "1700000000", SECRET);
    expect(verifyPaddleSignature(BODY + "tampered", header, SECRET)).toBe(false);
  });

  it("rejects missing or malformed headers and secret", () => {
    expect(verifyPaddleSignature(BODY, null, SECRET)).toBe(false);
    expect(verifyPaddleSignature(BODY, "garbage", SECRET)).toBe(false);
    expect(verifyPaddleSignature(BODY, "ts=1;h1=zz", SECRET)).toBe(false);
    expect(verifyPaddleSignature(BODY, sign(BODY, "1", SECRET), "")).toBe(false);
  });
});

describe("normalizePaddleEvent", () => {
  it("normalizes a subscription event with custom_data", () => {
    const raw = JSON.stringify({
      event_type: "subscription.activated",
      data: {
        id: "sub_1",
        customer_id: "ctm_1",
        status: "active",
        current_billing_period: { ends_at: "2026-08-01T00:00:00Z" },
        custom_data: { firm_id: "firm-1" },
      },
    });
    expect(normalizePaddleEvent(raw)).toEqual({
      kind: "subscription",
      provider: "paddle",
      firmId: "firm-1",
      customerId: "ctm_1",
      subscriptionId: "sub_1",
      status: "active",
      currentPeriodEnd: "2026-08-01T00:00:00Z",
    });
  });

  it("normalizes a PAYG transaction with a run_id", () => {
    const raw = JSON.stringify({
      event_type: "transaction.completed",
      data: { id: "txn_1", custom_data: { firm_id: "firm-1", run_id: "run-1" } },
    });
    expect(normalizePaddleEvent(raw)).toEqual({
      kind: "package",
      provider: "paddle",
      firmId: "firm-1",
      runId: "run-1",
      transactionId: "txn_1",
    });
  });

  it("ignores unmappable / irrelevant events and bad JSON", () => {
    // subscription without firm_id
    expect(
      normalizePaddleEvent(JSON.stringify({ event_type: "subscription.activated", data: { id: "s" } })),
    ).toBeNull();
    // a renewal transaction (no run_id) is handled by subscription events, not here
    expect(
      normalizePaddleEvent(
        JSON.stringify({ event_type: "transaction.completed", data: { id: "t", custom_data: { firm_id: "f" } } }),
      ),
    ).toBeNull();
    expect(normalizePaddleEvent(JSON.stringify({ event_type: "report.created", data: { id: "x" } }))).toBeNull();
    expect(normalizePaddleEvent("not json")).toBeNull();
  });
});
