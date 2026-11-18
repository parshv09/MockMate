import { LandingNavbar } from "../components/landing/LandingNavbar.jsx";
import { HeroStudioShowcase } from "../components/landing/HeroStudioShowcase.jsx";
import { FeatureBentoSection } from "../components/landing/FeatureBentoSection.jsx";
import { HowItWorksTimeline } from "../components/landing/HowItWorksTimeline.jsx";
import { InteractiveDemoSection } from "../components/landing/InteractiveDemoSection.jsx";
import { AnalyticsReportPreview } from "../components/landing/AnalyticsReportPreview.jsx";
import { FinalCtaFooter } from "../components/landing/FinalCtaFooter.jsx";

export function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <a
        href="#landing-main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground"
      >
        Skip to main content
      </a>

      <LandingNavbar />

      <main id="landing-main" className="flex-1">
        <HeroStudioShowcase />
        <FeatureBentoSection />
        <HowItWorksTimeline />
        <InteractiveDemoSection />
        <AnalyticsReportPreview />
        <FinalCtaFooter />
      </main>
    </div>
  );
}
