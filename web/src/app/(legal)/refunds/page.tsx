import type { Metadata } from "next";
import Link from "next/link";

import { H2, LegalTitle, P } from "@/components/legal/prose";

export const metadata: Metadata = {
  title: "Refund & Cancellation Policy",
  description:
    "How refunds and cancellations work for TorenOne — a 14-day refund, cancel any time, processed by Paddle.",
  alternates: { canonical: "/refunds" },
};

export default function RefundsPage() {
  return (
    <>
      <LegalTitle title="Refund &amp; Cancellation Policy" updated="Last updated 2026-06-24" />

      <P>
        This policy explains how billing, cancellations and refunds work for TorenOne (the
        &ldquo;Service&rdquo;), operated by FINCREST PTY LTD (registration number 2025/522652/07). It
        forms part of, and should be read with, our <Link href="/terms">Terms of Service</Link>.
        Payments are processed by our reseller and Merchant of Record, Paddle, and refunds are handled
        in line with Paddle&rsquo;s buyer terms.
      </P>

      <H2>1. Refunds</H2>
      <P>
        If you are not satisfied with a purchase, you may request a refund within{" "}
        <strong>14 days</strong> of the transaction. Approved refunds are returned to your original
        payment method through Paddle.
      </P>

      <H2>2. Cancelling a subscription</H2>
      <P>
        You can cancel your firm subscription at any time, from your account or by contacting us.
        Cancellation stops future renewals; you keep access until the end of the current billing
        period.
      </P>

      <H2>3. How to request a refund or cancel</H2>
      <P>
        Email us at <strong>admin@torenone.com</strong> with your account email and the purchase in
        question, or request a refund directly through Paddle using the receipt you received. We aim
        to respond within 5 business days.
      </P>

      <H2>4. Your statutory rights</H2>
      <P>
        Nothing in this policy limits any rights you have under South African law, including the
        Consumer Protection Act 68 of 2008, that cannot lawfully be excluded.
      </P>

      <H2>5. Changes</H2>
      <P>
        We may update this policy from time to time; the &ldquo;last updated&rdquo; date above
        reflects the current version. Material changes will be notified.
      </P>
    </>
  );
}
