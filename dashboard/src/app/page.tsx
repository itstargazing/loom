import { AttentionPanel } from "@/components/home/attention-panel";
import { HeroPanel } from "@/components/home/hero-panel";
import { PipelineStage } from "@/components/home/pipeline-stage";
import { StatsRow } from "@/components/home/stats-row";
import { ErrorPanel } from "@/components/panel";
import { getAccount, getOverview, getPrivacySettings, getSkillEntries, getWatchedSets } from "@/lib/api";
import { buildHomeView } from "@/lib/home-view";
import type { Contradiction, Deadline } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const [overview, account, privacy, contradictions, deadlines, watchedSets] =
    await Promise.all([
      getOverview(),
      getAccount(),
      getPrivacySettings(),
      getSkillEntries<Contradiction>("contradictions", { limit: 50 }),
      getSkillEntries<Deadline>("deadlines", { limit: 50 }),
      getWatchedSets(),
    ]);

  const view = buildHomeView({
    overview: overview.ok ? overview.data : null,
    account: account.ok ? account.data : null,
    privacy: privacy.ok ? privacy.data : null,
    contradictions: contradictions.ok ? contradictions.data : null,
    deadlines: deadlines.ok ? deadlines.data : null,
    watchedSets: watchedSets.ok ? watchedSets.data : null,
  });

  return (
    <div className="mx-auto flex w-full max-w-[920px] flex-col gap-md">
      {!overview.ok ? (
        <ErrorPanel title="Could not load dashboard data" error={overview.error} />
      ) : null}
      <HeroPanel headline={view.headline} empty={view.empty} />
      <PipelineStage stage={view.stage} />
      <StatsRow
        signalsWoven={view.signalsWoven}
        signalsLastDay={view.signalsLastDay}
        classified={view.classified}
        localOnlyDomains={view.localOnlyDomains}
        localOnlyActive={view.localOnlyActive}
      />
      <AttentionPanel
        unresolved={view.unresolved}
        routeNext={view.routeNext}
        facts={view.facts}
      />
    </div>
  );
}
