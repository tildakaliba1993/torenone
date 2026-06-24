import type { Metadata } from "next";
import Link from "next/link";

import { H2, LegalTitle, P, UL } from "@/components/legal/prose";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How TorenOne collects, uses and protects personal information (PoPIA notice).",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <>
      <LegalTitle title="Privacy Policy &amp; PoPIA Notice" updated="Last updated 2026-06-24" />

      <P>
        This Policy explains how FINCREST PTY LTD (registration number 2025/522652/07), which
        operates TorenOne (&ldquo;TorenOne&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;), collects, uses
        and protects personal information when you use the Service, in line with the Protection of
        Personal Information Act 4 of 2013 (&ldquo;PoPIA&rdquo;). Our Information Officer is Tylda
        Wilondja, reachable at <strong>admin@torenone.com</strong>.
      </P>

      <H2>1. Information we process</H2>
      <UL>
        <li><strong>Account data:</strong> your name, email, firm and role, used to authenticate you and scope your data to your firm.</li>
        <li><strong>Project data:</strong> the frame descriptions, inputs and calculation packages you create. These may contain project details you choose to enter.</li>
        <li><strong>Usage &amp; technical data:</strong> logs, request metadata and aggregate product analytics (e.g. designs run, pass/fail, latency) used to operate, secure and improve the Service. These do not include the content of your descriptions.</li>
      </UL>

      <H2>2. How we use it (purpose &amp; lawful basis)</H2>
      <UL>
        <li>To provide the Service (perform our contract with you).</li>
        <li>To secure the Service and prevent abuse (legitimate interest).</li>
        <li>To improve reliability and accuracy via aggregate analytics (legitimate interest).</li>
        <li>To comply with legal obligations.</li>
      </UL>
      <P>We do not sell your personal information.</P>

      <H2>3. The AI parsing step (third-party processing)</H2>
      <P>
        When you submit a free-text description, that text is sent to a third-party AI provider
        (currently OpenAI) to extract a typed specification. The text may therefore be processed outside
        South Africa. <strong>The AI does not compute any engineering value</strong> — those come solely
        from TorenOne&rsquo;s deterministic kernel. Please avoid submitting personal or confidential
        information you are not entitled to disclose. Data submitted through the provider&rsquo;s API
        is not used to train its models.
      </P>

      <H2>4. Storage, location &amp; transfers</H2>
      <P>
        Account and project data are stored with our infrastructure providers under access controls
        that scope each firm&rsquo;s data to that firm. Data is hosted in the European Union and South
        Africa. Where personal information is transferred across borders (e.g. the AI step, or hosting
        regions), we rely on the PoPIA section 72 conditions for trans-border flows.
      </P>

      <H2>5. Retention</H2>
      <P>
        We keep project data and calculation packages while your account is active and per our retention
        policy (report PDFs are subject to a defined retention window). We delete or de-identify personal
        information when it is no longer needed for the purposes above or as required by law.
      </P>

      <H2>6. Sharing &amp; sub-processors</H2>
      <P>
        We share personal information only with operators (sub-processors) that help us run the
        Service, each under appropriate safeguards, and where required by law. These currently include:
      </P>
      <UL>
        <li><strong>Supabase</strong> — database, authentication and report storage.</li>
        <li><strong>Fly.io</strong> — hosting of the engineering service.</li>
        <li><strong>Netlify</strong> — hosting of the web application.</li>
        <li><strong>OpenAI</strong> — the AI parsing step (see section 3).</li>
        <li><strong>Paddle</strong> — payment processing and invoicing (Merchant of Record).</li>
        <li><strong>Sentry</strong> — error monitoring (when enabled).</li>
      </UL>
      <P>We do not sell your personal information.</P>

      <H2>7. Security</H2>
      <UL>
        <li>Authentication and per-firm access isolation (row-level security).</li>
        <li>Encryption in transit; private report storage with scoped, short-lived access links.</li>
        <li>Rate limiting, security headers and dependency scanning.</li>
      </UL>
      <P>No system is perfectly secure; we will notify you and the Information Regulator of a compromise as required by PoPIA.</P>

      <H2>8. Your rights under PoPIA</H2>
      <P>You may, subject to PoPIA, request to:</P>
      <UL>
        <li>access the personal information we hold about you;</li>
        <li>correct or delete inaccurate or outdated information;</li>
        <li>object to certain processing; and</li>
        <li>lodge a complaint with the Information Regulator (South Africa).</li>
      </UL>
      <P>To exercise these rights, contact our Information Officer at admin@torenone.com.</P>

      <H2>9. Children</H2>
      <P>The Service is intended for professional use and is not directed at children.</P>

      <H2>10. Changes &amp; contact</H2>
      <P>
        We may update this Policy; material changes will be notified. Questions: FINCREST PTY LTD
        (TorenOne), Information Officer Tylda Wilondja, admin@torenone.com. See also our{" "}
        <Link href="/terms">Terms of Service</Link> and{" "}
        <Link href="/refunds">Refund &amp; Cancellation Policy</Link>.
      </P>
    </>
  );
}
