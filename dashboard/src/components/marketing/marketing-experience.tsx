"use client";

import { CustomCursor, ScrollProgress } from "./motion/chrome";
import { LenisRoot } from "./lenis-root";
import { MarketingNav } from "./marketing-nav";
import { MessToMap } from "./visualizations/mess-to-map";
import {
  SiteConcept,
  SiteCta,
  SiteEditorial,
  SiteEngine,
  SiteFeatures,
  SiteFooter,
  SiteHero,
  SiteNetworkStory,
  SiteProblem,
  SiteProduct,
  SiteStats,
} from "./sections/site-sections";

export function MarketingExperience() {
  return (
    <LenisRoot>
      <div className="marketing-root">
        <ScrollProgress />
        <CustomCursor />
        <MarketingNav />
        <main>
          <SiteHero />
          <SiteProblem />
          <SiteConcept />
          <SiteProduct />
          <SiteFeatures />
          <SiteNetworkStory />
          <MessToMap />
          <SiteEditorial />
          <SiteEngine />
          <SiteStats />
          <SiteCta />
        </main>
        <SiteFooter />
      </div>
    </LenisRoot>
  );
}
