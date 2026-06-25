import crypto from "node:crypto";

import { describe, expect, it } from "vitest";

import { verifyPaddleSignature } from "./server";

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
