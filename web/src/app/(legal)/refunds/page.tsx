import type { Metadata } from "next";
import Link from "next/link";

import { H2, LegalTitle, P, UL } from "@/components/legal/prose";

export const metadata: Metadata = {
  title: "Refund & Cancellation Policy",
  description:
    "How refunds and cancellations work for TorenOne — pay-as-you-go calc packages and the firm subscription.",
  alternates: { canonical: "/refunds" },
};

export default function RefundsPage() {
  return (
    <>
      <LegalTitle title="Refund &amp; Cancellation Policy" updated="Last updated 2026-06-24" />

      <P>
        This policy explains how billing, cancellations and refunds work for TorenOne (the
        &ldquo;Service&rdquo;), operated by FinCrest (Pty) Ltd (registration number 2025/522652/07).
        It forms part of, and should be read with, our <Link href="/terms">Terms of Service</Link>.
        It applies to both pay-as-you-go calc-package purchases and the firm subscription.
      </P>

      <H2>1. What you are paying for</H2>
      <P>
        Creating an account, describing a frame, running the kernel, viewing on-screen results and
        using Check mode are <strong>free</strong>. You are charged only for a <strong>calc
        package</strong> — the stamp-ready calculation-package PDF for a finalised design — either as
        a one-off purchase or as part of a subscription that includes calc packages.
      </P>

      <H2>2. Who processes your payment</H2>
      <P>
        Payments are collected by our reseller and Merchant of Record, who acts as the seller for the
        transaction, processes the payment and issues your invoice. Their name will appear on your
        card or bank statement. Refunds are issued through the same channel to the original payment
        method.
      </P>

      <H2>3. Pay-as-you-go calc packages</H2>
      <P>
        A calc package is a digital good that is generated and delivered to you on purchase. Because
        it is delivered immediately, a purchased calc package is <strong>non-refundable once it has
        been generated or downloaded</strong>, except where:
      </P>
      <UL>
        <li>the Service failed to generate or deliver the package due to a fault on our side; or</li>
        <li>the package was materially defective because of a malfunction in the Service.</li>
      </UL>
      <P>
        In those cases we will, at your choice, re-issue the package or refund that purchase. Re-downloads
        and minor revisions of a design you have already paid for are free and do not incur a new charge.
      </P>

      <H2>4. Firm subscription</H2>
      <UL>
        <li>
          <strong>Cancel anytime.</strong> You can cancel your subscription at any time from your
          account or by contacting us. Cancellation stops future renewals; your access continues until
          the end of the current billing period.
        </li>
        <li>
          <strong>Partial periods.</strong> Subscription fees for the current period are generally
          non-refundable, and we do not pro-rate partial months, except where required by law.
        </li>
        <li>
          <strong>New subscriptions.</strong> If you are unhappy with a <em>first-time</em> subscription,
          contact us within <strong>14 days</strong> of the initial charge and, where the included calc
          packages are substantially unused, we will consider a refund at our discretion.
        </li>
        <li>
          <strong>Renewals.</strong> Subscriptions renew automatically until cancelled. We will make the
          renewal date and amount available in your account.
        </li>
      </UL>

      <H2>5. Your statutory rights</H2>
      <P>
        Nothing in this policy limits any rights you have under South African law, including the
        Consumer Protection Act 68 of 2008 and the Electronic Communications and Transactions Act 25 of
        2002, that cannot lawfully be excluded. Note that statutory cooling-off rights for electronic
        transactions do not apply to digital goods once their generation or download has begun.
      </P>

      <H2>6. How to request a refund or cancel</H2>
      <P>
        Email us at <strong>admin@torenone.com</strong> with your account email and the design or
        invoice in question. We aim to respond within 5 business days. Approved refunds are returned to
        your original payment method via our Merchant of Record.
      </P>

      <H2>7. Chargebacks</H2>
      <P>
        If you believe a charge is incorrect, please contact us first — we will usually resolve it
        faster than a bank dispute. Abusive or fraudulent chargebacks may result in suspension of the
        account under our <Link href="/terms">Terms of Service</Link>.
      </P>

      <H2>8. Changes</H2>
      <P>
        We may update this policy from time to time; the &ldquo;last updated&rdquo; date above reflects
        the current version. Material changes will be notified.
      </P>
    </>
  );
}
