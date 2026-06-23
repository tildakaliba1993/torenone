import { Hero } from "@/components/landing/hero";
import { LandingNav } from "@/components/landing/landing-nav";
import {
  Features,
  FinalCta,
  HowItWorks,
  SiteFooter,
  Stats,
  TrustBar,
  WhyDifferent,
} from "@/components/landing/sections";

export default function Home() {
  return (
    <div className="flex min-h-dvh flex-col">
      <LandingNav />
      <main className="flex-1">
        <Hero />
        <TrustBar />
        <Stats />
        <Features />
        <HowItWorks />
        <WhyDifferent />
        <FinalCta />
      </main>
      <SiteFooter />
    </div>
  );
}
