import type { Metadata } from "next";
import Link from "next/link";

import { H2, LegalTitle, P, UL } from "@/components/legal/prose";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "The terms governing your use of TorenOne.",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  return (
    <>
      <LegalTitle title="Terms of Service" updated="Last updated 2026-06-24" />

      <P>
        These Terms govern your use of TorenOne (the &ldquo;Service&rdquo;), operated by FINCREST
        PTY LTD (registration number 2025/522652/07), a company incorporated in the Republic of
        South Africa with its registered address at 187 Sir Lowry Road, C316, Woodstock Quarter,
        Cape Town 7915 (&ldquo;TorenOne&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;). By creating an
        account or using the Service you agree to these Terms. If you do not agree, do not use the
        Service.
      </P>

      <H2>1. What TorenOne is — and is not</H2>
      <P>
        TorenOne is a <strong>computational aid</strong> for the design and checking of single-bay
        SANS steel portal frames. It automates load derivation, analysis and code checks against the
        South African National Standards and produces a calculation package. TorenOne is{" "}
        <strong>not</strong> a registered person, does not practise engineering, and does not provide
        engineering, legal or professional advice.
      </P>
      <P>
        <strong>The registered engineer is the authoritative, responsible agent.</strong> Every output
        must be independently reviewed, verified and — where it informs construction — checked and
        stamped by a professional engineer or technologist registered with the Engineering Council of
        South Africa (ECSA) who accepts professional responsibility for the design. TorenOne does not
        replace that judgement, registration or accountability.
      </P>

      <H2>2. Eligibility &amp; accounts</H2>
      <UL>
        <li>You must be a professional firm or a suitably qualified person to use the Service for real projects.</li>
        <li>You are responsible for the accuracy of the inputs you provide and confirm.</li>
        <li>You are responsible for activity under your account and for keeping your credentials secure.</li>
        <li>Firm &ldquo;owner&rdquo; users may invite colleagues; you are responsible for who you grant access to.</li>
      </UL>

      <H2>3. Your responsibilities as the engineer</H2>
      <UL>
        <li>Review every assumption, load, combination, analysis result and code check before use.</li>
        <li>Confirm all values flagged <strong>PROVISIONAL</strong> against the governing SANS standards.</li>
        <li>Verify items the Service states are out of scope (e.g. connections, foundations, ground conditions, secondary steel, seismic, fire, fatigue) by your own means.</li>
        <li>Apply your professional judgement; do not rely on the Service as a substitute for it.</li>
        <li>Ensure the final design is checked and stamped by an appropriately registered person before construction.</li>
      </UL>

      <H2>4. Acceptable use</H2>
      <P>
        You may not misuse the Service, including by: reverse-engineering or scraping it; attempting to
        circumvent security, rate limits or access controls; using it to design structures outside its
        stated scope and relying on the result; or using it in any unlawful manner.
      </P>

      <H2>5. The AI parsing step</H2>
      <P>
        Free-text descriptions you submit are processed by a third-party AI provider to extract a typed
        specification. <strong>The AI does not compute engineering numbers</strong> — all engineering
        values are produced by TorenOne&rsquo;s deterministic kernel and traced to SANS clauses. Do not
        submit confidential information you are not entitled to disclose. See our{" "}
        <Link href="/privacy">Privacy Policy</Link> for how this data is handled.
      </P>

      <H2>6. Intellectual property</H2>
      <P>
        The Service, its software and the kernel are owned by TorenOne. You retain ownership of the
        project inputs you provide and the calculation packages generated for your projects. You grant
        us a limited licence to process your inputs to provide the Service.
      </P>

      <H2>7. Fees, billing &amp; refunds</H2>
      <P>
        Creating an account, describing a frame, running the kernel, viewing on-screen results and
        Check mode are free. We charge only for a <strong>calc package</strong> — the stamp-ready
        calculation-package PDF for a finalised design — either pay-as-you-go or as part of a firm
        subscription, at the prices on our <Link href="/pricing">pricing page</Link>. Subscriptions
        renew automatically until cancelled. Payments are collected by our reseller and Merchant of
        Record, who acts as seller of record, processes the payment and issues your invoice. Billing,
        cancellation and refunds are governed by our{" "}
        <Link href="/refunds">Refund &amp; Cancellation Policy</Link>.
      </P>

      <H2>8. Disclaimer of warranties</H2>
      <P>
        To the maximum extent permitted by law, the Service is provided <strong>&ldquo;as is&rdquo;</strong>{" "}
        and <strong>&ldquo;as available&rdquo;</strong>, without warranties of any kind, whether express or
        implied, including fitness for a particular purpose and accuracy. We do not warrant that the
        Service is error-free or that any output is correct, complete or suitable for any particular
        project. Nothing in these Terms limits any rights you have under the Consumer Protection Act 68
        of 2008 that cannot lawfully be excluded.
      </P>

      <H2>9. Limitation of liability</H2>
      <P>
        To the maximum extent permitted by law, TorenOne is not liable for any indirect, incidental,
        special or consequential loss, or for any loss arising from your reliance on an output that was
        not independently reviewed and stamped by a registered person. Because the engineer remains the
        responsible agent, you accept that professional responsibility for any design rests with the
        reviewing registered person and not with TorenOne. To the extent any liability cannot lawfully
        be excluded, our total aggregate liability is limited to the fees you paid for the Service in
        the three months preceding the event giving rise to the claim.
      </P>

      <H2>10. Indemnity</H2>
      <P>
        You agree to indemnify TorenOne against claims arising from your use of the Service in breach of
        these Terms, including use of an output in construction without the required professional review
        and stamp.
      </P>

      <H2>11. Suspension &amp; termination</H2>
      <P>
        We may suspend or terminate access for breach of these Terms or to protect the Service. You may
        stop using the Service at any time.
      </P>

      <H2>12. Changes</H2>
      <P>
        We may update the Service and these Terms. Material changes will be notified; continued use after
        changes take effect constitutes acceptance.
      </P>

      <H2>13. Governing law</H2>
      <P>
        These Terms are governed by the laws of the Republic of South Africa, and the South African
        courts have jurisdiction.
      </P>

      <H2>14. Contact</H2>
      <P>
        Questions about these Terms: FINCREST PTY LTD (TorenOne), 187 Sir Lowry Road, C316,
        Woodstock Quarter, Cape Town 7915 · <strong>admin@torenone.com</strong>. See also our{" "}
        <Link href="/privacy">Privacy Policy</Link> and{" "}
        <Link href="/refunds">Refund &amp; Cancellation Policy</Link>.
      </P>
    </>
  );
}
